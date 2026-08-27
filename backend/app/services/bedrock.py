from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, cast

from anthropic import AnthropicBedrock, APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _coerce_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON object from a model's text response.

    Claude models often wrap JSON in ```json ... ``` fences or add a short
    preamble; this strips fences and, failing that, grabs the outermost
    {...} span, so structured output survives those quirks.
    """
    candidates: list[str] = []
    stripped = text.strip()
    candidates.append(stripped)
    fence = _FENCE_RE.search(text)
    if fence:
        candidates.append(fence.group(1).strip())
    start, end = stripped.find("{"), stripped.rfind("}")
    if start != -1 and end > start:
        candidates.append(stripped[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


class BedrockError(Exception):
    """Base exception for Bedrock (Claude) call failures."""


class BedrockResponseParseError(BedrockError):
    """The model's response wasn't valid JSON. Worth a retry — LLM output varies by sample."""

    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(message)
        self.raw_response = raw_response


class BedrockLLMClient:
    """Shared base for calling a Claude model via AWS Bedrock with JSON output.

    Both the Haiku detection client and the Sonnet caption client subclass
    this so the auth, retry, JSON parsing, vision, and cost-logging plumbing
    lives in one place — they differ only in model ID, token budget, and
    per-token cost rates.

    Authenticates via the standard AWS credential chain (access key/secret,
    IAM role, etc.) — no Anthropic API key involved. HTTP-level retries
    (connection errors, 5xx) are already handled internally by
    `AnthropicBedrock`; this class adds one extra retry specifically for
    malformed JSON output, since that's an LLM-sampling issue, not a network
    one.
    """

    def __init__(
        self,
        *,
        model_id: str,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
        aws_region: str = "us-east-1",
        vision_model_id: str | None = None,
        max_tokens: int = 1024,
        input_cost_per_mtok: float = 0.0,
        output_cost_per_mtok: float = 0.0,
    ) -> None:
        self._client = AnthropicBedrock(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
        )
        self._model_id = model_id
        # Vision (image input) requires a vision-capable model; `model_id` may be
        # text-only, so image calls use `vision_model_id` when set.
        self._vision_model_id = vision_model_id or model_id
        self._max_tokens = max_tokens
        self._input_cost_per_mtok = input_cost_per_mtok
        self._output_cost_per_mtok = output_cost_per_mtok

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens / 1_000_000 * self._input_cost_per_mtok
            + output_tokens / 1_000_000 * self._output_cost_per_mtok
        )

    @retry(
        retry=retry_if_exception_type(BedrockResponseParseError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """Send a text message and parse the response as a JSON object."""
        try:
            response = self._client.messages.create(
                model=self._model_id,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except APIError as exc:
            raise BedrockError(f"Bedrock request failed: {exc}") from exc
        return self._parse_json_response(response)

    @retry(
        retry=retry_if_exception_type(BedrockResponseParseError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def complete_json_with_images(
        self,
        system_prompt: str,
        user_message: str,
        images: list[tuple[str, bytes]],
    ) -> dict[str, Any]:
        """Send a message with images (vision) and parse the response as JSON.

        `images` is a list of (media_type, raw_bytes), e.g. ("image/jpeg",
        b"..."). Uses `vision_model_id` — see __init__.
        """
        content: list[dict[str, Any]] = [{"type": "text", "text": user_message}]
        for media_type, raw_bytes in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.standard_b64encode(raw_bytes).decode(),
                    },
                }
            )
        try:
            response = self._client.messages.create(
                model=self._vision_model_id,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": cast("Any", content)}],
            )
        except APIError as exc:
            raise BedrockError(f"Bedrock vision request failed: {exc}") from exc
        return self._parse_json_response(response)

    def _parse_json_response(self, response: Any) -> dict[str, Any]:
        self._log_usage(response)

        text = "".join(block.text for block in response.content if block.type == "text")
        parsed = _coerce_json_object(text)
        if parsed is None:
            raise BedrockResponseParseError(
                f"Model did not return a JSON object: {text[:200]}", text
            )
        return parsed

    def _log_usage(self, response: Any) -> None:
        usage = response.usage
        cost = self.estimate_cost(usage.input_tokens, usage.output_tokens)
        logger.info(
            "%s call: input_tokens=%s output_tokens=%s estimated_cost_usd=%.6f",
            type(self).__name__,
            usage.input_tokens,
            usage.output_tokens,
            cost,
        )

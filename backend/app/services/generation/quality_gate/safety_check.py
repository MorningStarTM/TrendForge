from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from app.services.bedrock import BedrockLLMClient, BedrockResponseParseError
from app.services.generation.quality_gate.models import CheckResult, GateAction

# Plan task 16.1 / architecture doc 4.5: Haiku scans the caption for cultural
# sensitivity (KSA/UAE), profanity, competitor mentions, and political/
# religious content. A failure is an AUTO-REJECT — it must never reach a human
# reviewer.
#
# The rules below are a PLACEHOLDER (KSA/UAE cultural-sensitivity specifics are
# business content, like the detection prompt and blacklist). See
# prompts/quality_gate/safety_prompt.md for the intended long-term home.
_SAFETY_SYSTEM_PROMPT = """\
You are a brand-safety reviewer for Papa John's social media in the KSA and
UAE markets. Judge whether a caption is safe to publish. Flag it as UNSAFE if
it contains any of: cultural or religious insensitivity for KSA/UAE, profanity,
competitor brand mentions, or political/religious content.

Respond with ONLY a JSON object, no other text:
{
  "safe": <true | false>,
  "flags": <array of any of: cultural_sensitivity, profanity, competitor, political_religious>,
  "reason": <short explanation, or "" if safe>
}"""


class SafetyVerdict(BaseModel):
    safe: bool
    flags: list[str] = []
    reason: str = ""


def check_text_safety(caption: str, client: BedrockLLMClient) -> CheckResult:
    """Scan a caption for brand-safety issues via Haiku (plan task 16.1)."""
    raw = client.complete_json(_SAFETY_SYSTEM_PROMPT, f"Caption:\n{caption}")
    try:
        verdict = SafetyVerdict.model_validate(raw)
    except ValidationError as exc:
        raise BedrockResponseParseError(
            f"Safety response didn't match the SafetyVerdict schema: {exc}", json.dumps(raw)
        ) from exc

    reason = None if verdict.safe else (verdict.reason or ", ".join(verdict.flags) or "unsafe")
    return CheckResult(
        name="text_safety",
        passed=verdict.safe,
        reason=reason,
        fail_action=GateAction.REJECT,
    )

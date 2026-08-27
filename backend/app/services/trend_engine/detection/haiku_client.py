from __future__ import annotations

from app.services.bedrock import BedrockError, BedrockLLMClient, BedrockResponseParseError

# Bedrock model ID for Claude Haiku — some Bedrock regions require an
# inference-profile-prefixed ID (e.g. "us.anthropic.claude-3-5-haiku-...")
# instead of the bare model ID. Confirm/adjust this once real AWS
# credentials are available and you can see what your account/region needs.
DEFAULT_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"
DEFAULT_MAX_TOKENS = 1024

# Doc 3.2's stated per-trend cost example (~2K in / ~500 out -> $0.001)
# implies these rates; not fetched from a live pricing API, so re-check
# against Anthropic's current Bedrock pricing before relying on this for
# real budgeting.
INPUT_COST_PER_MILLION_TOKENS = 0.25
OUTPUT_COST_PER_MILLION_TOKENS = 1.00

# The Bedrock client machinery now lives in app.services.bedrock; these
# aliases keep existing imports (`HaikuClientError`, `HaikuResponseParseError`)
# working for the detection classifier, the visual-patterns analyzer, and
# their tests.
HaikuClientError = BedrockError
HaikuResponseParseError = BedrockResponseParseError


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1_000_000 * INPUT_COST_PER_MILLION_TOKENS
        + output_tokens / 1_000_000 * OUTPUT_COST_PER_MILLION_TOKENS
    )


class HaikuClient(BedrockLLMClient):
    """Claude Haiku via AWS Bedrock — structured (JSON) output, cost logging.

    Thin subclass of `BedrockLLMClient` fixing Haiku's model ID and cost
    rates. Used for trend detection/classification (Module 9) and the
    text-safety quality gate; the vision path is used for TCO visual-pattern
    analysis when `vision_model_id` points at a vision-capable model.
    """

    def __init__(
        self,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
        aws_region: str = "us-east-1",
        model_id: str = DEFAULT_MODEL_ID,
        vision_model_id: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        super().__init__(
            model_id=model_id,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
            vision_model_id=vision_model_id,
            max_tokens=max_tokens,
            input_cost_per_mtok=INPUT_COST_PER_MILLION_TOKENS,
            output_cost_per_mtok=OUTPUT_COST_PER_MILLION_TOKENS,
        )

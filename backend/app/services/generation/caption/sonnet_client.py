from __future__ import annotations

from app.services.bedrock import BedrockLLMClient

# Bedrock model ID for Claude Sonnet — verify the exact ID / inference-profile
# prefix against your Bedrock region once real AWS credentials are available.
DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
# Captions are short but the model returns 2-3 variants as JSON; give it room.
DEFAULT_MAX_TOKENS = 2048

# Approximate Bedrock pricing for Sonnet; the plan doc's caption cost example
# (~4K in / ~2K out -> ~$0.03) is in this ballpark. Re-check against current
# Bedrock pricing before relying on this for budgeting.
INPUT_COST_PER_MILLION_TOKENS = 3.00
OUTPUT_COST_PER_MILLION_TOKENS = 15.00


class SonnetClient(BedrockLLMClient):
    """Claude Sonnet via AWS Bedrock — structured (JSON) output, cost logging.

    Thin subclass of `BedrockLLMClient` fixing Sonnet's model ID, a larger
    token budget (multiple caption variants), and Sonnet's cost rates. Used
    for caption generation (Module 13) and, later, image-prompt generation
    (Module 14).
    """

    def __init__(
        self,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
        aws_region: str = "us-east-1",
        model_id: str = DEFAULT_MODEL_ID,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        super().__init__(
            model_id=model_id,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
            max_tokens=max_tokens,
            input_cost_per_mtok=INPUT_COST_PER_MILLION_TOKENS,
            output_cost_per_mtok=OUTPUT_COST_PER_MILLION_TOKENS,
        )

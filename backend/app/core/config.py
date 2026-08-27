from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    scrapecreators_api_key: str
    scrapecreators_base_url: str = "https://api.scrapecreators.com"

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"
    s3_bucket_brand_kb: str = "brand-kb"
    # General-purpose bucket that also holds brand KB material (upload target).
    s3_bucket_raw_media: str = "raw-media"
    bedrock_region: str = "us-east-1"
    haiku_model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"
    # Sonnet (via Bedrock) for caption + image-prompt generation (Modules 13-14).
    # Verify the exact ID / inference-profile prefix against your Bedrock region.
    sonnet_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    # Must be a vision-capable Bedrock model for the visual-analysis (Option A)
    # path; left unset falls back to haiku_model_id (which may be text-only).
    vision_model_id: str | None = None

    # Hugging Face Inference API for embeddings (dedup + Brand KB RAG) — hosted,
    # so no torch/sentence-transformers is bundled. Same model as before, so the
    # validated 0.85 dedup threshold still holds.
    hf_token: str | None = None
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Google Gemini for image generation (nano banana).
    gemini_api_key: str | None = None
    gemini_image_model: str = "gemini-2.5-flash-image"


@lru_cache
def get_settings() -> Settings:
    return Settings()

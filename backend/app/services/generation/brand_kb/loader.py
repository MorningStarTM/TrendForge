from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.services.generation.brand_kb.chunking import BrandChunk, chunk_document
from app.services.generation.brand_kb.extractors import (
    UnsupportedFormatError,
    extract_text,
    is_supported,
)
from app.services.generation.brand_kb.retrieval import BrandKB, get_brand_kb

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

# Architecture doc 12.1: brand KB lives under these prefixes in s3://brand-kb/.
DEFAULT_PREFIXES = (
    "guidelines/",
    "recent-posts/",
    "dos-and-donts/",
    "regional/",
    "competitors/",
)


def load_chunks_from_s3(
    s3_client: Any,
    bucket: str,
    prefixes: tuple[str, ...] = DEFAULT_PREFIXES,
) -> list[BrandChunk]:
    """List brand KB objects in S3, extract text, and chunk them (docs 12.1-12.2).

    `s3_client` is any boto3-S3-compatible client (injected so this is testable
    without real AWS). Unsupported file types are skipped with a warning rather
    than aborting the whole load.
    """
    chunks: list[BrandChunk] = []
    for prefix in prefixes:
        for key in _list_keys(s3_client, bucket, prefix):
            if not is_supported(key):
                logger.warning("Skipping unsupported brand KB file: %s", key)
                continue
            data = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
            try:
                text = extract_text(key, data)
            except UnsupportedFormatError as exc:
                logger.warning("Skipping %s: %s", key, exc)
                continue
            chunks.extend(chunk_document(text, source_doc=key))
    return chunks


def _list_keys(s3_client: Any, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    continuation_token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = s3_client.list_objects_v2(**kwargs)
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith("/"):  # skip folder placeholder keys
                keys.append(key)
        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")
    return keys


def _build_s3_client(settings: Settings) -> Any:
    import boto3

    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def load_brand_kb(
    settings: Settings | None = None,
    kb: BrandKB | None = None,
    s3_client: Any | None = None,
) -> int:
    """Populate the Brand KB from S3: load chunks, embed, store. Returns chunk count.

    The real entry point wires up boto3 from settings; tests pass their own
    `s3_client` and `kb`.
    """
    if settings is None:
        from app.core.config import get_settings

        settings = get_settings()
    kb = kb or get_brand_kb()
    s3_client = s3_client or _build_s3_client(settings)

    chunks = load_chunks_from_s3(s3_client, settings.s3_bucket_brand_kb)
    added = kb.add_chunks(chunks)
    logger.info("Loaded %s brand KB chunks from s3://%s", added, settings.s3_bucket_brand_kb)
    return added

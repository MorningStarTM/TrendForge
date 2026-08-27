"""S3-backed storage for Brand Context KB documents (Module 12).

Uploads, lists and deletes brand-guideline material in the general bucket
(S3_BUCKET_RAW_MEDIA) under the category prefixes the RAG loader reads from.
Kept separate from
`brand_kb/loader.py` (which reads + chunks for retrieval) so the frontend has a
plain document-management surface.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.services.generation.brand_kb.extractors import is_supported
from app.services.generation.brand_kb.loader import DEFAULT_PREFIXES

logger = logging.getLogger(__name__)

# Human labels for the S3 category prefixes (architecture doc 12.1).
CATEGORIES: dict[str, str] = {
    "guidelines": "Brand guidelines",
    "recent-posts": "Recent posts",
    "dos-and-donts": "Do's & don'ts",
    "regional": "Regional (KSA / UAE)",
    "competitors": "Competitors",
}


class BrandStorageError(RuntimeError):
    """S3 is not configured or the operation failed."""


def _prefix_for(category: str) -> str:
    prefix = f"{category}/"
    if prefix not in DEFAULT_PREFIXES:
        raise BrandStorageError(
            f"Unknown category '{category}'. Valid: {sorted(CATEGORIES)}"
        )
    return prefix


def _client(settings: Settings) -> Any:
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        raise BrandStorageError("AWS credentials are not configured.")
    import boto3

    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def _wrap_s3_errors(exc: Exception) -> BrandStorageError:
    from botocore.exceptions import ClientError

    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"NoSuchBucket", "404"}:
            return BrandStorageError(
                "Brand KB bucket does not exist yet — create the S3 bucket "
                "named in S3_BUCKET_RAW_MEDIA."
            )
        if code in {"AccessDenied", "403", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            return BrandStorageError("AWS denied access to the brand KB bucket.")
    return BrandStorageError(str(exc))


def list_documents(settings: Settings | None = None) -> list[dict[str, Any]]:
    """List every brand-KB object across all category prefixes."""
    settings = settings or get_settings()
    bucket = settings.s3_bucket_raw_media
    client = _client(settings)
    docs: list[dict[str, Any]] = []
    try:
        for category in CATEGORIES:
            prefix = f"{category}/"
            token: str | None = None
            while True:
                kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
                if token:
                    kwargs["ContinuationToken"] = token
                resp = client.list_objects_v2(**kwargs)
                for obj in resp.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue
                    filename = key[len(prefix) :]
                    last_modified = obj.get("LastModified")
                    docs.append(
                        {
                            "key": key,
                            "filename": filename,
                            "category": category,
                            "size": obj.get("Size", 0),
                            "last_modified": last_modified.isoformat()
                            if isinstance(last_modified, datetime)
                            else None,
                            "extractable": is_supported(filename),
                        }
                    )
                if not resp.get("IsTruncated"):
                    break
                token = resp.get("NextContinuationToken")
    except Exception as exc:  # noqa: BLE001 - normalise to a UI-friendly error
        raise _wrap_s3_errors(exc) from exc
    docs.sort(key=lambda d: d.get("last_modified") or "", reverse=True)
    return docs


def upload_document(
    category: str, filename: str, data: bytes, settings: Settings | None = None
) -> dict[str, Any]:
    """Upload one brand-KB file to s3://<bucket>/<category>/<filename>."""
    settings = settings or get_settings()
    prefix = _prefix_for(category)
    safe_name = filename.strip().replace("/", "_")
    if not safe_name:
        raise BrandStorageError("Empty filename.")
    key = f"{prefix}{safe_name}"
    client = _client(settings)
    try:
        client.put_object(Bucket=settings.s3_bucket_raw_media, Key=key, Body=data)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_s3_errors(exc) from exc
    logger.info("Uploaded brand KB file: %s (%s bytes)", key, len(data))
    return {
        "key": key,
        "filename": safe_name,
        "category": category,
        "size": len(data),
        "extractable": is_supported(safe_name),
    }


def delete_document(key: str, settings: Settings | None = None) -> None:
    """Delete a brand-KB object by its full S3 key."""
    settings = settings or get_settings()
    if not any(key.startswith(f"{c}/") for c in CATEGORIES):
        raise BrandStorageError("Refusing to delete a key outside the brand KB prefixes.")
    client = _client(settings)
    try:
        client.delete_object(Bucket=settings.s3_bucket_raw_media, Key=key)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_s3_errors(exc) from exc
    logger.info("Deleted brand KB file: %s", key)


def rebuild_kb(settings: Settings | None = None) -> int:
    """Re-load, chunk and embed the whole brand KB from S3. Returns chunk count."""
    from app.services.generation.brand_kb.loader import load_brand_kb

    settings = settings or get_settings()
    try:
        return load_brand_kb(settings=settings)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_s3_errors(exc) from exc

"""
Cloudflare R2 file storage service.

Uses boto3 with the R2 S3-compatible endpoint. All functions are best-effort:
if R2 is not configured (env vars missing), they return None/False gracefully
so the application continues without file persistence.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return all(
        os.getenv(k)
        for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
    )


def _get_client():
    """Return a boto3 S3 client pointed at Cloudflare R2, or None if not configured."""
    if not _is_configured():
        return None

    try:
        import boto3  # imported lazily so missing boto3 doesn't crash startup

        account_id = os.environ["R2_ACCOUNT_ID"]
        return boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
    except Exception as exc:
        logger.error("Failed to create R2 client: %s", exc)
        return None


def make_key(tender_id: str, filename: str) -> str:
    """Generate a deterministic, path-traversal-safe R2 object key."""
    safe = filename.replace("/", "_").replace("\\", "_").replace("..", "_")
    return f"tenders/{tender_id}/{safe}"


def upload_file(local_path: str, key: str) -> bool:
    """
    Upload *local_path* to R2 under *key*.
    Returns True on success, False if R2 is not configured or upload fails.
    """
    client = _get_client()
    if client is None:
        return False

    bucket = os.environ["R2_BUCKET_NAME"]
    try:
        client.upload_file(local_path, bucket, key)
        logger.info("R2 upload succeeded: key=%s", key)
        return True
    except Exception as exc:
        logger.error("R2 upload failed: key=%s error=%s", key, exc)
        return False


def get_presigned_url(key: str, expires_in: int = 3600) -> str | None:
    """
    Generate a pre-signed GET URL for *key*.
    Returns None if R2 is not configured or the operation fails.
    """
    client = _get_client()
    if client is None:
        return None

    bucket = os.environ["R2_BUCKET_NAME"]
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as exc:
        logger.error("R2 presign failed: key=%s error=%s", key, exc)
        return None

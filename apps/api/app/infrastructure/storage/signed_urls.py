"""
Claustor AI — GCS Signed URL Generator
Generates time-limited signed URLs for secure document access.
"""
from __future__ import annotations
import structlog
from datetime import timedelta
from typing import Optional

logger = structlog.get_logger(__name__)


def generate_signed_url(
    gcs_path: str,
    expiry_minutes: int = 60,
    method: str = "GET",
) -> Optional[str]:
    """
    Generate a signed URL for GCS object access.
    URL expires after expiry_minutes (default 60 min).
    Returns None if GCS not configured (dev mode).
    """
    try:
        from google.cloud import storage
        from app.core.config import settings

        client = storage.Client()

        if gcs_path.startswith("gs://"):
            parts = gcs_path[5:].split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""
        else:
            bucket_name = settings.GCS_BUCKET
            blob_name = gcs_path

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiry_minutes),
            method=method,
        )
        logger.debug("signed_url_generated",
                    bucket=bucket_name, blob=blob_name,
                    expiry_minutes=expiry_minutes)
        return url

    except ImportError:
        logger.debug("gcs_not_configured_signed_url_skipped")
        return None
    except Exception as e:
        logger.warning("signed_url_failed", path=gcs_path, error=str(e))
        return None


def generate_upload_url(
    org_id: str,
    filename: str,
    content_type: str = "application/pdf",
    expiry_minutes: int = 15,
) -> Optional[dict]:
    """Generate a signed URL for direct client upload to GCS."""
    try:
        from app.core.config import settings
        import uuid
        blob_name = f"{org_id}/{uuid.uuid4()}/{filename}"
        url = generate_signed_url(
            gcs_path=f"gs://{settings.GCS_BUCKET}/{blob_name}",
            expiry_minutes=expiry_minutes,
            method="PUT",
        )
        if url:
            return {
                "upload_url": url,
                "blob_name": blob_name,
                "expires_in": expiry_minutes * 60,
            }
    except Exception as e:
        logger.warning("upload_url_failed", error=str(e))
    return None

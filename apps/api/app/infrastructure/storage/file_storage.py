"""
Claustor AI — File Storage
GCS in production, local filesystem in dev.
Auto-detects based on GOOGLE_APPLICATION_CREDENTIALS.
"""

import os
import shutil
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

LOCAL_STORAGE_DIR = Path("/tmp/claustor-uploads")
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class FileStorage:
    """
    Unified file storage — GCS or local.
    Local is used automatically when GCS credentials not configured.
    """

    def __init__(self):
        self._use_gcs = self._check_gcs()
        if self._use_gcs:
            from google.cloud import storage as gcs
            from app.core.config import settings
            self._client = gcs.Client()
            self._bucket_name = getattr(settings, "GCS_BUCKET", "claustor-contracts")
            self._bucket = self._client.bucket(self._bucket_name)
            logger.info("file_storage_gcs", bucket=self._bucket_name)
        else:
            logger.info("file_storage_local", path=str(LOCAL_STORAGE_DIR))

    def _check_gcs(self) -> bool:
        """Check if GCS credentials are available."""
        try:
            creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_file and Path(creds_file).exists():
                return True
            # Check application default credentials
            from google.auth import default
            default()
            return True
        except Exception:
            return False

    async def upload(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Upload file. Returns storage path.
        """
        if self._use_gcs:
            blob = self._bucket.blob(path)
            blob.upload_from_string(data, content_type=content_type)
            return f"gs://{self._bucket_name}/{path}"
        else:
            local_path = LOCAL_STORAGE_DIR / path.replace("/", "_")
            local_path.write_bytes(data)
            return str(local_path)

    async def download(self, path: str) -> bytes:
        """Download file by path."""
        if self._use_gcs:
            if path.startswith("gs://"):
                path = path.split("/", 3)[-1]
            blob = self._bucket.blob(path)
            return blob.download_as_bytes()
        else:
            # Handle both GCS paths and local paths
            if path.startswith("gs://"):
                # Convert GCS path to local
                filename = path.split("/")[-1]
                local_path = LOCAL_STORAGE_DIR / filename
            elif path.startswith("/tmp/"):
                local_path = Path(path)
            else:
                local_path = LOCAL_STORAGE_DIR / path.replace("/", "_")

            if local_path.exists():
                return local_path.read_bytes()
            else:
                raise FileNotFoundError(f"File not found locally: {local_path}")

    async def delete(self, path: str) -> None:
        """Delete file."""
        if self._use_gcs:
            if path.startswith("gs://"):
                path = path.split("/", 3)[-1]
            blob = self._bucket.blob(path)
            blob.delete()
        else:
            local_path = LOCAL_STORAGE_DIR / path.replace("/", "_")
            if local_path.exists():
                local_path.unlink()

    def get_download_url(self, path: str, expiry_minutes: int = 60) -> str:
        """Get signed URL for GCS or local path."""
        if self._use_gcs:
            from datetime import timedelta
            if path.startswith("gs://"):
                path = path.split("/", 3)[-1]
            blob = self._bucket.blob(path)
            return blob.generate_signed_url(expiration=timedelta(minutes=expiry_minutes))
        else:
            return path  # Return local path for dev


# Singleton
_storage: FileStorage | None = None

def get_storage() -> FileStorage:
    global _storage
    if _storage is None:
        _storage = FileStorage()
    return _storage

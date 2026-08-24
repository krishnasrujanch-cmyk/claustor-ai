"""
Claustor AI — Storage Client
GCS in production, local filesystem in dev.
Auto-detects based on GCP credentials availability.
"""

import os
import asyncio
from pathlib import Path
from uuid import UUID

import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

LOCAL_DIR = Path.home() / "claustor-uploads"
LOCAL_DIR.mkdir(parents=True, exist_ok=True)  # ~/claustor-uploads/

MAX_FILE_SIZE_MB    = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES  = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword", "text/plain",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def _gcs_available() -> bool:
    try:
        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds and Path(creds).exists():
            return True
        from google.auth import default
        default()
        return True
    except Exception:
        return False


# USE_GCS evaluated lazily in StorageClient.__init__


class StorageClient:
    """Unified storage — GCS or local fallback."""

    def __init__(self):
        if _gcs_available():
            from google.cloud import storage as gcs
            self._client = gcs.Client(project=getattr(settings, "GCP_PROJECT", None))
            self._bucket_name = getattr(settings, "GCS_BUCKET_CONTRACTS", "claustor-contracts")
            self._bucket = self._client.bucket(self._bucket_name)
            logger.info("storage_gcs", bucket=self._bucket_name)
        else:
            logger.info("storage_local", path=str(LOCAL_DIR))

    async def upload_contract(
        self,
        org_id: UUID,
        contract_id: UUID,
        filename: str,
        data: bytes = None, file_bytes: bytes = None,
        content_type: str = "application/pdf",
    ) -> dict:
        path = f"orgs/{org_id}/contracts/{contract_id}/{filename}"
        payload = data or file_bytes or b""

        if USE_GCS:
            blob = self._bucket.blob(path)
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: blob.upload_from_string(payload, content_type=content_type)
            )
            gcs_path = f"gs://{self._bucket_name}/{path}"
        else:
            # Local fallback
            local_path = LOCAL_DIR / str(org_id) / str(contract_id)
            local_path.mkdir(parents=True, exist_ok=True)
            file_path = local_path / filename
            file_path.write_bytes(payload)
            gcs_path = str(file_path)

        logger.info("file_uploaded", path=gcs_path, size=len(payload))
        return {"gcs_path": gcs_path, "size_bytes": len(payload)}

    async def download_contract_concurrent(self, paths: list[str]) -> list[bytes]:
        """Download multiple contracts concurrently."""
        tasks = [self.download_contract(p) for p in paths]
        return await asyncio.gather(*tasks)

    async def download_contract(self, gcs_path: str) -> bytes:
        if USE_GCS and gcs_path.startswith("gs://"):
            parts = gcs_path.replace("gs://", "").split("/", 1)
            blob = self._client.bucket(parts[0]).blob(parts[1])
            return await asyncio.get_event_loop().run_in_executor(
                None, blob.download_as_bytes
            )
        else:
            # Local fallback — handle both gs:// paths stored as local
            local_path = Path(gcs_path)
            if local_path.exists():
                return local_path.read_bytes()
            # Try to find in local storage by contract_id in path
            raise FileNotFoundError(f"File not found: {gcs_path}")

    async def delete_contract(self, org_id: UUID, contract_id: UUID) -> None:
        if USE_GCS:
            prefix = f"orgs/{org_id}/contracts/{contract_id}/"
            blobs = self._client.list_blobs(self._bucket_name, prefix=prefix)
            for blob in blobs:
                blob.delete()
        else:
            local_path = LOCAL_DIR / str(org_id) / str(contract_id)
            if local_path.exists():
                import shutil
                shutil.rmtree(local_path)


_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    global _client
    if _client is None:
        _client = StorageClient()
    return _client

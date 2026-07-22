"""
Claustor AI — Google Cloud Storage Client
Per-org file isolation: orgs/{org_id}/contracts/{contract_id}/
Signed URLs for secure temporary access.
"""

import asyncio
import hashlib
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import structlog
from google.cloud import storage
from google.cloud.exceptions import NotFound

from app.core.config import settings

logger = structlog.get_logger(__name__)

# File size limits
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".txt"}


class StorageClient:
    """
    GCS storage client with per-org isolation.

    File structure:
        orgs/{org_id}/contracts/{contract_id}/original.pdf
        orgs/{org_id}/contracts/{contract_id}/parsed.json
        orgs/{org_id}/contracts/{contract_id}/ocr_cache.json
    """

    def __init__(self):
        self.client = storage.Client(project=settings.GCP_PROJECT)
        self.bucket_name = settings.GCS_BUCKET_CONTRACTS
        self.cache_bucket_name = settings.GCS_BUCKET_CACHE
        self._bucket = None
        self._cache_bucket = None

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    @property
    def cache_bucket(self):
        if self._cache_bucket is None:
            self._cache_bucket = self.client.bucket(self.cache_bucket_name)
        return self._cache_bucket

    def get_contract_path(self, org_id: UUID, contract_id: UUID, filename: str) -> str:
        """Get GCS path for a contract file."""
        return f"orgs/{org_id}/contracts/{contract_id}/{filename}"

    def get_cache_path(self, file_hash: str, cache_type: str) -> str:
        """Get GCS path for cached processing output."""
        return f"cache/{file_hash}/{cache_type}.json"

    def compute_file_hash(self, file_bytes: bytes) -> str:
        """SHA-256 hash of file — used for dedup and cache keys."""
        return hashlib.sha256(file_bytes).hexdigest()

    def validate_file(
        self,
        filename: str,
        file_bytes: bytes,
        mime_type: str | None = None,
    ) -> tuple[bool, str]:
        """
        Validate file before upload.
        Returns (is_valid, error_message).
        """
        # Check size
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            return False, f"File too large. Max {MAX_FILE_SIZE_MB}MB allowed."

        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File type not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

        # Check MIME type if provided
        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            return False, f"MIME type not supported: {mime_type}"

        # Basic PDF magic bytes check
        if ext == ".pdf" and not file_bytes.startswith(b"%PDF"):
            return False, "Invalid PDF file."

        return True, ""

    async def upload_contract(
        self,
        org_id: UUID,
        contract_id: UUID,
        filename: str,
        file_bytes: bytes,
        mime_type: str = "application/pdf",
    ) -> dict:
        """
        Upload contract file to GCS.

        Returns:
            {gcs_path, file_hash, file_size_bytes, signed_url}
        """
        file_hash = self.compute_file_hash(file_bytes)
        safe_filename = "original" + Path(filename).suffix.lower()
        gcs_path = self.get_contract_path(org_id, contract_id, safe_filename)

        loop = asyncio.get_event_loop()

        def _upload():
            blob = self.bucket.blob(gcs_path)
            blob.metadata = {
                "org_id": str(org_id),
                "contract_id": str(contract_id),
                "original_filename": filename,
                "file_hash": file_hash,
            }
            blob.upload_from_string(
                file_bytes,
                content_type=mime_type,
                checksum="md5",
            )
            return blob

        blob = await loop.run_in_executor(None, _upload)

        logger.info(
            "contract_uploaded",
            org_id=str(org_id),
            contract_id=str(contract_id),
            gcs_path=gcs_path,
            size_bytes=len(file_bytes),
            file_hash=file_hash[:8],
        )

        return {
            "gcs_path": gcs_path,
            "file_hash": file_hash,
            "file_size_bytes": len(file_bytes),
        }

    async def download_contract(
        self,
        org_id: UUID,
        contract_id: UUID,
        filename: str = "original.pdf",
    ) -> bytes:
        """Download contract file from GCS."""
        gcs_path = self.get_contract_path(org_id, contract_id, filename)

        loop = asyncio.get_event_loop()

        def _download():
            blob = self.bucket.blob(gcs_path)
            return blob.download_as_bytes()

        try:
            file_bytes = await loop.run_in_executor(None, _download)
            logger.debug(
                "contract_downloaded",
                org_id=str(org_id),
                contract_id=str(contract_id),
                size_bytes=len(file_bytes),
            )
            return file_bytes
        except NotFound:
            raise FileNotFoundError(f"Contract file not found: {gcs_path}")

    async def generate_signed_url(
        self,
        org_id: UUID,
        contract_id: UUID,
        filename: str = "original.pdf",
        expiry_minutes: int = 15,
    ) -> str:
        """
        Generate temporary signed URL for file download.
        Never expose raw GCS paths to users.
        """
        gcs_path = self.get_contract_path(org_id, contract_id, filename)
        loop = asyncio.get_event_loop()

        def _sign():
            blob = self.bucket.blob(gcs_path)
            return blob.generate_signed_url(
                expiration=timedelta(minutes=expiry_minutes),
                method="GET",
                version="v4",
            )

        url = await loop.run_in_executor(None, _sign)
        logger.debug(
            "signed_url_generated",
            org_id=str(org_id),
            contract_id=str(contract_id),
            expiry_minutes=expiry_minutes,
        )
        return url

    async def delete_contract(
        self,
        org_id: UUID,
        contract_id: UUID,
    ) -> int:
        """
        Delete all files for a contract.
        Returns number of files deleted.
        """
        prefix = f"orgs/{org_id}/contracts/{contract_id}/"
        loop = asyncio.get_event_loop()

        def _delete():
            blobs = list(self.client.list_blobs(self.bucket_name, prefix=prefix))
            count = len(blobs)
            if blobs:
                self.bucket.delete_blobs(blobs)
            return count

        count = await loop.run_in_executor(None, _delete)
        logger.info(
            "contract_files_deleted",
            org_id=str(org_id),
            contract_id=str(contract_id),
            files_deleted=count,
        )
        return count

    async def save_parsed_output(
        self,
        file_hash: str,
        cache_type: str,
        data: str,
    ) -> None:
        """
        Cache parsed/OCR output by file hash.
        Same file uploaded by different orgs = same parse result.
        TTL: managed by GCS lifecycle policy (7 days).
        """
        gcs_path = self.get_cache_path(file_hash, cache_type)
        loop = asyncio.get_event_loop()

        def _save():
            blob = self.cache_bucket.blob(gcs_path)
            blob.upload_from_string(data, content_type="application/json")

        await loop.run_in_executor(None, _save)
        logger.debug("parse_cache_saved", file_hash=file_hash[:8], cache_type=cache_type)

    async def load_parsed_output(
        self,
        file_hash: str,
        cache_type: str,
    ) -> str | None:
        """Load cached parse output. Returns None if not cached."""
        gcs_path = self.get_cache_path(file_hash, cache_type)
        loop = asyncio.get_event_loop()

        def _load():
            blob = self.cache_bucket.blob(gcs_path)
            if not blob.exists():
                return None
            return blob.download_as_text()

        try:
            result = await loop.run_in_executor(None, _load)
            if result:
                logger.debug("parse_cache_hit", file_hash=file_hash[:8], cache_type=cache_type)
            return result
        except Exception:
            return None


# Singleton
_storage_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    """Get or create singleton storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client

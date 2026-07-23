"""
Claustor AI — Contract Service
Business logic for contract management.
Coordinates: DB, GCS, Pinecone, Celery queue.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.domain.models import Contract, Clause
from app.domain.schemas.contract import ProcessingStatus

logger = structlog.get_logger(__name__)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

# Processing steps by status
PROCESSING_STEPS = {
    "queued":     (0,  "Waiting in queue",         []),
    "parsing":    (20, "Extracting document text",  ["queued"]),
    "extracting": (40, "Extracting clauses",        ["queued", "parsing"]),
    "scoring":    (60, "Scoring risks",             ["queued", "parsing", "extracting"]),
    "indexing":   (80, "Indexing for search",       ["queued", "parsing", "extracting", "scoring"]),
    "analyzed":   (100,"Analysis complete",         ["queued", "parsing", "extracting", "scoring", "indexing"]),
    "failed":     (0,  "Processing failed",         []),
}


class ContractLimitError(Exception):
    pass


class ContractService:
    """
    Contract business logic.
    All contract operations go through this service.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def validate_file(
        self,
        filename: str,
        file_bytes: bytes,
        mime_type: str | None = None,
    ) -> None:
        """Validate file before upload. Raises ValueError on invalid."""
        # Size check
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File too large. Maximum size is 50MB.")

        # Extension check
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{ext}' not supported. "
                f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # MIME type check
        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Invalid file type: {mime_type}")

        # PDF magic bytes check
        if ext == ".pdf" and not file_bytes.startswith(b"%PDF"):
            raise ValueError("Invalid PDF file — file appears corrupted.")

    async def check_contract_limit(self, org_id: UUID, plan: str) -> None:
        """Check if org has reached their monthly contract limit."""
        limits = settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["free"])
        max_contracts = limits["contracts"]

        if max_contracts == -1:  # unlimited
            return

        # Count contracts this month
        result = await self.db.execute(
            select(func.count(Contract.id)).where(
                Contract.org_id == org_id,
                Contract.is_active == True,
            )
        )
        current_count = result.scalar() or 0

        if current_count >= max_contracts:
            raise ContractLimitError(
                f"You have reached your {plan} plan limit of {max_contracts} contracts. "
                f"Please upgrade to upload more contracts."
            )

    async def create_and_queue(
        self,
        org_id: UUID,
        user_id: UUID,
        filename: str,
        file_bytes: bytes,
        mime_type: str = "application/pdf",
    ) -> tuple[Contract, int]:
        """
        Create contract DB record and queue for processing.

        Returns:
            (contract, queue_position)
        """
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check for duplicate
        existing = await self.db.execute(
            select(Contract).where(
                Contract.org_id == org_id,
                Contract.file_hash == file_hash,
                Contract.is_active == True,
            )
        )
        existing_contract = existing.scalar_one_or_none()
        if existing_contract:
            logger.info(
                "duplicate_contract_detected",
                contract_id=str(existing_contract.id),
                file_hash=file_hash[:8],
            )
            # Return existing contract (idempotent upload)
            return existing_contract, 0

        # Upload to GCS
        contract_id = uuid.uuid4()
        gcs_path = None

        try:
            from app.infrastructure.storage.gcs import get_storage_client
            storage = get_storage_client()
            result = await storage.upload_contract(
                org_id=org_id,
                contract_id=contract_id,
                filename=filename,
                file_bytes=file_bytes,
                mime_type=mime_type,
            )
            gcs_path = result["gcs_path"]
        except Exception as e:
            logger.warning("gcs_upload_failed", error=str(e), note="Continuing without GCS")
            gcs_path = f"local/{org_id}/{contract_id}/{filename}"

        # Create contract record
        contract = Contract(
            id=contract_id,
            org_id=org_id,
            uploaded_by=user_id,
            title=Path(filename).stem.replace("_", " ").replace("-", " ").title(),
            original_filename=filename,
            file_hash=file_hash,
            file_path=gcs_path,
            file_size_bytes=len(file_bytes),
            mime_type=mime_type,
            status="queued",
            version=1,
        )

        self.db.add(contract)
        await self.db.flush()  # get ID without committing

        # Queue for async processing
        queue_position = await self._queue_processing(
            contract_id=contract_id,
            org_id=org_id,
            file_hash=file_hash,
            plan=settings.PLAN_LIMITS.get("starter", {}),
        )

        await self.db.commit()
        await self.db.refresh(contract)

        return contract, queue_position

    async def _queue_processing(
        self,
        contract_id: UUID,
        org_id: UUID,
        file_hash: str,
        plan: dict,
    ) -> int:
        """Queue contract for Celery processing. Returns queue position."""
        try:
            from app.workers.tasks import process_contract
            task = process_contract.delay(
                contract_id=str(contract_id),
                org_id=str(org_id),
                file_hash=file_hash,
            )
            logger.info(
                "contract_queued",
                contract_id=str(contract_id),
                task_id=task.id,
            )
            return 1
        except Exception as e:
            logger.warning(
                "celery_queue_failed",
                error=str(e),
                note="Will process inline (dev mode)",
            )
            # In dev without Celery — process inline
            try:
                await self._process_inline(contract_id, org_id, file_hash)
            except Exception as pe:
                logger.error("inline_processing_failed", error=str(pe))
            return 0

    async def _process_inline(
        self,
        contract_id: UUID,
        org_id: UUID,
        file_hash: str,
    ) -> None:
        """
        Process contract inline (development mode without Celery).
        In production, Celery workers handle this.
        """
        from app.agents.pipeline.contract_pipeline import ContractPipeline
        pipeline = ContractPipeline()
        await pipeline.process(
            contract_id=contract_id,
            org_id=org_id,
            file_hash=file_hash,
            db=self.db,
        )

    async def list_contracts(
        self,
        org_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        risk_level: str | None = None,
        contract_type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Contract], int]:
        """List contracts with filtering and pagination."""
        query = select(Contract).where(
            Contract.org_id == org_id,
            Contract.is_active == True,
        )

        # Filters
        if status_filter:
            query = query.where(Contract.status == status_filter)
        if risk_level:
            query = query.where(Contract.risk_level == risk_level)
        if contract_type:
            query = query.where(Contract.contract_type == contract_type)
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Contract.title.ilike(search_term),
                    Contract.counterparty.ilike(search_term),
                )
            )

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        query = query.order_by(Contract.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        contracts = list(result.scalars().all())

        return contracts, total

    async def get_contract(
        self,
        contract_id: UUID,
        org_id: UUID,
    ) -> Contract | None:
        """Get contract with clauses. Returns None if not found or wrong org."""
        result = await self.db.execute(
            select(Contract)
            .options(selectinload(Contract.clauses))
            .where(
                Contract.id == contract_id,
                Contract.org_id == org_id,
                Contract.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_processing_status(
        self,
        contract_id: UUID,
        org_id: UUID,
    ) -> ProcessingStatus | None:
        """Get current processing status for frontend polling."""
        result = await self.db.execute(
            select(Contract.status, Contract.processing_error, Contract.processed_at)
            .where(
                Contract.id == contract_id,
                Contract.org_id == org_id,
            )
        )
        row = result.first()
        if not row:
            return None

        current_status, error, completed_at = row
        step_info = PROCESSING_STEPS.get(current_status, PROCESSING_STEPS["queued"])
        progress, step_label, steps_done = step_info

        return ProcessingStatus(
            contract_id=contract_id,
            status=current_status,
            progress_pct=progress,
            current_step=step_label,
            steps_completed=steps_done,
            error=error,
            completed_at=completed_at,
        )

    async def delete_contract(
        self,
        contract_id: UUID,
        org_id: UUID,
    ) -> bool:
        """Soft delete contract. Also deletes vectors and GCS files."""
        result = await self.db.execute(
            select(Contract).where(
                Contract.id == contract_id,
                Contract.org_id == org_id,
                Contract.is_active == True,
            )
        )
        contract = result.scalar_one_or_none()
        if not contract:
            return False

        # Delete Pinecone vectors
        try:
            from app.infrastructure.vector_store.pinecone_store import get_vector_store
            store = get_vector_store()
            await store.delete_contract(org_id, contract_id)
        except Exception as e:
            logger.warning("vector_delete_failed", error=str(e))

        # Delete GCS files
        try:
            from app.infrastructure.storage.gcs import get_storage_client
            storage = get_storage_client()
            await storage.delete_contract(org_id, contract_id)
        except Exception as e:
            logger.warning("gcs_delete_failed", error=str(e))

        # Soft delete DB record
        contract.is_active = False
        await self.db.commit()

        logger.info(
            "contract_deleted",
            contract_id=str(contract_id),
            org_id=str(org_id),
        )

        return True

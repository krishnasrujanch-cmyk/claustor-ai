"""
Claustor AI — Bulk Import
Upload a ZIP file containing multiple PDFs/DOCXs.
Each file is processed as a separate contract.
Returns a batch job ID for progress tracking.
"""

import io
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import Base, get_db

logger = structlog.get_logger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_ZIP_SIZE_MB    = 200
MAX_FILES_PER_ZIP  = 50


class BulkImportJob(Base):
    """Tracks a bulk import batch."""
    __tablename__ = "bulk_import_jobs"

    id           = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id       = Column(PGUUID(as_uuid=True), nullable=False)
    user_id      = Column(PGUUID(as_uuid=True), nullable=False)
    status       = Column(String(50), default="processing")
    total_files  = Column(Integer, default=0)
    processed    = Column(Integer, default=0)
    succeeded    = Column(Integer, default=0)
    failed       = Column(Integer, default=0)
    results      = Column(JSONB, default=list)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True))


@router.post("/", status_code=202)
async def bulk_upload(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a ZIP file containing multiple contracts.

    Supported formats in ZIP: PDF, DOCX, DOC
    Max ZIP size: 200MB
    Max files: 50 per batch

    Returns a job_id to track progress via GET /bulk/{job_id}
    """
    if user.plan not in ("starter", "professional", "enterprise"):
        raise HTTPException(status_code=403, detail="Bulk import requires Starter plan or higher")

    # Validate ZIP
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a ZIP file")

    file_bytes = await file.read()

    if len(file_bytes) > MAX_ZIP_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"ZIP file too large. Maximum {MAX_ZIP_SIZE_MB}MB")

    # Extract and validate contents
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    valid_files = [
        name for name in zf.namelist()
        if Path(name).suffix.lower() in ALLOWED_EXTENSIONS
        and not name.startswith("__MACOSX")
        and not Path(name).name.startswith(".")
    ]

    if not valid_files:
        raise HTTPException(status_code=400, detail="No valid contract files found in ZIP (PDF/DOCX only)")

    if len(valid_files) > MAX_FILES_PER_ZIP:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files ({len(valid_files)}). Maximum {MAX_FILES_PER_ZIP} per batch"
        )

    # Check plan contract limits
    from app.services.billing.billing_service import BillingService, UsageLimitError
    billing = BillingService(db)
    try:
        for _ in valid_files:
            await billing.check_and_increment_contracts(user.org_id, user.plan)
    except UsageLimitError as e:
        raise HTTPException(status_code=402, detail=str(e))

    # Create batch job
    job = BulkImportJob(
        org_id=user.org_id,
        user_id=user.id,
        total_files=len(valid_files),
        status="processing",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Process files inline (dev mode) or via Celery (prod)
    results = []
    succeeded = 0
    failed_count = 0

    from app.services.contract_service import ContractService

    for filename in valid_files:
        try:
            contract_bytes = zf.read(filename)
            ext = Path(filename).suffix.lower()
            mime = "application/pdf" if ext == ".pdf" else \
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            service = ContractService(db)
            service.validate_file(filename, contract_bytes, mime)

            contract, _ = await service.create_and_queue(
                org_id=user.org_id,
                user_id=user.id,
                filename=Path(filename).name,
                file_bytes=contract_bytes,
                mime_type=mime,
            )

            results.append({
                "filename":    Path(filename).name,
                "contract_id": str(contract.id),
                "status":      "queued",
            })
            succeeded += 1

        except Exception as e:
            results.append({
                "filename": Path(filename).name,
                "status":   "failed",
                "error":    str(e)[:200],
            })
            failed_count += 1
            logger.warning("bulk_file_failed", filename=filename, error=str(e))

    # Update job
    from sqlalchemy import update
    await db.execute(
        update(BulkImportJob).where(BulkImportJob.id == job.id).values(
            status="completed" if failed_count == 0 else "partial",
            processed=len(valid_files),
            succeeded=succeeded,
            failed=failed_count,
            results=results,
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    logger.info(
        "bulk_import_complete",
        job_id=str(job.id),
        org_id=str(user.org_id),
        total=len(valid_files),
        succeeded=succeeded,
        failed=failed_count,
    )

    return {
        "job_id":       str(job.id),
        "status":       "completed" if failed_count == 0 else "partial",
        "total_files":  len(valid_files),
        "succeeded":    succeeded,
        "failed":       failed_count,
        "results":      results,
        "message":      f"{succeeded}/{len(valid_files)} contracts queued for AI analysis",
    }


@router.get("/{job_id}")
async def get_job_status(
    job_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get bulk import job status and results."""
    result = await db.execute(
        select(BulkImportJob).where(
            BulkImportJob.id == job_id,
            BulkImportJob.org_id == user.org_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id":      str(job.id),
        "status":      job.status,
        "total":       job.total_files,
        "processed":   job.processed,
        "succeeded":   job.succeeded,
        "failed":      job.failed,
        "results":     job.results,
        "created_at":  job.created_at.isoformat() if job.created_at else None,
        "completed_at":job.completed_at.isoformat() if job.completed_at else None,
        "progress_pct":round((job.processed or 0) / max(job.total_files or 1, 1) * 100),
    }

"""
Claustor AI — Contract Endpoints
Upload, list, retrieve, delete, reprocess contracts.
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import AuthUser, get_current_user
from app.domain.models import Clause, Contract, Obligation
from app.domain.schemas.contract import (
    ContractDetailOut, ContractListOut, ContractOut,
    ContractUploadResponse, ProcessingStatus,
)
from app.infrastructure.database.session import get_db
from app.services.contract_service import ContractService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ContractUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_contract(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Upload contract PDF/DOCX for AI analysis."""
    if not user.can_upload:
        raise HTTPException(status_code=403, detail="Role cannot upload contracts")

    file_bytes = await file.read()
    service = ContractService(db)
    await service.check_contract_limit(user.org_id, user.plan)
    service.validate_file(file.filename or "contract.pdf", file_bytes, file.content_type)

    contract, queue_pos = await service.create_and_queue(
        org_id=user.org_id,
        user_id=user.id,
        filename=file.filename or "contract.pdf",
        file_bytes=file_bytes,
        mime_type=file.content_type or "application/pdf",
    )

    wait_times = {"free": 900, "starter": 300, "professional": 60, "enterprise": 15}

    logger.info("contract_uploaded",
                contract_id=str(contract.id), org_id=str(user.org_id))

    return ContractUploadResponse(
        contract_id=str(contract.id),
        status="queued",
        message="Contract uploaded. AI analysis in progress.",
        queue_position=queue_pos,
        estimated_wait_seconds=wait_times.get(user.plan, 900),
    )


@router.get("/", response_model=ContractListOut)
async def list_contracts(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    risk_level: str | None = Query(None),
    search: str | None = Query(None),
):
    """List contracts for the organisation."""
    service = ContractService(db)

    # Role-based filtering:
    # legal_reviewer → only sees contracts assigned to them for review
    # business_viewer → only sees contracts they uploaded
    # contract_manager/admin → sees all org contracts
    reviewer_only_id = None
    uploader_only_id = None

    if user.role == "legal_reviewer":
        # Get contract IDs assigned to this reviewer
        from sqlalchemy import select as _sel
        from app.api.v1.endpoints.reviews import ContractReview
        review_result = await db.execute(
            _sel(ContractReview.contract_id).where(
                ContractReview.assigned_to == user.id
            )
        )
        assigned_ids = [r[0] for r in review_result.fetchall()]
        reviewer_only_id = assigned_ids if assigned_ids else ["00000000-0000-0000-0000-000000000000"]
    elif user.role == "business_viewer":
        uploader_only_id = user.id

    contracts, total = await service.list_contracts(
        org_id=user.org_id, page=page, page_size=page_size,
        status_filter=status_filter, risk_level=risk_level, search=search,
        contract_ids=reviewer_only_id,
        uploaded_by=uploader_only_id,
    )
    return ContractListOut(
        contracts=[ContractOut.model_validate(c) for c in contracts],
        total=total, page=page, page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.get("/{contract_id}", response_model=ContractDetailOut)
async def get_contract(
    contract_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """Get contract detail with clauses."""
    service = ContractService(db)
    contract = await service.get_contract(contract_id=contract_id, org_id=user.org_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractDetailOut.model_validate(contract)


@router.get("/{contract_id}/status", response_model=ProcessingStatus)
async def get_status(
    contract_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """Poll processing status."""
    service = ContractService(db)
    result = await service.get_processing_status(contract_id=contract_id, org_id=user.org_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contract not found")
    return result


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a contract."""
    service = ContractService(db)
    deleted = await service.delete_contract(contract_id=contract_id, org_id=user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")


@router.get("/{contract_id}/export-pdf")
async def export_contract_pdf(
    contract_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """Export contract summary as PDF."""
    from fastapi.responses import StreamingResponse
    import io

    result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id,
            Contract.org_id == user.org_id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    clause_result = await db.execute(
        select(Clause).where(Clause.contract_id == contract_id)
        .order_by(Clause.risk_score.desc())
    )
    clauses = clause_result.scalars().all()

    obligation_result = await db.execute(
        select(Obligation).where(Obligation.contract_id == contract_id)
    )
    obligations = obligation_result.scalars().all()

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(contract.title or "Contract Summary", styles["Heading1"]))
        story.append(Paragraph(f"Generated by Claustor AI", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        terms = [["Field", "Value"]]
        for label, value in [
            ("Counterparty",  contract.counterparty or "—"),
            ("Risk Level",    (contract.risk_level or "—").upper()),
            ("Risk Score",    str(round(contract.risk_score or 0))),
            ("Contract Value", f"{contract.contract_currency or 'USD'} {contract.contract_value:,.0f}" if contract.contract_value else "—"),
            ("Expiry Date",   str(contract.expiry_date) if contract.expiry_date else "—"),
        ]:
            terms.append([label, value])

        t = Table(terms, colWidths=[5*cm, 12*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#5B4BFF")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(t)

        doc.build(story)
        buffer.seek(0)
        filename = f"claustor-{(contract.title or 'contract').lower().replace(' ', '-')[:30]}.pdf"
        return StreamingResponse(buffer, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"})

    except ImportError:
        lines = [f"CONTRACT: {contract.title}", f"Risk: {contract.risk_level}", ""]
        for c in clauses:
            lines.append(f"[{c.risk_level}] {c.clause_type}: {c.title}")
        content_bytes = "\n".join(lines).encode()
        return StreamingResponse(io.BytesIO(content_bytes), media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=contract.txt"})


@router.post("/{contract_id}/reprocess")
async def reprocess_contract(
    contract_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """Reprocess a contract through the full AI pipeline."""
    result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id,
            Contract.org_id == user.org_id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Delete existing clauses + obligations for fresh re-extraction
    await db.execute(delete(Clause).where(Clause.contract_id == contract_id))
    await db.execute(delete(Obligation).where(Obligation.contract_id == contract_id))

    # Reset contract status
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(
            status="queued",
            risk_score=None,
            risk_level=None,
            clause_count=0,
            summary=None,
        )
    )
    await db.commit()

    # Queue via Celery to plan-specific queue
    try:
        from app.workers.tasks.contract_tasks import process_contract, PLAN_QUEUES
        plan_name  = getattr(user, "plan", "starter") or "starter"
        queue_name = PLAN_QUEUES.get(plan_name, "starter_queue")
        priority   = {"free":1,"starter":5,"professional":8,"enterprise":10}.get(plan_name, 5)
        process_contract.apply_async(
            kwargs={
                "contract_id": str(contract_id),
                "org_id":      str(user.org_id),
                "user_id":     str(user.id),
                "file_path":   contract.file_path or "",
                "plan":        plan_name,
            },
            queue=queue_name,
            priority=priority,
        )
        logger.info("contract_reprocess_queued",
                   contract_id=str(contract_id), queue=queue_name)
    except Exception as qe:
        logger.warning("reprocess_queue_failed", error=str(qe))

    return {
        "status":      "queued",
        "contract_id": str(contract_id),
        "message":     "Reprocessing started. Check notifications when complete.",
    }

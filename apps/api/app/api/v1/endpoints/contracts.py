"""
Claustor AI — Contract Endpoints
Upload, list, retrieve, delete contracts.
Processing happens async via Celery worker.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_db as _get_db
from app.domain.schemas.contract import (
    ContractDetailOut, ContractListOut, ContractOut,
    ContractUploadResponse, ProcessingStatus,
)
from app.infrastructure.database.session import get_db
from app.services.contract_service import ContractService

logger = structlog.get_logger(__name__)
router = APIRouter()

DbSession = AsyncSession  # alias for type hints


@router.post("/", response_model=ContractUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_contract(
    file: UploadFile = File(...),
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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

    wait_times = {"free": 900, "starter": 1800, "professional": 600, "enterprise": 120}

    logger.info("contract_uploaded", contract_id=str(contract.id), org_id=str(user.org_id))

    return ContractUploadResponse(
        contract_id=contract.id,
        status="queued",
        message="Contract uploaded. AI analysis in progress.",
        queue_position=queue_pos,
        estimated_wait_seconds=wait_times.get(user.plan, 900),
    )


@router.get("/", response_model=ContractListOut)
async def list_contracts(
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    risk_level: str | None = Query(None),
    search: str | None = Query(None),
):
    """List contracts for the organisation."""
    service = ContractService(db)
    contracts, total = await service.list_contracts(
        org_id=user.org_id, page=page, page_size=page_size,
        status_filter=status_filter, risk_level=risk_level, search=search,
    )
    return ContractListOut(
        contracts=[ContractOut.model_validate(c) for c in contracts],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{contract_id}", response_model=ContractDetailOut)
async def get_contract(
    contract_id: uuid.UUID,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get contract with extracted clauses."""
    service = ContractService(db)
    contract = await service.get_contract(contract_id=contract_id, org_id=user.org_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractDetailOut.model_validate(contract)


@router.get("/{contract_id}/status", response_model=ProcessingStatus)
async def get_status(
    contract_id: uuid.UUID,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll processing status. Frontend calls this every 3 seconds."""
    service = ContractService(db)
    result = await service.get_processing_status(contract_id=contract_id, org_id=user.org_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contract not found")
    return result


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: uuid.UUID,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete contract, clauses, vectors and files."""
    if not user.is_admin and user.role != "contract_manager":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    service = ContractService(db)
    deleted = await service.delete_contract(contract_id=contract_id, org_id=user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")


@router.get("/{contract_id}/export-pdf")
async def export_contract_pdf(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """
    Export contract summary as PDF.
    Includes: key terms, clauses, risk scores, obligations.
    """
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

    # Get clauses
    from app.domain.models import Clause, Obligation
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
        # Try reportlab (if installed)
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=20, spaceAfter=6)
        story.append(Paragraph(contract.title or "Contract Summary", title_style))
        story.append(Paragraph(f"Generated by Claustor AI · {__import__('datetime').datetime.now().strftime('%d %b %Y')}", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        # Key terms table
        story.append(Paragraph("Key Terms", styles["Heading2"]))
        terms = [["Field", "Value"]]
        for label, value in [
            ("Counterparty",  contract.counterparty or "—"),
            ("Contract Type", contract.contract_type or "—"),
            ("Governing Law", contract.governing_law or "—"),
            ("Contract Value", f"{contract.contract_currency or 'USD'} {contract.contract_value:,.0f}" if contract.contract_value else "—"),
            ("Effective Date", str(contract.effective_date) if contract.effective_date else "—"),
            ("Expiry Date",    str(contract.expiry_date) if contract.expiry_date else "—"),
            ("Auto Renewal",   "Yes" if contract.auto_renewal else "No" if contract.auto_renewal is not None else "—"),
            ("Risk Level",     (contract.risk_level or "—").upper()),
            ("Risk Score",     str(round(contract.risk_score or 0))),
        ]:
            terms.append([label, value])

        t = Table(terms, colWidths=[5*cm, 12*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#5B4BFF")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ("FONTSIZE",   (0,0), (-1,-1), 10),
            ("PADDING",    (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Summary
        if contract.summary:
            story.append(Paragraph("AI Summary", styles["Heading2"]))
            story.append(Paragraph(contract.summary, styles["Normal"]))
            story.append(Spacer(1, 0.5*cm))

        # Clauses
        if clauses:
            story.append(Paragraph(f"Clauses ({len(clauses)})", styles["Heading2"]))
            clause_data = [["Clause Type", "Title", "Risk", "Section"]]
            for c in clauses:
                clause_data.append([
                    (c.clause_type or "").replace("_", " ").title(),
                    c.title or "—",
                    (c.risk_level or "—").upper(),
                    c.section_reference or "—",
                ])
            ct = Table(clause_data, colWidths=[4*cm, 8*cm, 2.5*cm, 2.5*cm])
            ct.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#374151")),
                ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                ("FONTSIZE",   (0,0), (-1,-1), 9),
                ("PADDING",    (0,0), (-1,-1), 5),
            ]))
            story.append(ct)
            story.append(Spacer(1, 0.5*cm))

        # Obligations
        if obligations:
            story.append(Paragraph(f"Obligations ({len(obligations)})", styles["Heading2"]))
            ob_data = [["Title", "Type", "Party", "Due Date", "Amount"]]
            for ob in obligations:
                ob_data.append([
                    ob.title or "—",
                    ob.obligation_type or "—",
                    ob.party or "—",
                    str(ob.due_date) if ob.due_date else "—",
                    f"{ob.currency} {ob.amount:,.0f}" if ob.amount else "—",
                ])
            ot = Table(ob_data, colWidths=[5*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm])
            ot.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#374151")),
                ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                ("FONTSIZE",   (0,0), (-1,-1), 9),
                ("PADDING",    (0,0), (-1,-1), 5),
            ]))
            story.append(ot)

        doc.build(story)
        buffer.seek(0)

        filename = f"claustor-{(contract.title or 'contract').lower().replace(' ', '-')[:30]}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError:
        # Fallback: plain text export if reportlab not installed
        lines = [
            f"CONTRACT SUMMARY — {contract.title}",
            f"Generated by Claustor AI",
            "=" * 60,
            f"Counterparty:  {contract.counterparty or '—'}",
            f"Contract Type: {contract.contract_type or '—'}",
            f"Governing Law: {contract.governing_law or '—'}",
            f"Risk Level:    {(contract.risk_level or '—').upper()}",
            f"Risk Score:    {round(contract.risk_score or 0)}",
            f"Contract Value:{contract.contract_currency or 'USD'} {contract.contract_value:,.0f}" if contract.contract_value else "Contract Value: —",
            f"Effective:     {contract.effective_date or '—'}",
            f"Expires:       {contract.expiry_date or '—'}",
            "",
            "CLAUSES",
            "-" * 40,
        ]
        for c in clauses:
            lines.append(f"[{(c.risk_level or '').upper()}] {c.clause_type} — {c.title or ''}")
            if c.summary:
                lines.append(f"  {c.summary[:150]}")

        if obligations:
            lines += ["", "OBLIGATIONS", "-" * 40]
            for ob in obligations:
                lines.append(f"{ob.title} | {ob.obligation_type} | Due: {ob.due_date or '—'}")

        content_bytes = "\n".join(lines).encode("utf-8")
        filename = f"claustor-{(contract.title or 'contract').lower().replace(' ', '-')[:30]}.txt"
        return StreamingResponse(
            io.BytesIO(content_bytes),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

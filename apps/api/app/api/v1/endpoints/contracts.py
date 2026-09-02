"""
Claustor AI — Contract Endpoints
Upload, list, retrieve, delete, reprocess contracts.
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import AuthUser, get_current_user
from app.api.v1.endpoints.audit import write_audit
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
    parent_contract_id: str | None = Form(None),
    version_note: str | None = Form(None),
):
    """Upload contract PDF/DOCX for AI analysis."""
    if not user.can_upload:
        raise HTTPException(status_code=403, detail="Role cannot upload contracts")

    file_bytes = await file.read()
    service = ContractService(db)
    try:
        await service.check_contract_limit(user.org_id, user.plan)
    except Exception as _lim:
        if "limit" in str(_lim).lower() or "upgrade" in str(_lim).lower():
            raise HTTPException(status_code=403, detail=str(_lim))
        raise
    service.validate_file(file.filename or "contract.pdf", file_bytes, file.content_type)

    # Handle versioning
    import uuid as _uuid
    _parent_id = None
    _family_id = None
    _version_num = 1

    if parent_contract_id:
        try:
            from app.domain.models import Contract as _CM
            from sqlalchemy import select as _sel, update as _upd
            _parent_uuid = _uuid.UUID(parent_contract_id)
            _pr = await db.execute(_sel(_CM).where(
                _CM.id == _parent_uuid, _CM.org_id == user.org_id))
            _parent = _pr.scalar_one_or_none()
            if _parent:
                _family_id = _parent.contract_family_id or _parent.id
                _version_num = (_parent.version_number or 1) + 1
                _parent_id = _parent_uuid
                await db.execute(
                    _upd(_CM).where(_CM.contract_family_id == _family_id)
                    .values(is_latest=False))
                await db.commit()
        except Exception as ve:
            logger.warning("versioning_failed", error=str(ve))

    contract, queue_pos = await service.create_and_queue(
        org_id=user.org_id,
        user_id=user.id,
        filename=file.filename or "contract.pdf",
        file_bytes=file_bytes,
        mime_type=file.content_type or "application/pdf",
        parent_contract_id=_parent_id,
        contract_family_id=_family_id,
        version_number=_version_num,
        version_note=version_note,
    )

    wait_times = {"free": 900, "starter": 300, "professional": 60, "enterprise": 15}

    logger.info("contract_uploaded",
                contract_id=str(contract.id), org_id=str(user.org_id))
    await write_audit(db, user.org_id, user.id, user.role,
        action="contract_upload", resource_type="contract",
        resource_id=contract.id,
        extra_data={"filename": file.filename})
    await db.commit()

    return ContractUploadResponse(
        contract_id=str(contract.id),
        status="queued",
        message="Contract uploaded. AI analysis in progress.",
        queue_position=queue_pos,
        estimated_wait_seconds=wait_times.get(user.plan, 900),
    )



@router.get("/by-counterparty")
async def list_contracts_by_counterparty(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
    risk_level: str | None = Query(None),
    expiry_days: int | None = Query(None),
):
    """
    List contracts grouped by counterparty with aggregate metrics.
    Returns: counterparty name, contract count, total value, max risk,
    earliest expiry, and individual contracts within each group.
    """
    from app.domain.models import Contract as _CM
    from sqlalchemy import select as _sel, func as _func, case as _case
    from datetime import datetime, timedelta

    query = _sel(_CM).where(
        _CM.org_id == user.org_id,
        _CM.is_active == True,
        _CM.is_latest == True,
    )

    # Role-based filtering
    if user.role == "legal_reviewer":
        from app.api.v1.endpoints.reviews import ContractReview
        review_result = await db.execute(
            _sel(ContractReview.contract_id).where(
                ContractReview.assigned_to == user.id
            )
        )
        assigned_ids = [r[0] for r in review_result.fetchall()]
        query = query.where(_CM.id.in_(assigned_ids or [uuid.UUID(int=0)]))
    elif user.role == "business_viewer":
        query = query.where(_CM.uploaded_by == user.id)

    if search:
        query = query.where(
            _CM.title.ilike(f"%{search}%") |
            _CM.counterparty.ilike(f"%{search}%")
        )
    if risk_level:
        query = query.where(_CM.risk_level == risk_level)
    if expiry_days is not None:
        cutoff = datetime.utcnow() + timedelta(days=expiry_days)
        query = query.where(_CM.expiry_date <= cutoff.date())
        query = query.where(_CM.expiry_date >= datetime.utcnow().date())

    result = await db.execute(query.order_by(_CM.counterparty, _CM.updated_at.desc()))
    contracts = result.scalars().all()

    # Group by counterparty
    from collections import defaultdict, OrderedDict
    groups: dict = defaultdict(list)
    for c in contracts:
        key = (c.counterparty or "Unknown").strip()
        groups[key].append(c)

    # Build response with aggregates
    counterparty_groups = []
    risk_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, None: 0}

    for name, group_contracts in sorted(groups.items()):
        total_value = sum(c.contract_value or 0 for c in group_contracts)
        currency = next((c.contract_currency for c in group_contracts if c.contract_currency), "USD")
        max_risk = max(group_contracts, key=lambda c: risk_priority.get(c.risk_level, 0)).risk_level
        avg_risk_score = sum(c.risk_score or 0 for c in group_contracts) / len(group_contracts)

        # Earliest expiry
        expiry_dates = [c.expiry_date for c in group_contracts if c.expiry_date]
        earliest_expiry = min(expiry_dates).isoformat() if expiry_dates else None

        # Count expiring soon (next 90 days)
        now = datetime.utcnow().date()
        cutoff_90 = now + timedelta(days=90)
        expiring_soon = sum(
            1 for c in group_contracts
            if c.expiry_date and now <= c.expiry_date <= cutoff_90
        )

        counterparty_groups.append({
            "counterparty":     name,
            "contract_count":   len(group_contracts),
            "total_value":      total_value,
            "currency":         currency,
            "max_risk_level":   max_risk,
            "avg_risk_score":   round(avg_risk_score, 1),
            "earliest_expiry":  earliest_expiry,
            "expiring_soon":    expiring_soon,
            "contracts": [
                {
                    "id":              str(c.id),
                    "title":           c.title,
                    "contract_type":   c.contract_type,
                    "status":          c.status,
                    "risk_level":      c.risk_level,
                    "risk_score":      c.risk_score,
                    "contract_value":  c.contract_value,
                    "contract_currency": c.contract_currency,
                    "effective_date":  c.effective_date.isoformat() if c.effective_date else None,
                    "expiry_date":     c.expiry_date.isoformat() if c.expiry_date else None,
                    "review_status":   c.review_status,
                    "original_filename": c.original_filename,
                    "created_at":      c.created_at.isoformat() if c.created_at else None,
                }
                for c in group_contracts
            ],
        })

    # Sort by total value descending (highest exposure first)
    counterparty_groups.sort(key=lambda g: g["total_value"], reverse=True)

    return {
        "groups":            counterparty_groups,
        "total_counterparties": len(counterparty_groups),
        "total_contracts":   len(contracts),
        "portfolio_value":   sum(g["total_value"] for g in counterparty_groups),
    }

@router.get("/{contract_id}/versions")
async def list_contract_versions(
    contract_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """List all versions of a contract family."""
    from app.domain.models import Contract as _CM
    from sqlalchemy import select as _sel

    _result = await db.execute(
        _sel(_CM).where(_CM.id == contract_id, _CM.org_id == user.org_id)
    )
    _contract = _result.scalar_one_or_none()
    if not _contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    _family_id = _contract.contract_family_id or _contract.id
    _versions_result = await db.execute(
        _sel(_CM)
        .where(_CM.contract_family_id == _family_id, _CM.org_id == user.org_id)
        .order_by(_CM.version_number.desc())
    )
    _versions = _versions_result.scalars().all()
    if not _versions:
        _versions = [_contract]

    return {
        "family_id":  str(_family_id),
        "latest_id":  str(next((v.id for v in _versions if v.is_latest), _contract.id)),
        "versions": [{
            "id":               str(v.id),
            "version_number":   v.version_number or 1,
            "is_latest":        v.is_latest,
            "version_note":     v.version_note,
            "status":           v.status,
            "risk_level":       v.risk_level,
            "review_status":    v.review_status,
            "original_filename":v.original_filename,
            "created_at":       v.created_at.isoformat() if v.created_at else None,
        } for v in _versions],
    }


@router.get("/grouped")
async def list_contracts_grouped(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    risk_level: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    uploaded_by: str | None = Query(None),
    contract_type: str | None = Query(None),
    counterparty: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    value_min: float | None = Query(None),
    value_max: float | None = Query(None),
    expiry_days: int | None = Query(None),
):
    """List contracts grouped by family — one row per contract family."""
    from app.domain.models import Contract as _CM
    from sqlalchemy import select as _sel, func as _func

    # Get all latest contracts (one per family)
    query = _sel(_CM).where(
        _CM.org_id == user.org_id,
        _CM.is_active == True,
        _CM.is_latest == True,
    )

    # Role-based filtering
    if user.role == "legal_reviewer":
        from app.api.v1.endpoints.reviews import ContractReview
        review_result = await db.execute(
            _sel(ContractReview.contract_id).where(
                ContractReview.assigned_to == user.id
            )
        )
        assigned_ids = [r[0] for r in review_result.fetchall()]
        query = query.where(_CM.id.in_(assigned_ids or [uuid.UUID(int=0)]))
    elif user.role == "business_viewer":
        query = query.where(_CM.uploaded_by == user.id)

    if search:
        query = query.where(
            _CM.title.ilike(f"%{search}%") |
            _CM.counterparty.ilike(f"%{search}%")
        )
    if risk_level:
        query = query.where(_CM.risk_level == risk_level)
    if status_filter:
        query = query.where(_CM.status == status_filter)
    if uploaded_by:
        try:
            query = query.where(_CM.uploaded_by == uuid.UUID(uploaded_by))
        except Exception:
            pass
    if contract_type:
        query = query.where(_CM.contract_type.ilike(f"%{contract_type}%"))
    if counterparty:
        query = query.where(_CM.counterparty.ilike(f"%{counterparty}%"))
    if date_from:
        try:
            from datetime import datetime
            query = query.where(_CM.created_at >= datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            from datetime import datetime
            query = query.where(_CM.created_at <= datetime.fromisoformat(date_to))
        except Exception:
            pass
    if value_min is not None:
        query = query.where(_CM.contract_value >= value_min)
    if value_max is not None:
        query = query.where(_CM.contract_value <= value_max)
    if expiry_days is not None:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() + timedelta(days=expiry_days)
        query = query.where(_CM.expiry_date <= cutoff.date())
        query = query.where(_CM.expiry_date >= datetime.utcnow().date())

    # Count total
    count_q = _sel(_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(_CM.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    latest_contracts = result.scalars().all()

    # Fetch ALL versions in ONE query (fix N+1)
    family_ids = [c.contract_family_id or c.id for c in latest_contracts]
    all_versions_result = await db.execute(
        _sel(_CM)
        .where(_CM.contract_family_id.in_(family_ids), _CM.org_id == user.org_id)
        .order_by(_CM.version_number.desc())
    )
    all_versions = all_versions_result.scalars().all()
    # Group versions by family_id
    from collections import defaultdict
    versions_by_family: dict = defaultdict(list)
    for v in all_versions:
        versions_by_family[str(v.contract_family_id or v.id)].append(v)

    grouped = []
    for contract in latest_contracts:
        family_id = contract.contract_family_id or contract.id
        versions = versions_by_family.get(str(family_id), [contract])

        grouped.append({
            "id":               str(contract.id),
            "family_id":        str(family_id),
            "title":            contract.title,
            "counterparty":     contract.counterparty,
            "contract_type":    contract.contract_type,
            "status":           contract.status,
            "risk_level":       contract.risk_level,
            "risk_score":       contract.risk_score,
            "contract_value":   contract.contract_value,
            "contract_currency":contract.contract_currency,
            "review_status":    contract.review_status,
            "effective_date":   contract.effective_date.isoformat() if contract.effective_date else None,
            "expiry_date":      contract.expiry_date.isoformat() if contract.expiry_date else None,
            "version_number":   contract.version_number or 1,
            "version_count":    len(versions),
            "uploaded_by":      str(contract.uploaded_by),
            "created_at":       contract.created_at.isoformat() if contract.created_at else None,
            "updated_at":       contract.updated_at.isoformat() if contract.updated_at else None,
            "versions": [
                {
                    "id":             str(v.id),
                    "version_number": v.version_number or 1,
                    "is_latest":      v.is_latest,
                    "status":         v.status,
                    "review_status":  v.review_status,
                    "risk_level":     v.risk_level,
                    "created_at":     v.created_at.isoformat() if v.created_at else None,
                    "version_note":   v.version_note,
                    "original_filename": v.original_filename,
                }
                for v in versions
            ],
        })

    return {
        "contracts":   grouped,
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get("/", response_model=ContractListOut)
async def list_contracts(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    risk_level: str | None = Query(None),
    search: str | None = Query(None),
    uploaded_by: str | None = Query(None),
    contract_type: str | None = Query(None),
    counterparty: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    value_min: float | None = Query(None),
    value_max: float | None = Query(None),
    expiry_days: int | None = Query(None),
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
        uploaded_by=uploaded_by or uploader_only_id,
        contract_type=contract_type,
        counterparty=counterparty, date_from=date_from, date_to=date_to,
        value_min=value_min, value_max=value_max, expiry_days=expiry_days,
        contract_ids=reviewer_only_id,
    )
    return ContractListOut(
        contracts=[ContractOut.model_validate(c) for c in contracts],
        total=total, page=page, page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.get("/search-suggestions")
async def search_suggestions(
    q: str = Query("", max_length=100),
    limit: int = Query(5, le=10),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Smart search suggestions for ⌘K command palette.
    Returns categorized results: contracts, counterparties, risks.
    """
    from sqlalchemy import text

    org_id = str(user.org_id)
    q_clean = q.strip()[:50]

    contracts = []
    counterparties = []
    risks = []

    if q_clean:
        # Contracts — title/counterparty match
        r = await db.execute(text("""
            SELECT id::text, title, counterparty, contract_type, risk_level
            FROM contracts
            WHERE org_id = :org_id
              AND status != 'deleted'
              AND (
                title ILIKE :q OR
                counterparty ILIKE :q OR
                contract_type ILIKE :q
              )
            ORDER BY
              CASE WHEN title ILIKE :exact THEN 0
                   WHEN counterparty ILIKE :exact THEN 1
                   ELSE 2 END,
              updated_at DESC
            LIMIT :limit
        """), {
            "org_id": org_id,
            "q": f"%{q_clean}%",
            "exact": f"{q_clean}%",
            "limit": limit,
        })
        for row in r.fetchall():
            contracts.append({
                "id": row[0], "title": row[1],
                "counterparty": row[2], "contract_type": row[3],
            })

        # Counterparties — distinct names
        r2 = await db.execute(text("""
            SELECT DISTINCT counterparty
            FROM contracts
            WHERE org_id = :org_id
              AND status != 'deleted'
              AND counterparty ILIKE :q
              AND counterparty IS NOT NULL
            ORDER BY counterparty
            LIMIT 4
        """), {"org_id": org_id, "q": f"%{q_clean}%"})
        counterparties = [row[0] for row in r2.fetchall() if row[0]]

        # High-risk contracts matching query
        r3 = await db.execute(text("""
            SELECT c.id::text, c.title, c.risk_level
            FROM contracts c
            WHERE c.org_id = :org_id
              AND c.status = 'analyzed'
              AND c.risk_level = 'high'
              AND (c.title ILIKE :q OR c.counterparty ILIKE :q)
            ORDER BY c.updated_at DESC
            LIMIT 3
        """), {"org_id": org_id, "q": f"%{q_clean}%"})
        for row in r3.fetchall():
            risks.append({
                "label": f"⚠ High Risk: {row[1][:40]}",
                "contract": row[1],
                "href": f"/dashboard/contracts/{row[0]}",
            })
    else:
        # Empty query — return recent contracts
        r = await db.execute(text("""
            SELECT id::text, title, counterparty, contract_type
            FROM contracts
            WHERE org_id = :org_id AND status != 'deleted'
            ORDER BY updated_at DESC
            LIMIT :limit
        """), {"org_id": org_id, "limit": limit})
        for row in r.fetchall():
            contracts.append({
                "id": row[0], "title": row[1],
                "counterparty": row[2], "contract_type": row[3],
            })

    return {
        "contracts": contracts,
        "counterparties": counterparties,
        "risks": risks,
    }
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
    # Audit log
    await write_audit(db, user.org_id, user.id, user.role,
        action="contract_view", resource_type="contract",
        resource_id=contract_id,
        extra_data={"title": contract.title if contract else ""})
    await db.commit()
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
    await write_audit(db, user.org_id, user.id, user.role,
        action="contract_delete", resource_type="contract",
        resource_id=contract_id)
    await db.commit()


@router.get("/{contract_id}/download")
async def download_original(
    contract_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """Download the original uploaded contract file."""
    import os
    from fastapi.responses import FileResponse
    result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id,
            Contract.org_id == user.org_id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    file_path = contract.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Original file not found")

    filename = contract.original_filename or f"contract-{str(contract_id)[:8]}.pdf"
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=contract.mime_type or "application/pdf",
    )


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
# Add this to app/api/v1/endpoints/contracts.py
# GET /api/v1/contracts/search-suggestions




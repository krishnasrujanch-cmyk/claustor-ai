"""
Claustor AI — Report Generation Endpoints
==========================================
Portfolio risk report and counterparty exposure report (PDF).
"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.models import Contract, Clause, Obligation
from app.infrastructure.database.session import get_db
from app.api.v1.dependencies.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/portfolio-risk")
async def portfolio_risk_report(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate portfolio risk report as PDF."""
    from app.services.report_generator import generate_portfolio_risk_report

    # Fetch all active contracts for this org
    result = await db.execute(
        select(Contract).where(
            Contract.org_id == user.org_id,
            Contract.is_active == True,
            Contract.is_latest == True,
        ).order_by(Contract.risk_score.desc())
    )
    contracts = result.scalars().all()

    if not contracts:
        raise HTTPException(status_code=404, detail="No contracts found")

    # Fetch clauses grouped by contract
    clause_result = await db.execute(
        select(Clause).where(
            Clause.contract_id.in_([c.id for c in contracts])
        ).order_by(Clause.risk_score.desc())
    )
    all_clauses = clause_result.scalars().all()
    clauses_by_contract = {}
    for cl in all_clauses:
        cid = str(cl.contract_id)
        if cid not in clauses_by_contract:
            clauses_by_contract[cid] = []
        clauses_by_contract[cid].append(cl)

    # Fetch obligations
    ob_result = await db.execute(
        select(Obligation).where(
            Obligation.contract_id.in_([c.id for c in contracts])
        )
    )
    obligations = ob_result.scalars().all()

    buffer = generate_portfolio_risk_report(contracts, clauses_by_contract, obligations)

    filename = f"claustor-portfolio-risk-{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/counterparty-exposure")
async def counterparty_exposure_report(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate counterparty exposure report as PDF."""
    from app.services.report_generator import generate_counterparty_exposure_report
    from collections import defaultdict

    # Fetch contracts
    result = await db.execute(
        select(Contract).where(
            Contract.org_id == user.org_id,
            Contract.is_active == True,
            Contract.is_latest == True,
        )
    )
    contracts = result.scalars().all()

    if not contracts:
        raise HTTPException(status_code=404, detail="No contracts found")

    # Group by counterparty
    groups_map = defaultdict(list)
    for c in contracts:
        key = (c.counterparty or "Unknown").strip()
        groups_map[key].append(c)

    risk_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, None: 0}
    today = datetime.utcnow().date()
    cutoff_90 = today + timedelta(days=90)

    groups = []
    for name, group_contracts in sorted(groups_map.items()):
        total_value = sum(c.contract_value or 0 for c in group_contracts)
        currency = next((c.contract_currency for c in group_contracts if c.contract_currency), "USD")
        max_risk = max(group_contracts, key=lambda c: risk_priority.get(c.risk_level, 0)).risk_level
        avg_risk_score = sum(c.risk_score or 0 for c in group_contracts) / len(group_contracts)
        expiry_dates = [c.expiry_date for c in group_contracts if c.expiry_date]
        earliest_expiry = min(expiry_dates).isoformat() if expiry_dates else None
        expiring_soon = sum(1 for c in group_contracts
                          if c.expiry_date and today <= c.expiry_date <= cutoff_90)

        groups.append({
            "counterparty": name,
            "contract_count": len(group_contracts),
            "total_value": total_value,
            "currency": currency,
            "max_risk_level": max_risk,
            "avg_risk_score": round(avg_risk_score, 1),
            "earliest_expiry": earliest_expiry,
            "expiring_soon": expiring_soon,
            "contracts": [
                {
                    "title": c.title,
                    "contract_type": c.contract_type,
                    "contract_value": c.contract_value,
                    "contract_currency": c.contract_currency,
                    "risk_level": c.risk_level,
                    "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                }
                for c in group_contracts
            ],
        })

    groups.sort(key=lambda g: g["total_value"], reverse=True)
    portfolio_value = sum(g["total_value"] for g in groups)

    buffer = generate_counterparty_exposure_report(groups, len(contracts), portfolio_value)

    filename = f"claustor-counterparty-exposure-{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

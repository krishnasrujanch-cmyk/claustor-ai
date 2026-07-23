"""
Claustor AI — Analytics Endpoints
Portfolio analytics, risk heatmap, clause distribution,
contract value over time, expiry timeline.
"""

from datetime import date, datetime, timedelta
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.domain.models import Contract, Clause, Obligation
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/overview")
async def get_overview(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    contract_id: str | None = Query(None),
):
    """Portfolio overview stats. Filter by contract_id for contract-level view."""
    import uuid as _uuid
    base_filter = [Contract.org_id == user.org_id, Contract.is_active == True]
    if contract_id:
        base_filter.append(Contract.id == _uuid.UUID(contract_id))

    result = await db.execute(
        select(
            func.count(Contract.id).label("total"),
            func.count(case((Contract.status == "analyzed", 1))).label("analyzed"),
            func.count(case((Contract.status == "queued", 1))).label("queued"),
            func.count(case((Contract.status == "failed", 1))).label("failed"),
            func.count(case((Contract.risk_level == "high", 1))).label("high_risk"),
            func.count(case((Contract.risk_level == "medium", 1))).label("medium_risk"),
            func.count(case((Contract.risk_level == "low", 1))).label("low_risk"),
            func.avg(Contract.risk_score).label("avg_risk_score"),
            func.sum(Contract.contract_value).label("total_value"),
            func.count(case((Contract.auto_renewal == True, 1))).label("auto_renewal_count"),
        ).where(*base_filter)
    )
    row = result.first()

    # Expiring in next 90 days
    today = date.today()
    expiring_result = await db.execute(
        select(func.count(Contract.id)).where(
            Contract.org_id == user.org_id,
            Contract.is_active == True,
            Contract.expiry_date >= today,
            Contract.expiry_date <= today + timedelta(days=90),
        )
    )
    expiring_soon = expiring_result.scalar() or 0

    # Clause stats
    clause_result = await db.execute(
        select(func.count(Clause.id).label("total_clauses"),
               func.avg(Clause.risk_score).label("avg_clause_risk"))
        .join(Contract, Clause.contract_id == Contract.id)
        .where(Contract.org_id == user.org_id)
    )
    clause_row = clause_result.first()

    return {
        "contracts": {
            "total":        row.total or 0,
            "analyzed":     row.analyzed or 0,
            "queued":       row.queued or 0,
            "failed":       row.failed or 0,
            "expiring_soon": expiring_soon,
            "auto_renewal": row.auto_renewal_count or 0,
        },
        "risk": {
            "high":       row.high_risk or 0,
            "medium":     row.medium_risk or 0,
            "low":        row.low_risk or 0,
            "avg_score":  round(float(row.avg_risk_score or 0), 1),
        },
        "value": {
            "total_usd":  float(row.total_value or 0),
            "total_m":    round(float(row.total_value or 0) / 1_000_000, 2),
        },
        "clauses": {
            "total":      clause_row.total_clauses or 0,
            "avg_risk":   round(float(clause_row.avg_clause_risk or 0), 1),
        },
    }


@router.get("/risk-heatmap")
async def get_risk_heatmap(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    contract_id: str | None = Query(None),
):
    """Risk heatmap — clause type vs risk level matrix. Optional contract filter."""
    import uuid as _uuid
    clause_filter = [Contract.org_id == user.org_id]
    if contract_id:
        clause_filter.append(Contract.id == _uuid.UUID(contract_id))

    result = await db.execute(
        select(
            Clause.clause_type,
            Clause.risk_level,
            func.count(Clause.id).label("count"),
            func.avg(Clause.risk_score).label("avg_score"),
        )
        .join(Contract, Clause.contract_id == Contract.id)
        .where(*clause_filter)
        .group_by(Clause.clause_type, Clause.risk_level)
        .order_by(Clause.clause_type)
    )
    rows = result.fetchall()

    # Build heatmap matrix
    clause_types = sorted(set(r.clause_type for r in rows))
    risk_levels  = ["low", "medium", "high"]

    matrix = {}
    for ct in clause_types:
        matrix[ct] = {}
        for rl in risk_levels:
            matching = [r for r in rows if r.clause_type == ct and r.risk_level == rl]
            matrix[ct][rl] = {
                "count":     matching[0].count if matching else 0,
                "avg_score": round(float(matching[0].avg_score), 1) if matching else 0,
            }

    # Top risky clause types
    type_risk = {}
    for r in rows:
        if r.clause_type not in type_risk:
            type_risk[r.clause_type] = {"total": 0, "risk_sum": 0}
        type_risk[r.clause_type]["total"] += r.count
        type_risk[r.clause_type]["risk_sum"] += float(r.avg_score or 0) * r.count

    ranked = sorted(
        [{"clause_type": ct, "avg_risk": round(v["risk_sum"] / max(v["total"], 1), 1), "count": v["total"]}
         for ct, v in type_risk.items()],
        key=lambda x: x["avg_risk"],
        reverse=True,
    )

    return {
        "matrix":      matrix,
        "clause_types": clause_types,
        "risk_levels": risk_levels,
        "ranked":      ranked,
    }


@router.get("/clause-distribution")
async def get_clause_distribution(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    contract_id: str | None = Query(None),
):
    """Clause type distribution. Optional contract filter."""
    import uuid as _uuid
    clause_filter = [Contract.org_id == user.org_id]
    if contract_id:
        clause_filter.append(Contract.id == _uuid.UUID(contract_id))

    result = await db.execute(
        select(
            Clause.clause_type,
            func.count(Clause.id).label("count"),
            func.avg(Clause.risk_score).label("avg_risk"),
        )
        .join(Contract, Clause.contract_id == Contract.id)
        .where(*clause_filter)
        .group_by(Clause.clause_type)
        .order_by(func.count(Clause.id).desc())
    )
    rows = result.fetchall()
    total = sum(r.count for r in rows)

    return {
        "distribution": [
            {
                "clause_type": r.clause_type,
                "count":       r.count,
                "pct":         round(r.count / max(total, 1) * 100, 1),
                "avg_risk":    round(float(r.avg_risk or 0), 1),
            }
            for r in rows
        ],
        "total_clauses": total,
    }


@router.get("/contract-types")
async def get_contract_types(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Contract type distribution + value breakdown."""
    result = await db.execute(
        select(
            Contract.contract_type,
            func.count(Contract.id).label("count"),
            func.sum(Contract.contract_value).label("total_value"),
            func.avg(Contract.risk_score).label("avg_risk"),
        )
        .where(
            Contract.org_id == user.org_id,
            Contract.is_active == True,
        )
        .group_by(Contract.contract_type)
        .order_by(func.count(Contract.id).desc())
    )
    rows = result.fetchall()
    total = sum(r.count for r in rows)

    return {
        "types": [
            {
                "contract_type": r.contract_type or "Unknown",
                "count":         r.count,
                "pct":           round(r.count / max(total, 1) * 100, 1),
                "total_value":   float(r.total_value or 0),
                "avg_risk":      round(float(r.avg_risk or 0), 1),
            }
            for r in rows
        ],
    }


@router.get("/expiry-timeline")
async def get_expiry_timeline(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Contracts expiring by quarter over next 3 years."""
    today = date.today()
    end_date = today + timedelta(days=365 * 3)

    result = await db.execute(
        select(
            Contract.id,
            Contract.title,
            Contract.counterparty,
            Contract.expiry_date,
            Contract.contract_value,
            Contract.contract_currency,
            Contract.risk_level,
            Contract.auto_renewal,
        )
        .where(
            Contract.org_id == user.org_id,
            Contract.is_active == True,
            Contract.expiry_date >= today,
            Contract.expiry_date <= end_date,
        )
        .order_by(Contract.expiry_date.asc())
    )
    rows = result.fetchall()

    # Group by quarter
    quarters: dict = {}
    for row in rows:
        if not row.expiry_date:
            continue
        q = f"Q{(row.expiry_date.month - 1) // 3 + 1} {row.expiry_date.year}"
        if q not in quarters:
            quarters[q] = {"quarter": q, "count": 0, "total_value": 0, "contracts": []}
        quarters[q]["count"] += 1
        quarters[q]["total_value"] += float(row.contract_value or 0)
        quarters[q]["contracts"].append({
            "id":           str(row.id),
            "title":        row.title,
            "counterparty": row.counterparty,
            "expiry_date":  row.expiry_date.isoformat(),
            "value":        float(row.contract_value or 0),
            "currency":     row.contract_currency,
            "risk_level":   row.risk_level,
            "auto_renewal": row.auto_renewal,
        })

    return {
        "timeline": list(quarters.values()),
        "total_expiring": len(rows),
    }


@router.get("/counterparty-risk")
async def get_counterparty_risk(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Risk breakdown by counterparty."""
    result = await db.execute(
        select(
            Contract.counterparty,
            func.count(Contract.id).label("contracts"),
            func.avg(Contract.risk_score).label("avg_risk"),
            func.sum(Contract.contract_value).label("total_value"),
        )
        .where(
            Contract.org_id == user.org_id,
            Contract.is_active == True,
            Contract.counterparty.isnot(None),
        )
        .group_by(Contract.counterparty)
        .order_by(func.avg(Contract.risk_score).desc())
    )
    rows = result.fetchall()

    return {
        "counterparties": [
            {
                "name":        r.counterparty,
                "contracts":   r.contracts,
                "avg_risk":    round(float(r.avg_risk or 0), 1),
                "total_value": float(r.total_value or 0),
                "risk_level":  "high" if (r.avg_risk or 0) >= 67 else "medium" if (r.avg_risk or 0) >= 34 else "low",
            }
            for r in rows
        ],
    }


@router.get("/export")
async def export_analytics(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    format: str = Query("csv", pattern="^(csv|json)$"),
    contract_id: str | None = Query(None),
):
    """Export analytics data as CSV or JSON."""
    import csv, io, json as json_lib
    from fastapi.responses import StreamingResponse
    import uuid as _uuid

    clause_filter = [Contract.org_id == user.org_id]
    if contract_id:
        clause_filter.append(Contract.id == _uuid.UUID(contract_id))

    result = await db.execute(
        select(
            Clause.clause_type,
            Clause.risk_level,
            Clause.risk_score,
            Clause.title,
            Clause.section_reference,
            Contract.title.label("contract_title"),
            Contract.counterparty,
        )
        .join(Contract, Clause.contract_id == Contract.id)
        .where(*clause_filter)
        .order_by(Clause.risk_score.desc())
    )
    rows = result.fetchall()

    if format == "json":
        data = [
            {
                "contract": r.contract_title,
                "counterparty": r.counterparty,
                "clause_type": r.clause_type,
                "clause_title": r.title,
                "section": r.section_reference,
                "risk_level": r.risk_level,
                "risk_score": r.risk_score,
            }
            for r in rows
        ]
        return StreamingResponse(
            io.BytesIO(json_lib.dumps(data, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=claustor-analytics.json"},
        )

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Contract","Counterparty","Clause Type","Clause Title","Section","Risk Level","Risk Score"])
    for r in rows:
        writer.writerow([r.contract_title, r.counterparty or "", r.clause_type,
                        r.title or "", r.section_reference or "", r.risk_level, r.risk_score])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=claustor-analytics.csv"},
    )

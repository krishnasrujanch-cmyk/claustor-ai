"""
Claustor AI — Alerts Endpoints
View alerts, configure preferences, trigger manual alert check.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.domain.models import Contract, Obligation
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/upcoming")
async def get_upcoming_alerts(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30,
):
    """
    Get upcoming renewals and obligations within N days.
    Frontend uses this to show alert badges.
    """
    from datetime import date, timedelta
    today = date.today()
    end_date = today + timedelta(days=days)

    # Upcoming renewals
    renewals_result = await db.execute(
        select(
            Contract.id,
            Contract.title,
            Contract.counterparty,
            Contract.expiry_date,
            Contract.auto_renewal,
            Contract.renewal_notice_days,
            Contract.contract_value,
            Contract.contract_currency,
        ).where(
            Contract.org_id == user.org_id,
            Contract.is_active == True,
            Contract.expiry_date >= today,
            Contract.expiry_date <= end_date,
        ).order_by(Contract.expiry_date.asc())
    )
    renewals = renewals_result.fetchall()

    # Upcoming obligations (include those with no due date)
    from sqlalchemy import or_
    obligations_result = await db.execute(
        select(
            Obligation.id,
            Obligation.title,
            Obligation.obligation_type,
            Obligation.due_date,
            Obligation.amount,
            Obligation.currency,
            Obligation.party,
            Obligation.contract_id,
        ).where(
            Obligation.org_id == user.org_id,
            Obligation.status == "pending",
            or_(
                Obligation.due_date == None,
                Obligation.due_date >= today,
            )
        ).order_by(Obligation.due_date.asc().nullslast())
    )
    obligations = obligations_result.fetchall()

    return {
        "period_days": days,
        "renewals": [
            {
                "id": str(r.id),
                "title": r.title,
                "counterparty": r.counterparty,
                "expiry_date": r.expiry_date.isoformat() if r.expiry_date else None,
                "days_until_expiry": (r.expiry_date - today).days if r.expiry_date else None,
                "auto_renewal": r.auto_renewal,
                "renewal_notice_days": r.renewal_notice_days,
                "contract_value": r.contract_value,
                "currency": r.contract_currency,
                "urgency": _urgency(r.expiry_date, today),
            }
            for r in renewals
        ],
        "obligations": [
            {
                "id": str(o.id),
                "title": o.title,
                "type": o.obligation_type,
                "due_date": o.due_date.isoformat() if o.due_date else None,
                "days_until_due": (o.due_date - today).days if o.due_date else None,
                "amount": o.amount,
                "currency": o.currency,
                "party": o.party,
                "contract_id": str(o.contract_id),
                "urgency": _urgency(o.due_date, today),
            }
            for o in obligations
        ],
        "summary": {
            "total_renewals": len(renewals),
            "total_obligations": len(obligations),
            "urgent": sum(1 for r in renewals if _urgency(r.expiry_date, today) == "urgent") +
                     sum(1 for o in obligations if _urgency(o.due_date, today) == "urgent"),
        }
    }


@router.post("/obligations/{obligation_id}/complete")
async def mark_obligation_complete(
    obligation_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an obligation as completed."""
    import uuid
    from datetime import datetime, timezone

    result = await db.execute(
        select(Obligation).where(
            Obligation.id == uuid.UUID(obligation_id),
            Obligation.org_id == user.org_id,
        )
    )
    ob = result.scalar_one_or_none()
    if not ob:
        raise HTTPException(status_code=404, detail="Obligation not found")

    await db.execute(
        update(Obligation)
        .where(Obligation.id == ob.id)
        .values(status="completed", completed_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"status": "completed", "obligation_id": obligation_id}


@router.post("/trigger")
async def trigger_alerts(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger alert check for this org.
    Useful for testing. In production, Celery Beat runs this daily.
    """
    if user.role not in ("super_admin", "dept_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.services.alert_service import AlertService
    service = AlertService(db)
    result = await service.run_daily_alerts()
    return {"triggered": True, **result}


def _urgency(target_date, today) -> str:
    if not target_date:
        return "normal"
    days = (target_date - today).days
    if days <= 7:  return "urgent"
    if days <= 30: return "warning"
    return "normal"

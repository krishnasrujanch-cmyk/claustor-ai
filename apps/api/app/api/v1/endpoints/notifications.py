"""
Claustor AI — In-App Notifications
Shows recent contract analysis completions and alerts.
"""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.domain.models import Contract
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/")
async def get_notifications(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent notifications for the user.
    Includes: recently analyzed contracts, upcoming renewals, obligations.
    """
    notifications = []

    # Recently analyzed contracts (last 24 hours) — only uploaded by THIS user
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    result = await db.execute(
        select(Contract)
        .where(
            Contract.org_id == user.org_id,
            Contract.uploaded_by == user.id,
            Contract.status == "analyzed",
            Contract.updated_at >= cutoff,
        )
        .order_by(desc(Contract.updated_at))
        .limit(10)
    )
    recent = result.scalars().all()

    for c in recent:
        risk      = c.risk_level or "low"
        risk_emoji = "🔴" if risk == "high" else "🟡" if risk == "medium" else "🟢"
        notifications.append({
            "id":       f"analyzed_{c.id}",
            "type":     "contract_analyzed",
            "title":    f"{risk_emoji} Analysis complete",
            "message":  f'"{c.title}" analyzed — {c.clause_count or 0} clauses, risk: {risk}',
            "contract_id": str(c.id),
            "severity": risk,
            "time":     c.updated_at.isoformat() if c.updated_at else None,
            "read":     False,
        })

    # Failed contracts
    result2 = await db.execute(
        select(Contract)
        .where(
            Contract.org_id == user.org_id,
            Contract.uploaded_by == user.id,
            Contract.status == "failed",
            Contract.updated_at >= cutoff,
        )
        .order_by(desc(Contract.updated_at))
        .limit(5)
    )
    failed = result2.scalars().all()

    for c in failed:
        notifications.append({
            "id":       f"failed_{c.id}",
            "type":     "contract_failed",
            "title":    "❌ Analysis failed",
            "message":  f'"{c.title}" failed to analyze. Click to retry.',
            "contract_id": str(c.id),
            "severity": "error",
            "time":     c.updated_at.isoformat() if c.updated_at else None,
            "read":     False,
        })

    # Reviews assigned to THIS user
    try:
        from app.domain.models import ContractReview
        review_result = await db.execute(
            select(ContractReview, Contract.title)
            .join(Contract, ContractReview.contract_id == Contract.id)
            .where(
                ContractReview.assigned_to == user.id,
                ContractReview.status == "pending",
            )
            .order_by(desc(ContractReview.assigned_at))
            .limit(5)
        )
        for review, title in review_result.fetchall():
            notifications.append({
                "id":          f"review_{review.id}",
                "type":        "review_assigned",
                "title":       "📋 Review assigned to you",
                "message":     f'Please review "{title}" — {review.priority} priority',
                "contract_id": str(review.contract_id),
                "severity":    "high" if review.priority == "high" else "info",
                "time":        review.assigned_at.isoformat() if review.assigned_at else None,
                "read":        False,
            })
    except Exception:
        pass

    # Sort by time
    notifications.sort(key=lambda x: x["time"] or "", reverse=True)

    return {
        "notifications": notifications,
        "unread_count":  len(notifications),
    }

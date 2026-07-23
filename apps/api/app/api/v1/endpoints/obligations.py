"""Claustor AI — Obligations Endpoints."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.domain.models import Obligation
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/")
async def list_obligations(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    contract_id: str | None = Query(None),
):
    """List all obligations for the organisation."""
    query = select(Obligation).where(Obligation.org_id == user.org_id)

    if status:
        query = query.where(Obligation.status == status)
    if contract_id:
        import uuid
        query = query.where(Obligation.contract_id == uuid.UUID(contract_id))

    query = query.order_by(Obligation.due_date.asc().nullslast())
    result = await db.execute(query)
    obligations = result.scalars().all()

    return {
        "obligations": [
            {
                "id": str(ob.id),
                "contract_id": str(ob.contract_id),
                "title": ob.title,
                "description": ob.description,
                "obligation_type": ob.obligation_type,
                "party": ob.party,
                "due_date": ob.due_date.isoformat() if ob.due_date else None,
                "recurring": ob.recurring,
                "amount": ob.amount,
                "currency": ob.currency,
                "status": ob.status,
            }
            for ob in obligations
        ],
        "total": len(obligations),
    }

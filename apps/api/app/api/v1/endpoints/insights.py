"""Claustor AI — Memory & Insights Endpoints."""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_db
from app.agents.memory.memory_manager import MemoryManager

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/org")
async def get_org_insights(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cross-contract insights for the organisation."""
    memory = MemoryManager(db=db)
    insights = await memory.get_org_insights(user.org_id)
    return {"insights": insights, "total": len(insights)}


@router.post("/org/refresh")
async def refresh_org_insights(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate org insights from all contracts."""
    memory = MemoryManager(db=db)
    insights = await memory.generate_org_insights(user.org_id)
    return {"insights": insights, "generated": len(insights)}


@router.get("/user/interests")
async def get_user_interests(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get what topics this user asks about most."""
    memory = MemoryManager(db=db)
    interests = await memory.get_user_interests(user.org_id, user.id)
    return {"interests": interests}

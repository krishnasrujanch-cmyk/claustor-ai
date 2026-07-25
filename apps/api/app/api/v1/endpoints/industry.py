"""Claustor AI — Industry Settings Endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.core.industries import INDUSTRIES, INDUSTRY_CHOICES, get_plan_price
from app.domain.models import Organisation
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/")
async def list_industries():
    """List all available industries with pricing."""
    return {"industries": INDUSTRY_CHOICES}


@router.get("/pricing")
async def get_industry_pricing(
    plan: str = "starter",
):
    """Get pricing for all industry + plan combinations."""
    return {
        "plan": plan,
        "pricing": [
            get_plan_price(plan, ind_id)
            for ind_id in INDUSTRIES
        ]
    }


@router.get("/org")
async def get_org_industry(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current org industry setting."""
    result = await db.execute(
        select(Organisation.industry, Organisation.plan)
        .where(Organisation.id == user.org_id)
    )
    row = result.fetchone()
    industry_id = row.industry if row else "general"
    plan        = row.plan if row else "free"
    industry    = INDUSTRIES.get(industry_id, INDUSTRIES["general"])

    return {
        "industry":    industry_id,
        "label":       industry["label"],
        "icon":        industry["icon"],
        "description": industry["description"],
        "pricing":     get_plan_price(plan, industry_id),
        "high_risk_clauses":  industry["high_risk_clauses"],
        "critical_missing":   industry["critical_missing"],
    }


class SetIndustryRequest(BaseModel):
    industry: str


@router.post("/org")
async def set_org_industry(
    req: SetIndustryRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set industry for the organisation."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    if req.industry not in INDUSTRIES:
        raise HTTPException(status_code=400,
            detail=f"Invalid industry. Choose from: {list(INDUSTRIES.keys())}")

    await db.execute(
        update(Organisation)
        .where(Organisation.id == user.org_id)
        .values(industry=req.industry)
    )
    await db.commit()

    industry = INDUSTRIES[req.industry]
    logger.info("org_industry_set",
               org_id=str(user.org_id), industry=req.industry)

    return {
        "industry":  req.industry,
        "label":     industry["label"],
        "message":   f"Industry set to {industry['label']}. New contracts will use industry-specific risk scoring.",
    }

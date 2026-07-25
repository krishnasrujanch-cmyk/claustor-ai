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

    from app.core.industries import INDUSTRY_PLAN_ACCESS, PLAN_CONFIG, get_plan_price
    addon_result = await db.execute(
        select(Organisation.addon_enabled).where(Organisation.id == user.org_id)
    )
    addon_enabled = bool(addon_result.scalar() or False)
    plan_config   = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])
    pricing       = get_plan_price(plan, addon_enabled)

    return {
        "industry":        industry_id,
        "label":           industry["label"],
        "icon":            industry["icon"],
        "description":     industry["description"],
        "addon_enabled":   addon_enabled,
        "pricing":         pricing,
        "plan_config":     plan_config,
        "high_risk_clauses":   industry["high_risk_clauses"],
        "critical_missing":    industry["critical_missing"],
        "active_industries":   pricing["active_industries"],
        "available_industries": [
            {"id": k, "label": v["label"], "icon": v["icon"],
             "accessible": k in pricing["active_industries"]}
            for k, v in INDUSTRIES.items()
        ],
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

    # Check plan access
    from app.core.industries import INDUSTRY_PLAN_ACCESS
    allowed_plans = INDUSTRY_PLAN_ACCESS.get(req.industry, ["professional", "enterprise"])
    if user.plan not in allowed_plans:
        raise HTTPException(status_code=403,
            detail=f"Industry '{req.industry}' requires {allowed_plans[0]} plan or higher. "
                   f"Your plan: {user.plan}. Upgrade at /admin/billing")

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


class SetAddonRequest(BaseModel):
    addon_enabled: bool


@router.post("/org/addon")
async def toggle_addon(
    req: SetAddonRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable industry add-on for the organisation."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    # Read plan from DB (JWT plan may be stale)
    from app.core.industries import PLAN_CONFIG
    plan_result = await db.execute(
        select(Organisation.plan).where(Organisation.id == user.org_id)
    )
    actual_plan = plan_result.scalar() or user.plan
    plan_config = PLAN_CONFIG.get(actual_plan, {})
    if not plan_config.get("has_addon"):
        raise HTTPException(status_code=400,
            detail=f"Plan '{actual_plan}' does not support add-ons")

    await db.execute(
        update(Organisation)
        .where(Organisation.id == user.org_id)
        .values(addon_enabled=req.addon_enabled)
    )
    await db.commit()

    pricing = get_plan_price(actual_plan, req.addon_enabled)
    action  = "enabled" if req.addon_enabled else "disabled"
    logger.info("addon_toggled", org_id=str(user.org_id),
               addon_enabled=req.addon_enabled, plan=actual_plan)

    return {
        "addon_enabled": req.addon_enabled,
        "message":       f"Add-on {action}. New monthly total: {pricing['display']}",
        "pricing":       pricing,
        "active_industries": pricing["active_industries"],
    }

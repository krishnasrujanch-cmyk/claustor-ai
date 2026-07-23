"""
Claustor AI — Plan Enforcement Middleware
Feature gating by plan. Every feature checks plan before executing.
3 layers: Auth → Plan check → Permission check.
"""

from functools import wraps

import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

# Feature → allowed plans mapping
FEATURE_PLANS = {
    # Document processing
    "basic_extraction":   ["free", "starter", "professional", "enterprise"],
    "ocr":                ["starter", "professional", "enterprise"],
    "table_extraction":   ["starter", "professional", "enterprise"],
    "vision":             ["professional", "enterprise"],
    "handwriting":        ["enterprise"],

    # Search & chat
    "chat":               ["free", "starter", "professional", "enterprise"],
    "hybrid_search":      ["starter", "professional", "enterprise"],

    # Contract features
    "comparison":         ["professional", "enterprise"],
    "versioning":         ["starter", "professional", "enterprise"],
    "bulk_import":        ["starter", "professional", "enterprise"],
    "playbook":           ["enterprise"],
    "approval_workflow":  ["professional", "enterprise"],

    # Integrations
    "api_access":         ["professional", "enterprise"],
    "webhooks":           ["professional", "enterprise"],
    "slack_integration":  ["professional", "enterprise"],
    "sso":                ["enterprise"],
    "ldap":               ["enterprise"],
    "scim":               ["enterprise"],

    # Analytics
    "risk_heatmap":       ["professional", "enterprise"],
    "analytics":          ["professional", "enterprise"],
    "covenant_monitoring":["enterprise"],

    # Metadata
    "metadata_comments":  ["professional", "enterprise"],
    "metadata_tracked_changes": ["professional", "enterprise"],
    "metadata_stripping": ["enterprise"],

    # Domain packs
    "financial_pack":     ["starter", "professional", "enterprise"],
    "healthcare_pack":    ["starter", "professional", "enterprise"],

    # White label
    "white_label":        ["enterprise"],
}


def require_feature(feature: str):
    """
    FastAPI dependency factory for feature gating.

    Usage:
        @router.post("/", dependencies=[Depends(require_feature("api_access"))])
        async def my_endpoint():
            ...
    """
    async def _check(user=None):
        from app.api.v1.dependencies.auth import get_current_user
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")

        allowed_plans = FEATURE_PLANS.get(feature, ["enterprise"])

        if user.plan not in allowed_plans:
            min_plan = allowed_plans[0] if allowed_plans else "enterprise"
            logger.warning(
                "feature_access_denied",
                feature=feature,
                user_plan=user.plan,
                required_plan=min_plan,
                org_id=str(user.org_id),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "feature_not_available",
                    "feature": feature,
                    "current_plan": user.plan,
                    "required_plan": min_plan,
                    "upgrade_url": "/billing/upgrade",
                    "message": f"'{feature}' requires {min_plan} plan or higher. "
                               f"Your current plan: {user.plan}.",
                }
            )
        return user
    return _check


def check_feature(plan: str, feature: str) -> bool:
    """
    Simple boolean feature check.
    Use in service layer where FastAPI deps aren't available.

    Usage:
        if check_feature(user.plan, "vision"):
            # use vision
    """
    allowed = FEATURE_PLANS.get(feature, ["enterprise"])
    return plan in allowed


def get_plan_features(plan: str) -> list[str]:
    """Get all features available for a plan."""
    return [
        feature for feature, plans in FEATURE_PLANS.items()
        if plan in plans
    ]

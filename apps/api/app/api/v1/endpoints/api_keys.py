"""
Claustor AI — API Key Endpoints
Create, list, revoke API keys for Professional+ plans.
"""

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.middleware.plan_enforcement import require_feature
from app.infrastructure.database.session import get_db
from app.services.auth.api_key_service import APIKeyService, VALID_SCOPES

logger = structlog.get_logger(__name__)
router = APIRouter()


class CreateKeyRequest(BaseModel):
    name: str
    scopes: list[str]
    expires_at: datetime | None = None
    is_test: bool = False


@router.get("/scopes")
async def list_scopes():
    """List all available API key scopes."""
    return {
        "scopes": list(VALID_SCOPES),
        "descriptions": {
            "contracts:read":   "Read contracts and clauses",
            "contracts:write":  "Upload and process contracts",
            "contracts:delete": "Delete contracts",
            "chat:read":        "Read conversation history",
            "chat:write":       "Send chat queries",
            "analytics:read":   "Read analytics and reports",
            "users:read":       "Read user list",
            "users:write":      "Invite and manage users",
        }
    }


@router.get("/")
async def list_keys(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the organisation."""
    if user.plan not in ("professional", "enterprise"):
        raise HTTPException(
            status_code=403,
            detail="API keys require Professional plan or higher"
        )
    service = APIKeyService(db)
    keys = await service.list_keys(user.org_id)
    return {"keys": keys, "total": len(keys)}


@router.post("/", status_code=201)
async def create_key(
    req: CreateKeyRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key.
    Key is shown ONCE — save it securely.
    Requires Professional plan.
    """
    if user.plan not in ("professional", "enterprise"):
        raise HTTPException(
            status_code=403,
            detail="API keys require Professional plan or higher"
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can create API keys"
        )

    if not req.name or len(req.name) < 3:
        raise HTTPException(status_code=400, detail="Key name must be at least 3 characters")

    service = APIKeyService(db)
    result = await service.create_key(
        org_id=user.org_id,
        user_id=user.id,
        name=req.name,
        scopes=req.scopes,
        expires_at=req.expires_at,
        is_test=req.is_test,
    )

    logger.info(
        "api_key_created_via_endpoint",
        org_id=str(user.org_id),
        name=req.name,
        scopes=req.scopes,
    )

    return result


@router.delete("/{key_id}")
async def revoke_key(
    key_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key immediately."""
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can revoke API keys"
        )

    service = APIKeyService(db)
    revoked = await service.revoke_key(key_id, user.org_id)

    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": "API key revoked", "key_id": str(key_id)}


@router.post("/verify")
async def verify_key(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Verify an API key and return its info.
    Used internally and for testing.
    """
    raw_key = payload.get("key")
    if not raw_key:
        raise HTTPException(status_code=400, detail="Key required")

    service = APIKeyService(db)
    info = await service.verify_key(raw_key)

    if not info:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    return {
        "valid": True,
        "org_id": info["org_id"],
        "scopes": info["scopes"],
        "plan": info["plan"],
        "name": info["name"],
    }

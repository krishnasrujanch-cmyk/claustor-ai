"""
Claustor AI — Auth Dependencies
JWT validation, current user extraction, plan enforcement.
Simple JWT auth for now — Auth0 SSO added in Week 5.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)


# ── Token Models ──────────────────────────────────────────

class TokenData(BaseModel):
    user_id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: str
    plan: str


class CurrentUser(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: str
    plan: str

    @property
    def is_admin(self) -> bool:
        return self.role in ("super_admin", "dept_admin")

    @property
    def is_viewer_only(self) -> bool:
        return self.role == "business_viewer"

    @property
    def can_upload(self) -> bool:
        return self.role in ("super_admin", "dept_admin", "contract_manager", "legal_reviewer")


# ── Token Creation ────────────────────────────────────────

def create_access_token(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    email: str,
    role: str,
    plan: str,
) -> str:
    """Create JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "email": email,
        "role": role,
        "plan": plan,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_dev_token(
    org_id: uuid.UUID | None = None,
    plan: str = "professional",
) -> str:
    """
    Create a development token for testing.
    ONLY works in development environment.
    """
    if settings.ENVIRONMENT == "production":
        raise ValueError("Dev tokens not allowed in production")

    return create_access_token(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        org_id=org_id or uuid.UUID("00000000-0000-0000-0000-000000000002"),
        email="dev@claustor.com",
        role="super_admin",
        plan=plan,
    )


# ── Token Validation ──────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)],
) -> CurrentUser:
    """
    Validate JWT token and return current user.
    Raises 401 if token is invalid or missing.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        email = payload.get("email")
        role = payload.get("role")
        plan = payload.get("plan")

        if not all([user_id, org_id, email, role, plan]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        return CurrentUser(
            id=uuid.UUID(user_id),
            org_id=uuid.UUID(org_id),
            email=email,
            role=role,
            plan=plan,
        )

    except JWTError as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Plan Enforcement ──────────────────────────────────────

def require_plan(*plans: str):
    """
    Dependency factory — requires specific plan(s).

    Usage:
        @router.post("/", dependencies=[Depends(require_plan("professional", "enterprise"))])
    """
    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]):
        if user.plan not in plans:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {' or '.join(plans)} plan. "
                       f"Your current plan: {user.plan}",
            )
        return user
    return _check


def require_role(*roles: str):
    """
    Dependency factory — requires specific role(s).

    Usage:
        @router.delete("/", dependencies=[Depends(require_role("super_admin"))])
    """
    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return user
    return _check


# ── Type Aliases ──────────────────────────────────────────

AuthUser = Annotated[CurrentUser, Depends(get_current_user)]

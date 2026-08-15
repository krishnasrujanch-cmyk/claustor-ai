"""Claustor AI — Auth Endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import (
    AuthUser, create_access_token, create_dev_token, get_current_user,
)
from app.core.config import settings
from app.core.security import hash_password, verify_password, generate_invite_token
from app.domain.models import Organisation, User
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    org_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    org_id: str
    role: str
    plan: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: DbSession):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    slug = req.org_name.lower().replace(" ", "-")[:50] + f"-{str(uuid.uuid4())[:4]}"
    org = Organisation(
        name=req.org_name, slug=slug, plan="free",
        max_users=1, max_contracts=5, max_queries_mo=100,
        pinecone_namespace=f"org_{str(uuid.uuid4()).replace('-','')[:8]}",
        gcs_prefix=f"orgs/{str(uuid.uuid4())}",
    )
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id, email=req.email, full_name=req.full_name,
        password_hash=hash_password(req.password),
        role="super_admin", is_active=True,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id, org.id, req.email, "super_admin", "free")
    await db.commit()
    logger.info("user_registered", user_id=str(user.id))
    # Send welcome notification
    try:
        from app.services.notifications import send_notification, NotificationEvent, NotificationPayload
        await send_notification(NotificationPayload(
            event=NotificationEvent.WELCOME_INVITE,
            recipient_email=user.email,
            recipient_name=user.full_name or user.email.split("@")[0].title(),
            org_name=req.org_name if hasattr(req, "org_name") else "",
            action_url=f"{settings.FRONTEND_URL}/dashboard",
        ))
    except Exception as _ne:
        logger.warning(f"welcome_notification_failed: {_ne}")
    return TokenResponse(access_token=token, user_id=str(user.id), org_id=str(org.id), role="super_admin", plan="free")


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: DbSession):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")

    org_result = await db.execute(select(Organisation.plan).where(Organisation.id == user.org_id))
    plan = org_result.scalar() or "free"

    token = create_access_token(user.id, user.org_id, user.email, user.role, plan)
    user.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("user_login", user_id=str(user.id))
    return TokenResponse(access_token=token, user_id=str(user.id), org_id=str(user.org_id), role=user.role, plan=plan)


@router.post("/dev-token", response_model=TokenResponse)
async def dev_token(db: AsyncSession = Depends(get_db)):
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")
    # Sync dev org plan to DB so /me returns correct plan
    from sqlalchemy import update as sa_update
    from app.domain.models import Organisation
    dev_org_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    await db.execute(
        sa_update(Organisation)
        .where(Organisation.id == dev_org_id)
        .values(plan="professional", max_contracts=1000, max_queries_mo=50000)
    )
    await db.commit()
    token = create_dev_token(plan="professional")
    return TokenResponse(
        access_token=token,
        user_id="00000000-0000-0000-0000-000000000001",
        org_id="00000000-0000-0000-0000-000000000002",
        role="super_admin", plan="professional",
    )


@router.get("/me")
async def me(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    """Always read plan fresh from DB — JWT plan may be stale after upgrade."""
    from sqlalchemy import select
    from app.domain.models import Organisation
    org_result = await db.execute(
        select(Organisation.plan).where(Organisation.id == user.org_id)
    )
    live_plan = org_result.scalar() or user.plan or "free"

    return {
        "user_id":  str(user.id),
        "org_id":   str(user.org_id),
        "email":    user.email,
        "role":     user.role,
        "plan":     live_plan,
        "is_admin": user.is_admin,
        "can_upload": getattr(user, "can_upload", True),
    }


# ── Password Reset ────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send password reset email."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    # Always return success (don't reveal if email exists)
    if not user:
        return {"message": "If that email exists, a reset link has been sent."}

    reset_token = generate_invite_token()
    reset_expires = datetime.now(timezone.utc).replace(microsecond=0)
    from datetime import timedelta
    reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    user.invite_token = f"reset_{reset_token}"
    user.invite_expires_at = reset_expires
    await db.commit()

    # Send email
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token=reset_{reset_token}"
    try:
        from app.core.config import settings
        if settings.RESEND_API_KEY:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": f"Claustor AI <{settings.RESEND_FROM}>",
                "to": req.email,
                "subject": "Reset your Claustor AI password",
                "html": f"""
                <div style="font-family:Inter,sans-serif;max-width:500px;margin:0 auto;padding:32px;">
                  <h2>Reset your password</h2>
                  <p>Click the button below to reset your password. This link expires in 1 hour.</p>
                  <a href="{reset_url}" style="display:inline-block;background:#5B4BFF;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
                    Reset password →
                  </a>
                  <p style="color:#6B7280;font-size:12px;margin-top:24px;">If you didn't request this, ignore this email.</p>
                </div>
                """,
            })
    except Exception as e:
        logger.warning("password_reset_email_failed", error=str(e))

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using token from email."""
    result = await db.execute(
        select(User).where(User.invite_token == req.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if not req.token.startswith("reset_"):
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if user.invite_expires_at and user.invite_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.password_hash = hash_password(req.new_password)
    user.invite_token = None
    user.invite_expires_at = None
    await db.commit()

    return {"message": "Password reset successfully. Please sign in."}


@router.get("/validate-invite/{token}")
async def validate_invite(token: str, db: DbSession):
    """Validate an invite token — called when user opens invite link."""
    from sqlalchemy import select
    result = await db.execute(
        select(User).where(User.invite_token == token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired invite link")
    return {
        "valid": True,
        "email": user.email,
        "role":  user.role,
        "name":  user.full_name,
    }


class AcceptInviteRequest(BaseModel):
    token:    str
    password: str


@router.post("/accept-invite")
async def accept_invite(req: AcceptInviteRequest, db: DbSession):
    """Accept invite and set password."""
    from sqlalchemy import select
    result = await db.execute(
        select(User).where(User.invite_token == req.token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired invite link")

    user.password_hash = hash_password(req.password)
    user.invite_token  = None
    user.is_active     = True
    await db.commit()

    logger.info("invite_accepted", user_id=str(user.id), email=user.email)
    return {"message": "Account activated. You can now log in.", "email": user.email}

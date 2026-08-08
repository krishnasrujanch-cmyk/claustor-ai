"""
Claustor AI — User Management Endpoints
Invite, list, update, deactivate users.
Role management, department assignment, guest access.
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.core.security import hash_password, generate_invite_token
from app.domain.models import Organisation, User
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()

VALID_ROLES = [
    "super_admin", "dept_admin", "contract_manager",
    "legal_reviewer", "business_viewer", "external_guest"
]


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "business_viewer"
    department_id: uuid.UUID | None = None
    is_external: bool = False
    guest_expires_days: int | None = None


class UpdateUserRequest(BaseModel):
    role: str | None = None
    department_id: uuid.UUID | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_external: bool
    last_active_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/")
async def list_users(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    search: str | None = Query(None),
):
    """List all users in the organisation."""
    query = select(User).where(
        User.org_id == user.org_id,
        User.is_active == True,
    )
    if role:
        query = query.where(User.role == role)
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    # Get plan limits
    org_result = await db.execute(
        select(Organisation.plan, Organisation.max_users, Organisation.extra_users_purchased)
        .where(Organisation.id == user.org_id)
    )
    org = org_result.first()

    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_external": u.is_external,
                "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "seats": {
            "used": total,
            "max": (org.max_users or 1) + (org.extra_users_purchased or 0) if org else 1,
            "plan": org.plan if org else "free",
        }
    }


@router.post("/invite", status_code=201)
async def invite_user(
    req: InviteUserRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Invite a user to the organisation.
    Sends invitation email (when Resend configured).
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can invite users")

    if req.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Valid: {VALID_ROLES}")

    # Check seat limit
    org_result = await db.execute(
        select(Organisation.plan, Organisation.max_users, Organisation.extra_users_purchased)
        .where(Organisation.id == user.org_id)
    )
    org = org_result.first()
    if org:
        max_seats = (org.max_users or 1) + (org.extra_users_purchased or 0)
        count_result = await db.execute(
            select(func.count(User.id)).where(
                User.org_id == user.org_id,
                User.is_active == True,
                User.is_external == False,
            )
        )
        current_users = count_result.scalar() or 0
        if current_users >= max_seats and not req.is_external:
            raise HTTPException(
                status_code=400,
                detail=f"User limit reached ({current_users}/{max_seats}). "
                       f"Purchase extra seats or upgrade plan.",
            )

    # Check email not already in org
    existing = await db.execute(
        select(User).where(
            User.email == req.email,
            User.org_id == user.org_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already in organisation")

    # Create invite token
    invite_token = generate_invite_token()
    invite_expires = datetime.now(timezone.utc) + timedelta(days=7)

    guest_expires = None
    if req.is_external and req.guest_expires_days:
        guest_expires = datetime.now(timezone.utc) + timedelta(days=req.guest_expires_days)

    new_user = User(
        org_id=user.org_id,
        email=req.email,
        full_name=req.full_name,
        role=req.role,
        is_external=req.is_external,
        guest_expires_at=guest_expires,
        invited_by=user.id,
        invite_token=invite_token,
        invite_expires_at=invite_expires,
        is_active=False,  # activated when they accept invite
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send invite email
    invite_url = f"https://claustor.com/invite/{invite_token}"
    await _send_invite_email(req.email, req.full_name, invite_url, user.email)

    logger.info(
        "user_invited",
        org_id=str(user.org_id),
        invited_by=str(user.id),
        email=req.email,
        role=req.role,
    )

    return {
        "id": str(new_user.id),
        "email": req.email,
        "role": req.role,
        "invite_token": invite_token,
        "invite_url": invite_url,
        "expires_at": invite_expires.isoformat(),
        "message": f"Invitation sent to {req.email}",
    }


@router.post("/accept-invite")
async def accept_invite(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Accept invitation and set password."""
    token = payload.get("token")
    password = payload.get("password")

    if not token or not password:
        raise HTTPException(status_code=400, detail="Token and password required")

    result = await db.execute(
        select(User).where(
            User.invite_token == token,
            User.is_active == False,
        )
    )
    invited_user = result.scalar_one_or_none()

    if not invited_user:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    if invited_user.invite_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation has expired")

    invited_user.password_hash = hash_password(password)
    invited_user.is_active = True
    invited_user.invite_token = None
    invited_user.invite_expires_at = None
    await db.commit()

    from app.api.v1.dependencies.auth import create_access_token
    org_result = await db.execute(
        select(Organisation.plan).where(Organisation.id == invited_user.org_id)
    )
    plan = org_result.scalar() or "free"

    token_str = create_access_token(
        invited_user.id, invited_user.org_id,
        invited_user.email, invited_user.role, plan,
    )

    return {
        "access_token": token_str,
        "token_type": "bearer",
        "message": "Invitation accepted successfully",
    }


@router.get("/me")
async def get_my_profile(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile + org details."""
    from sqlalchemy import select
    from app.domain.models import Organisation, User as UserModel
    org = await db.scalar(select(Organisation).where(Organisation.id == user.org_id))
    db_user = await db.scalar(select(UserModel).where(UserModel.email == user.email))
    return {
        "user": {
            "id": str(db_user.id) if db_user else "",
            "email": user.email,
            "full_name": db_user.full_name if db_user else "",
            "role": user.role,
        },
        "org": {
            "id": str(org.id) if org else None,
            "name": org.name if org else None,
            "gstin": org.gstin if org else None,
            "address": org.address if org else None,
            "phone": org.phone if org else None,
            "website": org.website if org else None,
            "plan": org.plan if org else None,
            "industry": org.industry if org else None,
        }
    }


@router.patch("/me")
async def update_my_profile(
    payload: dict = Body(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user name."""
    from sqlalchemy import update as _update, select as _sel
    from app.domain.models import User as UserModel
    db_user = await db.scalar(_sel(UserModel).where(UserModel.email == user.email))
    allowed = {k: v for k, v in payload.items() if k in ("full_name",)}
    if allowed and db_user:
        await db.execute(_update(UserModel).where(UserModel.id == db_user.id).values(**allowed))
        await db.commit()
    return {"message": "Profile updated"}


@router.patch("/me/org")
async def update_my_org(
    payload: dict = Body(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update org profile — admin/contract_manager only."""
    if user.role not in ("super_admin",):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only super admins can update organisation details")
    from sqlalchemy import update as _update
    from app.domain.models import Organisation
    allowed_fields = ("name", "gstin", "address", "phone", "website")
    updates = {k: v for k, v in payload.items() if k in allowed_fields}
    if updates:
        await db.execute(_update(Organisation).where(Organisation.id == user.org_id).values(**updates))
        await db.commit()
    return {"message": "Organisation updated"}

@router.patch("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    req: UpdateUserRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user role or department."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can update users")

    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == user.org_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if req.role and req.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role")

    updates = {}
    if req.role is not None:
        updates["role"] = req.role
    if req.department_id is not None:
        updates["department_id"] = req.department_id
    if req.is_active is not None:
        updates["is_active"] = req.is_active

    if updates:
        await db.execute(
            update(User).where(User.id == user_id).values(**updates)
        )
        await db.commit()

    return {"message": "User updated", "user_id": str(user_id)}


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user (soft delete, frees up seat)."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can deactivate users")

    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == user.org_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        update(User).where(User.id == user_id).values(is_active=False)
    )
    await db.commit()
    logger.info("user_deactivated", user_id=str(user_id), by=str(user.id))
    return {"message": "User deactivated", "seat_freed": True}


async def _send_invite_email(
    to_email: str,
    to_name: str,
    invite_url: str,
    from_name: str,
) -> None:
    """
    Send invitation email via Resend.

    Domain verification workaround:
    - Use onboarding@resend.dev as from address (works without domain verification)
    - In production: verify claustor.com on resend.com/domains and use RESEND_FROM
    - In dev: invite_url is always returned in API response for manual sharing
    """
    try:
        from app.core.config import settings
        if not settings.RESEND_API_KEY:
            logger.info("invite_email_skipped", reason="RESEND_API_KEY not set", url=invite_url)
            return

        import resend
        resend.api_key = settings.RESEND_API_KEY

        # Use onboarding@resend.dev for unverified domains (Resend default sender)
        # This works without domain verification for testing
        from_address = getattr(settings, "RESEND_FROM", None)
        if not from_address or "claustor.com" in from_address:
            # Fall back to Resend's test sender which works without domain verification
            from_address = "onboarding@resend.dev"

        resend.Emails.send({
            "from": f"Claustor AI <{from_address}>",
            "to": to_email,
            "subject": "You've been invited to Claustor AI",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:32px;">
              <div style="background:#5B4BFF;padding:20px 24px;border-radius:12px 12px 0 0;">
                <h1 style="color:white;margin:0;font-size:20px;">Claustor AI</h1>
              </div>
              <div style="background:#ffffff;padding:32px;border:1px solid #E5E7EB;border-top:none;border-radius:0 0 12px 12px;">
                <h2 style="color:#111827;margin-top:0;">You've been invited! 🎉</h2>
                <p style="color:#374151;">Hi {to_name or to_email},</p>
                <p style="color:#374151;"><strong>{from_name}</strong> has invited you to join their organisation on Claustor AI — the AI-powered contract intelligence platform.</p>
                <div style="text-align:center;margin:32px 0;">
                  <a href="{invite_url}"
                     style="background:#5B4BFF;color:white;padding:14px 32px;border-radius:8px;
                            text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">
                    Accept Invitation →
                  </a>
                </div>
                <p style="color:#6B7280;font-size:13px;">Or copy this link: <a href="{invite_url}" style="color:#5B4BFF;">{invite_url}</a></p>
                <p style="color:#6B7280;font-size:12px;margin-top:24px;border-top:1px solid #E5E7EB;padding-top:16px;">
                  This invitation expires in 7 days. If you didn't expect this, ignore this email.
                </p>
              </div>
            </div>
            """,
        })
        logger.info("invite_email_sent", to=to_email)
    except Exception as e:
        logger.warning("invite_email_failed", error=str(e), invite_url=invite_url)
        # Email failure is non-critical — invite_url is always in API response


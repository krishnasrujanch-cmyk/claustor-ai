"""Claustor AI — Auth Endpoints."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import (
    create_access_token, create_dev_token, get_current_user,
)
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.domain.models import Organisation, User
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()

DEV_ORG_ID  = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
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
    return TokenResponse(
        access_token=token, user_id=str(user.id),
        org_id=str(org.id), role="super_admin", plan="free",
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")
    org_result = await db.execute(
        select(Organisation.plan).where(Organisation.id == user.org_id)
    )
    plan = org_result.scalar() or "free"
    token = create_access_token(user.id, user.org_id, user.email, user.role, plan)
    user.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    return TokenResponse(
        access_token=token, user_id=str(user.id),
        org_id=str(user.org_id), role=user.role, plan=plan,
    )


@router.post("/dev-setup")
async def dev_setup(db: AsyncSession = Depends(get_db)):
    """Create dev org + user in DB. Dev only."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")
    existing = await db.execute(
        select(Organisation).where(Organisation.id == DEV_ORG_ID)
    )
    if existing.scalar_one_or_none():
        return {"status": "already exists", "org_id": str(DEV_ORG_ID)}
    org = Organisation(
        id=DEV_ORG_ID,
        name="Dev Organisation", slug="dev-org",
        plan="professional", max_users=50,
        max_contracts=1000, max_queries_mo=50000,
        pinecone_namespace="org_devtest01",
        gcs_prefix="orgs/dev",
    )
    db.add(org)
    await db.flush()
    user = User(
        id=DEV_USER_ID, org_id=DEV_ORG_ID,
        email="dev@claustor.com", full_name="Dev User",
        password_hash=hash_password("dev123456"),
        role="super_admin", is_active=True,
    )
    db.add(user)
    await db.commit()
    return {"status": "created", "org_id": str(DEV_ORG_ID)}


@router.post("/dev-token", response_model=TokenResponse)
async def dev_token():
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")
    token = create_dev_token(plan="professional")
    return TokenResponse(
        access_token=token,
        user_id=str(DEV_USER_ID),
        org_id=str(DEV_ORG_ID),
        role="super_admin", plan="professional",
    )


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "user_id": str(user.id),
        "org_id": str(user.org_id),
        "email": user.email,
        "role": user.role,
        "plan": user.plan,
    }

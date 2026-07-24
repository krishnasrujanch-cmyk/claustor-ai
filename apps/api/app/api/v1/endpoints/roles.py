"""
Claustor AI — Role & Permission Management
5 built-in roles + custom role creation.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import Base, get_db

logger = structlog.get_logger(__name__)
router = APIRouter()

# ── Built-in roles ────────────────────────────────────
BUILT_IN_ROLES = {
    "super_admin": {
        "label": "Super Admin",
        "description": "Full access — billing, users, settings, all contracts",
        "is_built_in": True,
        "permissions": ["*"],  # all permissions
    },
    "dept_admin": {
        "label": "Department Admin",
        "description": "Department level admin — no billing access",
        "is_built_in": True,
        "permissions": [
            "contracts:view","contracts:upload","contracts:delete","contracts:reprocess",
            "chat:use","reviews:assign","reviews:view","analytics:view","analytics:export",
            "users:view","users:invite","obligations:view","obligations:complete",
            "playbook:view","playbook:manage","bulk:import",
        ],
    },
    "contract_manager": {
        "label": "Contract Manager",
        "description": "Upload contracts, assign reviews, manage obligations",
        "is_built_in": True,
        "permissions": [
            "contracts:view","contracts:upload","contracts:delete","contracts:reprocess",
            "chat:use","reviews:assign","reviews:view","analytics:view",
            "obligations:view","obligations:complete","playbook:view","bulk:import",
        ],
    },
    "legal_reviewer": {
        "label": "Legal Reviewer",
        "description": "Review contracts, submit decisions, read-only otherwise",
        "is_built_in": True,
        "permissions": [
            "contracts:view","chat:use","reviews:view","reviews:decide",
            "analytics:view","obligations:view","playbook:view",
        ],
    },
    "business_viewer": {
        "label": "Business Viewer",
        "description": "Read-only — contracts, analytics, AI copilot",
        "is_built_in": True,
        "permissions": [
            "contracts:view","chat:use","analytics:view","obligations:view",
        ],
    },
}

# All available permissions
ALL_PERMISSIONS = [
    {"id":"contracts:view",        "label":"View contracts",           "group":"Contracts"},
    {"id":"contracts:upload",      "label":"Upload contracts",         "group":"Contracts"},
    {"id":"contracts:delete",      "label":"Delete contracts",         "group":"Contracts"},
    {"id":"contracts:reprocess",   "label":"Reprocess contracts",      "group":"Contracts"},
    {"id":"chat:use",              "label":"Use AI Copilot",           "group":"AI"},
    {"id":"reviews:view",          "label":"View reviews",             "group":"Reviews"},
    {"id":"reviews:assign",        "label":"Assign for review",        "group":"Reviews"},
    {"id":"reviews:decide",        "label":"Submit review decision",   "group":"Reviews"},
    {"id":"analytics:view",        "label":"View analytics",           "group":"Analytics"},
    {"id":"analytics:export",      "label":"Export analytics",         "group":"Analytics"},
    {"id":"obligations:view",      "label":"View obligations",         "group":"Obligations"},
    {"id":"obligations:complete",  "label":"Mark obligations complete","group":"Obligations"},
    {"id":"users:view",            "label":"View users",               "group":"Users"},
    {"id":"users:invite",          "label":"Invite users",             "group":"Users"},
    {"id":"users:manage",          "label":"Manage users (edit/deactivate)","group":"Users"},
    {"id":"billing:view",          "label":"View billing",             "group":"Billing"},
    {"id":"billing:manage",        "label":"Manage billing/subscriptions","group":"Billing"},
    {"id":"playbook:view",         "label":"View playbook",            "group":"Playbook"},
    {"id":"playbook:manage",       "label":"Manage playbook clauses",  "group":"Playbook"},
    {"id":"bulk:import",           "label":"Bulk import contracts",    "group":"Import"},
    {"id":"webhooks:manage",       "label":"Manage webhooks",          "group":"Integrations"},
    {"id":"settings:manage",       "label":"Manage organisation settings","group":"Settings"},
    {"id":"audit:view",            "label":"View audit log",           "group":"Settings"},
]


class CustomRole(Base):
    """Custom role created by organisation admin."""
    __tablename__ = "custom_roles"

    id          = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(PGUUID(as_uuid=True), nullable=False)
    name        = Column(String(50), nullable=False)   # slug: "finance_team"
    label       = Column(String(100), nullable=False)  # display: "Finance Team"
    description = Column(String(255))
    permissions = Column(JSONB, default=list)
    is_active   = Column(Boolean, default=True)
    created_by  = Column(PGUUID(as_uuid=True))
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CreateRoleRequest(BaseModel):
    label:       str
    description: str | None = None
    permissions: list[str] = []


class UpdateRoleRequest(BaseModel):
    label:       str | None = None
    description: str | None = None
    permissions: list[str] | None = None


# ── Endpoints ─────────────────────────────────────────

@router.get("/permissions")
async def list_permissions():
    """List all available permissions."""
    from itertools import groupby
    grouped = {}
    for p in ALL_PERMISSIONS:
        g = p["group"]
        if g not in grouped:
            grouped[g] = []
        grouped[g].append({"id": p["id"], "label": p["label"]})

    return {
        "permissions": ALL_PERMISSIONS,
        "grouped": [{"group": g, "permissions": perms} for g, perms in grouped.items()],
    }


@router.get("/")
async def list_roles(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all roles — built-in + custom for this org."""
    # Built-in roles
    roles = [
        {
            "id": role_id,
            "label": role["label"],
            "description": role["description"],
            "is_built_in": True,
            "permissions": role["permissions"],
            "user_count": 0,
        }
        for role_id, role in BUILT_IN_ROLES.items()
    ]

    # Custom roles for this org
    result = await db.execute(
        select(CustomRole).where(
            CustomRole.org_id == user.org_id,
            CustomRole.is_active == True,
        ).order_by(CustomRole.created_at)
    )
    custom = result.scalars().all()

    for c in custom:
        roles.append({
            "id":          str(c.id),
            "name":        c.name,
            "label":       c.label,
            "description": c.description,
            "is_built_in": False,
            "permissions": c.permissions,
            "created_at":  c.created_at.isoformat() if c.created_at else None,
        })

    return {"roles": roles, "total": len(roles)}


@router.post("/", status_code=201)
async def create_role(
    req: CreateRoleRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom role for the organisation."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can create roles")

    # Validate permissions
    valid_ids = {p["id"] for p in ALL_PERMISSIONS}
    invalid = set(req.permissions) - valid_ids
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid permissions: {invalid}")

    # Generate slug from label
    import re
    name = re.sub(r'[^a-z0-9_]', '_', req.label.lower().strip())[:50]

    # Check not duplicate
    existing = await db.execute(
        select(CustomRole).where(
            CustomRole.org_id == user.org_id,
            CustomRole.name == name,
            CustomRole.is_active == True,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Role '{name}' already exists")

    role = CustomRole(
        org_id=user.org_id,
        name=name,
        label=req.label,
        description=req.description,
        permissions=req.permissions,
        created_by=user.id,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    logger.info("custom_role_created", org_id=str(user.org_id), name=name)
    return {
        "id":          str(role.id),
        "name":        role.name,
        "label":       role.label,
        "description": role.description,
        "permissions": role.permissions,
        "is_built_in": False,
    }


@router.patch("/{role_id}")
async def update_role(
    role_id: uuid.UUID,
    req: UpdateRoleRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom role's permissions or label."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can update roles")

    result = await db.execute(
        select(CustomRole).where(
            CustomRole.id == role_id,
            CustomRole.org_id == user.org_id,
        )
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Custom role not found. Cannot edit built-in roles.")

    if req.label:      role.label = req.label
    if req.description is not None: role.description = req.description
    if req.permissions is not None: role.permissions = req.permissions
    role.updated_at = datetime.now(timezone.utc)

    await db.commit()
    return {"id": str(role.id), "label": role.label, "permissions": role.permissions}


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom role."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete roles")

    result = await db.execute(
        select(CustomRole).where(
            CustomRole.id == role_id,
            CustomRole.org_id == user.org_id,
        )
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Custom role not found")

    role.is_active = False
    await db.commit()

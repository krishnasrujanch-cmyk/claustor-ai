"""
Claustor AI — Playbook
Standard clause templates your legal team has approved.
Compare extracted clauses against playbook to flag deviations.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import Base, get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


class PlaybookClause(Base):
    """Standard/approved clause template."""
    __tablename__ = "playbook_clauses"

    id            = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id        = Column(PGUUID(as_uuid=True), nullable=False)
    clause_type   = Column(String(100), nullable=False)
    title         = Column(String(255), nullable=False)
    standard_text = Column(Text, nullable=False)
    notes         = Column(Text)
    risk_guidance = Column(Text)
    is_required   = Column(Boolean, default=False)
    is_active     = Column(Boolean, default=True)
    created_by    = Column(PGUUID(as_uuid=True))
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    tags          = Column(JSONB, default=list)


class CreatePlaybookClause(BaseModel):
    clause_type:   str
    title:         str
    standard_text: str
    notes:         str | None = None
    risk_guidance: str | None = None
    is_required:   bool = False
    tags:          list[str] = []


@router.get("/")
async def list_playbook(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clause_type: str | None = None,
):
    """List all playbook clauses for the organisation."""
    query = select(PlaybookClause).where(
        PlaybookClause.org_id == user.org_id,
        PlaybookClause.is_active == True,
    )
    if clause_type:
        query = query.where(PlaybookClause.clause_type == clause_type)

    query = query.order_by(PlaybookClause.clause_type, PlaybookClause.title)
    result = await db.execute(query)
    clauses = result.scalars().all()

    return {
        "playbook": [
            {
                "id":            str(c.id),
                "clause_type":   c.clause_type,
                "title":         c.title,
                "standard_text": c.standard_text,
                "notes":         c.notes,
                "risk_guidance": c.risk_guidance,
                "is_required":   c.is_required,
                "tags":          c.tags,
                "created_at":    c.created_at.isoformat() if c.created_at else None,
            }
            for c in clauses
        ],
        "total": len(clauses),
    }


@router.post("/", status_code=201)
async def create_playbook_clause(
    req: CreatePlaybookClause,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a standard clause to the playbook."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can manage playbook")

    clause = PlaybookClause(
        org_id=user.org_id,
        clause_type=req.clause_type,
        title=req.title,
        standard_text=req.standard_text,
        notes=req.notes,
        risk_guidance=req.risk_guidance,
        is_required=req.is_required,
        tags=req.tags,
        created_by=user.id,
    )
    db.add(clause)
    await db.commit()
    await db.refresh(clause)

    logger.info("playbook_clause_created", org_id=str(user.org_id), clause_type=req.clause_type)
    return {"id": str(clause.id), "clause_type": req.clause_type, "title": req.title}


@router.post("/compare/{contract_id}")
async def compare_with_playbook(
    contract_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare a contract's clauses against the playbook.
    Returns: matches, deviations, missing required clauses.
    """
    from app.domain.models import Clause, Contract

    # Get contract clauses
    contract_result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id,
            Contract.org_id == user.org_id,
        )
    )
    contract = contract_result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    clause_result = await db.execute(
        select(Clause).where(Clause.contract_id == contract_id)
    )
    contract_clauses = clause_result.scalars().all()

    # Get playbook
    playbook_result = await db.execute(
        select(PlaybookClause).where(
            PlaybookClause.org_id == user.org_id,
            PlaybookClause.is_active == True,
        )
    )
    playbook = playbook_result.scalars().all()

    if not playbook:
        return {
            "message": "No playbook clauses defined. Add standard clauses to your playbook first.",
            "matches": [], "deviations": [], "missing": [],
        }

    contract_types = {c.clause_type for c in contract_clauses}
    playbook_types = {p.clause_type for p in playbook}

    matches    = []
    deviations = []
    missing    = []

    for pb in playbook:
        matching = [c for c in contract_clauses if c.clause_type == pb.clause_type]
        if not matching:
            if pb.is_required:
                missing.append({
                    "clause_type":    pb.clause_type,
                    "playbook_title": pb.title,
                    "is_required":    True,
                    "message":        f"Required clause '{pb.title}' is missing from contract",
                })
        else:
            for contract_clause in matching:
                # Simple deviation check: compare key terms
                pb_text = pb.standard_text.lower()
                cc_text = (contract_clause.raw_text or "").lower()

                # Check for key risk terms
                risk_flags = []
                if "unlimited" in cc_text and "unlimited" not in pb_text:
                    risk_flags.append("Contract has UNLIMITED liability — playbook does not")
                if "no limitation" in cc_text:
                    risk_flags.append("Contract excludes liability limitation")
                if "perpetual" in cc_text and "perpetual" not in pb_text:
                    risk_flags.append("Contract has PERPETUAL terms — check expiry")

                if risk_flags or contract_clause.risk_level in ("high", "medium"):
                    deviations.append({
                        "clause_type":     pb.clause_type,
                        "clause_title":    contract_clause.title,
                        "playbook_title":  pb.title,
                        "risk_level":      contract_clause.risk_level,
                        "risk_flags":      risk_flags,
                        "risk_guidance":   pb.risk_guidance,
                    })
                else:
                    matches.append({
                        "clause_type":  pb.clause_type,
                        "clause_title": contract_clause.title,
                    })

    return {
        "contract_title": contract.title,
        "total_playbook_clauses": len(playbook),
        "summary": {
            "matches":    len(matches),
            "deviations": len(deviations),
            "missing":    len(missing),
        },
        "matches":    matches,
        "deviations": deviations,
        "missing":    missing,
    }


@router.delete("/{clause_id}", status_code=204)
async def delete_playbook_clause(
    clause_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a clause from the playbook."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(PlaybookClause).where(
            PlaybookClause.id == clause_id,
            PlaybookClause.org_id == user.org_id,
        )
    )
    clause = result.scalar_one_or_none()
    if not clause:
        raise HTTPException(status_code=404, detail="Playbook clause not found")

    clause.is_active = False
    await db.commit()

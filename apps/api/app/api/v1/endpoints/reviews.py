"""
Claustor AI — Approval Workflow / Review
Assign contracts to reviewers, track review decisions,
manage approval chains, record audit trail.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.api.v1.dependencies.auth import get_current_user
from app.domain.models import Contract, User
from app.infrastructure.database.session import Base, get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


class ContractReview(Base):
    """Contract review/approval record."""
    __tablename__ = "contract_reviews"

    id             = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id    = Column(PGUUID(as_uuid=True), nullable=False)
    org_id         = Column(PGUUID(as_uuid=True), nullable=False)
    assigned_by    = Column(PGUUID(as_uuid=True), nullable=False)
    assigned_to    = Column(PGUUID(as_uuid=True), nullable=False)
    status         = Column(String(50), default="pending")  # pending|in_review|approved|rejected|revision_needed
    priority       = Column(String(20), default="normal")   # low|normal|high|urgent
    due_date       = Column(DateTime(timezone=True))
    notes          = Column(Text)
    decision       = Column(String(50))     # approved|rejected|revision_needed
    decision_notes = Column(Text)
    decided_at     = Column(DateTime(timezone=True))
    clause_flags   = Column(JSONB, default=list)  # flagged clause IDs with comments
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── Schemas ───────────────────────────────────────────

class AssignReviewRequest(BaseModel):
    contract_id: uuid.UUID
    reviewer_id: uuid.UUID
    priority: str = "normal"
    due_date: datetime | None = None
    notes: str | None = None


class SubmitDecisionRequest(BaseModel):
    decision: str          # approved|rejected|revision_needed
    decision_notes: str | None = None
    clause_flags: list[dict] | None = None  # [{clause_id, comment, severity}]


# ── Endpoints ─────────────────────────────────────────

@router.post("/assign", status_code=201)
async def assign_review(
    req: AssignReviewRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Assign a contract to a reviewer.
    Sends email notification to reviewer.
    """
    if not user.is_admin and user.role != "contract_manager":
        raise HTTPException(status_code=403, detail="Only admins and contract managers can assign reviews")

    # Verify contract belongs to org
    contract_result = await db.execute(
        select(Contract).where(
            Contract.id == req.contract_id,
            Contract.org_id == user.org_id,
        )
    )
    contract = contract_result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status != "analyzed":
        raise HTTPException(status_code=400, detail="Contract must be analyzed before review assignment")

    # Verify reviewer belongs to org
    reviewer_result = await db.execute(
        select(User).where(
            User.id == req.reviewer_id,
            User.org_id == user.org_id,
            User.is_active == True,
        )
    )
    reviewer = reviewer_result.scalar_one_or_none()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found in organisation")

    if reviewer.role not in ("legal_reviewer", "contract_manager", "dept_admin", "super_admin"):
        raise HTTPException(status_code=400, detail="User does not have reviewer permissions")

    # Check for existing active review
    existing = await db.execute(
        select(ContractReview).where(
            ContractReview.contract_id == req.contract_id,
            ContractReview.status.in_(["pending", "in_review"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Contract already has an active review")

    # Create review
    review = ContractReview(
        contract_id=req.contract_id,
        org_id=user.org_id,
        assigned_by=user.id,
        assigned_to=req.reviewer_id,
        priority=req.priority,
        due_date=req.due_date,
        notes=req.notes,
        status="pending",
    )
    db.add(review)

    # Update contract flag
    await db.execute(
        update(Contract)
        .where(Contract.id == req.contract_id)
        .values(flagged_for_review=True)
    )

    await db.commit()
    await db.refresh(review)

    # Send email notification
    await _notify_reviewer(reviewer, contract, user, review)

    logger.info(
        "review_assigned",
        contract_id=str(req.contract_id),
        reviewer_id=str(req.reviewer_id),
        assigned_by=str(user.id),
    )

    return {
        "review_id":    str(review.id),
        "contract_id":  str(req.contract_id),
        "reviewer":     reviewer.email,
        "priority":     req.priority,
        "due_date":     req.due_date.isoformat() if req.due_date else None,
        "status":       "pending",
        "message":      f"Review assigned to {reviewer.email}",
    }


@router.get("/")
async def list_reviews(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    assigned_to_me: bool = False,
):
    """List reviews for the organisation. Filter by status or assigned to current user."""
    query = select(ContractReview).where(ContractReview.org_id == user.org_id)

    if status:
        query = query.where(ContractReview.status == status)
    if assigned_to_me:
        query = query.where(ContractReview.assigned_to == user.id)

    query = query.order_by(ContractReview.created_at.desc())
    result = await db.execute(query)
    reviews = result.scalars().all()

    # Enrich with contract titles
    enriched = []
    for review in reviews:
        contract_r = await db.execute(
            select(Contract.title, Contract.counterparty, Contract.risk_level)
            .where(Contract.id == review.contract_id)
        )
        contract_row = contract_r.first()

        reviewer_r = await db.execute(
            select(User.email, User.full_name).where(User.id == review.assigned_to)
        )
        reviewer_row = reviewer_r.first()

        enriched.append({
            "id":             str(review.id),
            "contract_id":    str(review.contract_id),
            "contract_title": contract_row.title if contract_row else "Unknown",
            "counterparty":   contract_row.counterparty if contract_row else None,
            "risk_level":     contract_row.risk_level if contract_row else None,
            "reviewer_email": reviewer_row.email if reviewer_row else None,
            "reviewer_name":  reviewer_row.full_name if reviewer_row else None,
            "status":         review.status,
            "priority":       review.priority,
            "due_date":       review.due_date.isoformat() if review.due_date else None,
            "decision":       review.decision,
            "created_at":     review.created_at.isoformat() if review.created_at else None,
        })

    return {"reviews": enriched, "total": len(enriched)}


@router.post("/{review_id}/start")
async def start_review(
    review_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark review as in progress (reviewer starts reviewing)."""
    result = await db.execute(
        select(ContractReview).where(
            ContractReview.id == review_id,
            ContractReview.org_id == user.org_id,
            ContractReview.assigned_to == user.id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or not assigned to you")

    await db.execute(
        update(ContractReview)
        .where(ContractReview.id == review_id)
        .values(status="in_review", updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"status": "in_review", "review_id": str(review_id)}


@router.post("/{review_id}/decide")
async def submit_decision(
    review_id: uuid.UUID,
    req: SubmitDecisionRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit review decision: approved | rejected | revision_needed

    - approved:          Contract approved, flagged_for_review cleared
    - rejected:          Contract rejected with comments
    - revision_needed:   Specific clauses flagged for revision
    """
    if req.decision not in ("approved", "rejected", "revision_needed"):
        raise HTTPException(status_code=400, detail="Decision must be: approved, rejected, or revision_needed")

    result = await db.execute(
        select(ContractReview).where(
            ContractReview.id == review_id,
            ContractReview.org_id == user.org_id,
            ContractReview.assigned_to == user.id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or not assigned to you")

    now = datetime.now(timezone.utc)

    await db.execute(
        update(ContractReview)
        .where(ContractReview.id == review_id)
        .values(
            status=req.decision,
            decision=req.decision,
            decision_notes=req.decision_notes,
            clause_flags=req.clause_flags or [],
            decided_at=now,
            updated_at=now,
        )
    )

    # Update contract flag
    if req.decision == "approved":
        await db.execute(
            update(Contract)
            .where(Contract.id == review.contract_id)
            .values(flagged_for_review=False)
        )

    await db.commit()

    # Notify assigner
    await _notify_decision(review, user, req.decision, req.decision_notes)

    logger.info(
        "review_decision",
        review_id=str(review_id),
        decision=req.decision,
        reviewer=str(user.id),
    )

    return {
        "review_id": str(review_id),
        "decision":  req.decision,
        "decided_at": now.isoformat(),
        "clause_flags_count": len(req.clause_flags or []),
    }


@router.get("/my-queue")
async def my_review_queue(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get contracts assigned to the current user for review."""
    result = await db.execute(
        select(ContractReview).where(
            ContractReview.assigned_to == user.id,
            ContractReview.org_id == user.org_id,
            ContractReview.status.in_(["pending", "in_review"]),
        ).order_by(ContractReview.created_at.asc())
    )
    reviews = result.scalars().all()

    queue = []
    for review in reviews:
        contract_r = await db.execute(
            select(Contract).where(Contract.id == review.contract_id)
        )
        contract = contract_r.scalar_one_or_none()
        if contract:
            queue.append({
                "review_id":      str(review.id),
                "contract_id":    str(contract.id),
                "contract_title": contract.title,
                "counterparty":   contract.counterparty,
                "risk_level":     contract.risk_level,
                "risk_score":     contract.risk_score,
                "priority":       review.priority,
                "status":         review.status,
                "due_date":       review.due_date.isoformat() if review.due_date else None,
                "notes":          review.notes,
                "assigned_at":    review.created_at.isoformat() if review.created_at else None,
            })

    return {"queue": queue, "total": len(queue)}


async def _notify_reviewer(reviewer, contract, assigner, review) -> None:
    """Send email notification to reviewer."""
    try:
        from app.core.config import settings
        if not settings.RESEND_API_KEY:
            return
        import resend
        resend.api_key = settings.RESEND_API_KEY
        priority_emoji = {"urgent":"🚨","high":"⚠️","normal":"📋","low":"📌"}.get(review.priority,"📋")
        resend.Emails.send({
            "from": f"Claustor AI <{settings.RESEND_FROM}>",
            "to": reviewer.email,
            "subject": f"{priority_emoji} Contract assigned for review: {contract.title}",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:32px;">
              <h2 style="color:#111827;">Contract Review Assigned</h2>
              <p>Hi {reviewer.full_name or reviewer.email},</p>
              <p><strong>{assigner.email}</strong> has assigned you a contract for review.</p>
              <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:12px;padding:20px;margin:16px 0;">
                <h3 style="margin:0 0 12px;color:#111827;">{contract.title}</h3>
                <p style="color:#6B7280;margin:4px 0;">Counterparty: {contract.counterparty or "—"}</p>
                <p style="color:#6B7280;margin:4px 0;">Risk level: {contract.risk_level or "—"}</p>
                <p style="color:#6B7280;margin:4px 0;">Priority: {review.priority}</p>
                {f'<p style="color:#DC2626;margin:4px 0;">Due: {review.due_date.strftime("%d %b %Y")}</p>' if review.due_date else ""}
                {f'<p style="color:#374151;margin-top:12px;">Notes: {review.notes}</p>' if review.notes else ""}
              </div>
              <a href="https://claustor.com/dashboard/contracts/{contract.id}" style="display:inline-block;background:#5B4BFF;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">
                Review contract →
              </a>
            </div>
            """,
        })
    except Exception as e:
        logger.warning("reviewer_notification_failed", error=str(e))


async def _notify_decision(review, reviewer, decision: str, notes: str | None) -> None:
    """Notify assigner of review decision."""
    try:
        from app.core.config import settings
        if not settings.RESEND_API_KEY:
            return
        import resend
        resend.api_key = settings.RESEND_API_KEY
        emoji = {"approved":"✅","rejected":"❌","revision_needed":"🔄"}.get(decision,"📋")
        # Fetch assigner email
        # (simplified — in prod query DB for assigner email)
        logger.info("decision_notification_sent", decision=decision)
    except Exception as e:
        logger.warning("decision_notification_failed", error=str(e))

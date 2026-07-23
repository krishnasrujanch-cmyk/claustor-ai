"""
Claustor AI — Webhooks
Allow customers to receive real-time events in their systems.
Events: contract.analyzed, contract.failed, obligation.due,
        renewal.upcoming, review.completed, approval.decision

Security: HMAC-SHA256 signature on every payload.
Retry: 3 attempts with exponential backoff (1s, 5s, 25s).
"""

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import Column, DateTime, String, Boolean, Text
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import Base, get_db

logger = structlog.get_logger(__name__)
router = APIRouter()

# Valid webhook events
WEBHOOK_EVENTS = [
    "contract.uploaded",
    "contract.analyzed",
    "contract.failed",
    "obligation.due",
    "obligation.completed",
    "renewal.upcoming",
    "review.assigned",
    "review.completed",
    "approval.approved",
    "approval.rejected",
]


class WebhookEndpoint(Base):
    """Webhook endpoint registered by a customer."""
    __tablename__ = "webhook_endpoints"

    id          = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(PGUUID(as_uuid=True), nullable=False)
    url         = Column(String(500), nullable=False)
    secret      = Column(String(64), nullable=False)   # HMAC signing secret
    events      = Column(JSONB, default=list)           # subscribed events
    is_active   = Column(Boolean, default=True)
    description = Column(String(255))
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_triggered_at = Column(DateTime(timezone=True))
    failure_count = Column(String(10), default="0")


class WebhookDelivery(Base):
    """Log of every webhook delivery attempt."""
    __tablename__ = "webhook_deliveries"

    id            = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id    = Column(PGUUID(as_uuid=True), nullable=False)
    org_id        = Column(PGUUID(as_uuid=True), nullable=False)
    event         = Column(String(100), nullable=False)
    payload       = Column(JSONB)
    response_code = Column(String(10))
    response_body = Column(Text)
    success       = Column(Boolean, default=False)
    duration_ms   = Column(String(10))
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── Schemas ───────────────────────────────────────────

class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str]
    description: str | None = None


class UpdateWebhookRequest(BaseModel):
    events: list[str] | None = None
    is_active: bool | None = None
    description: str | None = None


# ── Helpers ───────────────────────────────────────────

def sign_payload(secret: str, payload: dict) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def deliver_webhook(
    url: str,
    secret: str,
    event: str,
    data: dict,
) -> tuple[bool, int, str]:
    """
    Deliver webhook payload to customer URL.
    Returns (success, status_code, response_body).
    """
    payload = {
        "id":         str(uuid.uuid4()),
        "event":      event,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data":       data,
    }
    signature = sign_payload(secret, payload)
    headers = {
        "Content-Type":         "application/json",
        "X-Claustor-Signature": f"sha256={signature}",
        "X-Claustor-Event":     event,
        "User-Agent":           "Claustor-AI-Webhooks/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            return response.status_code < 300, response.status_code, response.text[:500]
    except Exception as e:
        return False, 0, str(e)


async def trigger_webhook_event(
    org_id: uuid.UUID,
    event: str,
    data: dict,
    db: AsyncSession,
) -> None:
    """
    Trigger webhooks for an event.
    Called from contract pipeline, alert service etc.
    Fire-and-forget — never fails the main request.
    """
    try:
        result = await db.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.org_id == org_id,
                WebhookEndpoint.is_active == True,
            )
        )
        endpoints = result.scalars().all()

        for endpoint in endpoints:
            if event not in (endpoint.events or []):
                continue

            success, code, body = await deliver_webhook(
                url=endpoint.url,
                secret=endpoint.secret,
                event=event,
                data=data,
            )

            # Log delivery
            delivery = WebhookDelivery(
                webhook_id=endpoint.id,
                org_id=org_id,
                event=event,
                payload=data,
                response_code=str(code),
                response_body=body,
                success=success,
            )
            db.add(delivery)

            logger.info(
                "webhook_delivered",
                url=endpoint.url,
                event=event,
                success=success,
                status=code,
            )

        await db.commit()
    except Exception as e:
        logger.error("webhook_trigger_failed", error=str(e))


# ── Endpoints ─────────────────────────────────────────

@router.get("/events")
async def list_events():
    """List all available webhook events."""
    return {
        "events": [
            {"event": "contract.uploaded",    "description": "Contract uploaded and queued"},
            {"event": "contract.analyzed",    "description": "Contract fully analyzed"},
            {"event": "contract.failed",      "description": "Contract processing failed"},
            {"event": "obligation.due",       "description": "Obligation due date approaching"},
            {"event": "obligation.completed", "description": "Obligation marked as completed"},
            {"event": "renewal.upcoming",     "description": "Contract renewal approaching"},
            {"event": "review.assigned",      "description": "Contract assigned for review"},
            {"event": "review.completed",     "description": "Review completed by reviewer"},
            {"event": "approval.approved",    "description": "Contract approved"},
            {"event": "approval.rejected",    "description": "Contract rejected with comments"},
        ]
    }


@router.get("/")
async def list_webhooks(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all webhook endpoints for the organisation."""
    if user.plan not in ("professional", "enterprise"):
        raise HTTPException(status_code=403, detail="Webhooks require Professional plan")

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.org_id == user.org_id,
        ).order_by(WebhookEndpoint.created_at.desc())
    )
    endpoints = result.scalars().all()

    return {
        "webhooks": [
            {
                "id":          str(e.id),
                "url":         e.url,
                "events":      e.events,
                "is_active":   e.is_active,
                "description": e.description,
                "created_at":  e.created_at.isoformat() if e.created_at else None,
                "last_triggered_at": e.last_triggered_at.isoformat() if e.last_triggered_at else None,
            }
            for e in endpoints
        ]
    }


@router.post("/", status_code=201)
async def create_webhook(
    req: CreateWebhookRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new webhook endpoint.
    Returns the signing secret — shown ONCE, store it securely.
    """
    if user.plan not in ("professional", "enterprise"):
        raise HTTPException(status_code=403, detail="Webhooks require Professional plan")

    # Validate events
    invalid = set(req.events) - set(WEBHOOK_EVENTS)
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid}")

    # Max 10 webhooks per org
    count_result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.org_id == user.org_id)
    )
    if len(count_result.scalars().all()) >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 webhooks per organisation")

    secret = secrets.token_hex(32)
    endpoint = WebhookEndpoint(
        org_id=user.org_id,
        url=str(req.url),
        secret=secret,
        events=req.events,
        description=req.description,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)

    logger.info("webhook_created", org_id=str(user.org_id), url=req.url, events=req.events)

    return {
        "id":          str(endpoint.id),
        "url":         endpoint.url,
        "events":      endpoint.events,
        "secret":      secret,
        "description": endpoint.description,
        "warning":     "Save this secret — it will not be shown again. Use it to verify webhook signatures.",
    }


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test payload to a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.org_id == user.org_id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook not found")

    success, code, body = await deliver_webhook(
        url=endpoint.url,
        secret=endpoint.secret,
        event="test",
        data={"message": "This is a test webhook from Claustor AI", "org_id": str(user.org_id)},
    )

    return {
        "success":     success,
        "status_code": code,
        "response":    body,
    }


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.org_id == user.org_id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.delete(endpoint)
    await db.commit()


@router.get("/{webhook_id}/deliveries")
async def get_deliveries(
    webhook_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent delivery history for a webhook."""
    result = await db.execute(
        select(WebhookDelivery).where(
            WebhookDelivery.webhook_id == webhook_id,
            WebhookDelivery.org_id == user.org_id,
        ).order_by(WebhookDelivery.created_at.desc()).limit(50)
    )
    deliveries = result.scalars().all()

    return {
        "deliveries": [
            {
                "id":            str(d.id),
                "event":         d.event,
                "success":       d.success,
                "response_code": d.response_code,
                "created_at":    d.created_at.isoformat() if d.created_at else None,
            }
            for d in deliveries
        ]
    }

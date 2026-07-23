"""
Claustor AI — Audit Log Service
Writes immutable audit trail for all important actions.
GDPR compliant: IPs hashed, PII not stored.
"""

import uuid
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AuditLog
from app.core.security import hash_ip

logger = structlog.get_logger(__name__)


class AuditService:
    """Writes audit log entries. Never fails — non-blocking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        status: str = "SUCCESS",
        org_id: UUID | None = None,
        user_id: UUID | None = None,
        user_role: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        ip_address: str | None = None,
        trace_id: str | None = None,
        duration_ms: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Write an audit log entry.
        Never raises — audit failures must not break the main request.
        """
        try:
            entry = AuditLog(
                org_id=org_id,
                user_id=user_id,
                user_role=user_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_hash=hash_ip(ip_address) if ip_address else None,
                trace_id=trace_id or str(uuid.uuid4())[:8],
                duration_ms=duration_ms,
                status=status,
                metadata=metadata or {},
            )
            self.db.add(entry)
            await self.db.commit()

            logger.debug(
                "audit_logged",
                action=action,
                status=status,
                org_id=str(org_id) if org_id else None,
                resource_type=resource_type,
            )
        except Exception as e:
            logger.error("audit_log_failed", error=str(e), action=action)


# ── FastAPI dependency ────────────────────────────────
async def get_audit_service(db) -> AuditService:
    return AuditService(db)


# ── Common audit actions ──────────────────────────────
class AuditAction:
    # Auth
    USER_REGISTER     = "user.register"
    USER_LOGIN        = "user.login"
    USER_LOGOUT       = "user.logout"
    USER_INVITE       = "user.invite"
    USER_DEACTIVATE   = "user.deactivate"
    PASSWORD_RESET    = "password.reset"
    API_KEY_CREATE    = "api_key.create"
    API_KEY_REVOKE    = "api_key.revoke"

    # Contracts
    CONTRACT_UPLOAD   = "contract.upload"
    CONTRACT_VIEW     = "contract.view"
    CONTRACT_DELETE   = "contract.delete"
    CONTRACT_ANALYZE  = "contract.analyze"
    CONTRACT_EXPORT   = "contract.export"

    # Chat
    CHAT_QUERY        = "chat.query"

    # Reviews
    REVIEW_ASSIGN     = "review.assign"
    REVIEW_DECISION   = "review.decision"

    # Billing
    PLAN_SUBSCRIBE    = "billing.subscribe"
    PLAN_CANCEL       = "billing.cancel"

    # Webhooks
    WEBHOOK_CREATE    = "webhook.create"
    WEBHOOK_DELETE    = "webhook.delete"

    # Admin
    BULK_IMPORT       = "bulk.import"
    SETTINGS_UPDATE   = "settings.update"

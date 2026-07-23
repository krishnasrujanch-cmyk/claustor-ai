"""Claustor AI — Audit Log Endpoints."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.domain.models import AuditLog
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/")
async def list_audit_logs(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
):
    """Get audit log for the organisation. Admin only."""
    if not user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    query = select(AuditLog).where(AuditLog.org_id == user.org_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id":            str(log.id),
                "action":        log.action,
                "status":        log.status,
                "user_id":       str(log.user_id) if log.user_id else None,
                "user_role":     log.user_role,
                "resource_type": log.resource_type,
                "resource_id":   str(log.resource_id) if log.resource_id else None,
                "trace_id":      log.trace_id,
                "duration_ms":   log.duration_ms,
                "metadata":      log.metadata,
                "created_at":    log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "page": page,
        "page_size": page_size,
    }

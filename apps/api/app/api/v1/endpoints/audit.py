"""
Claustor AI — Audit Log + Data Export Endpoints.

Audit log: complete record of all actions taken on org data.
Data export: download all org data as a ZIP archive.
"""

import io
import csv
import json
import zipfile
import hashlib
from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.domain.models import AuditLog, Contract, Clause, Obligation, User
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


# ── Helper: write audit event ──────────────────────────────────────────────────

async def write_audit(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID | None,
    user_role: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    status: str = "SUCCESS",
    extra_data: dict | None = None,
) -> None:
    """Write an audit log entry. Fire-and-forget — never raises."""
    try:
        log = AuditLog(
            org_id=org_id,
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            extra_data=extra_data or {},
        )
        db.add(log)
        await db.flush()
    except Exception as e:
        logger.warning("audit_write_failed", error=str(e))


# ── GET /audit/ — List audit logs ─────────────────────────────────────────────

@router.get("/")
async def list_audit_logs(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    user_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    """Get audit log for the organisation. Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    query = select(AuditLog).where(AuditLog.org_id == user.org_id)

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if user_id:
        try:
            query = query.where(AuditLog.user_id == UUID(user_id))
        except ValueError:
            pass
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Enrich with user emails
    user_ids = list({str(log.user_id) for log in logs if log.user_id})
    user_map: dict[str, str] = {}
    if user_ids:
        user_result = await db.execute(
            select(User.id, User.email, User.full_name)
            .where(User.id.in_([UUID(uid) for uid in user_ids]))
        )
        for row in user_result.fetchall():
            user_map[str(row.id)] = f"{row.full_name or row.email}"

    return {
        "logs": [
            {
                "id":            str(log.id),
                "action":        log.action,
                "status":        log.status,
                "user":          user_map.get(str(log.user_id), "System") if log.user_id else "System",
                "user_role":     log.user_role,
                "resource_type": log.resource_type,
                "resource_id":   str(log.resource_id) if log.resource_id else None,
                "extra_data":    log.extra_data or {},
                "created_at":    log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


# ── GET /audit/summary — Stats ─────────────────────────────────────────────────

@router.get("/summary")
async def audit_summary(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit activity summary for the org."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(text("""
        SELECT
            action,
            COUNT(*) as count,
            COUNT(DISTINCT user_id) as unique_users,
            MAX(created_at) as last_seen
        FROM audit_log
        WHERE org_id = :org_id
          AND created_at > NOW() - INTERVAL '30 days'
        GROUP BY action
        ORDER BY count DESC
        LIMIT 20
    """), {"org_id": str(user.org_id)})

    rows = result.fetchall()
    return {
        "period": "last_30_days",
        "actions": [
            {
                "action":       row.action,
                "count":        row.count,
                "unique_users": row.unique_users,
                "last_seen":    row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in rows
        ],
    }


# ── GET /audit/export — Download audit log as CSV ────────────────────────────

@router.get("/export")
async def export_audit_csv(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download full audit log as CSV."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == user.org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10000)
    )
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Action", "Status", "User ID", "Role",
                     "Resource Type", "Resource ID", "Extra Data"])

    for log in logs:
        writer.writerow([
            log.created_at.isoformat() if log.created_at else "",
            log.action,
            log.status,
            str(log.user_id) if log.user_id else "",
            log.user_role or "",
            log.resource_type or "",
            str(log.resource_id) if log.resource_id else "",
            json.dumps(log.extra_data or {}),
        ])

    output.seek(0)
    filename = f"claustor-audit-{user.org_id}-{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ── GET /audit/data-export — Full org data ZIP ───────────────────────────────

@router.get("/data-export")
async def export_org_data(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export ALL org data as a ZIP archive.
    Includes: contracts metadata, clauses, obligations, reviews, audit log.
    Original contract files included if stored locally.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    import os

    # Log this export event
    await write_audit(
        db, user.org_id, user.id, user.role,
        action="data_export",
        resource_type="organisation",
        status="SUCCESS",
        extra_data={"requested_by": user.email},
    )
    await db.commit()

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        # ── README ────────────────────────────────────────────────
        readme = f"""CLAUSTOR AI — DATA EXPORT
========================
Organisation: {user.org_id}
Exported by:  {user.email}
Export date:  {datetime.now(timezone.utc).isoformat()}
Export scope: Full organisation data

CONTENTS:
  contracts/metadata.json     — All contract records
  contracts/clauses.json      — All extracted clauses
  obligations/obligations.csv — All obligations
  audit/audit_log.csv         — Complete audit trail
  README.txt                  — This file

NOTE: Original PDF/DOCX files included where available.
This export is for portability and backup purposes.
"""
        zf.writestr("README.txt", readme)

        # ── Contracts metadata ────────────────────────────────────
        contracts_result = await db.execute(
            select(Contract)
            .where(Contract.org_id == user.org_id, Contract.is_active == True)
            .order_by(Contract.created_at.desc())
        )
        contracts = contracts_result.scalars().all()

        contracts_data = []
        for c in contracts:
            contracts_data.append({
                "id":               str(c.id),
                "title":            c.title,
                "original_filename":c.original_filename,
                "contract_type":    c.contract_type,
                "counterparty":     c.counterparty,
                "governing_law":    c.governing_law,
                "effective_date":   c.effective_date.isoformat() if c.effective_date else None,
                "expiry_date":      c.expiry_date.isoformat() if c.expiry_date else None,
                "contract_value":   float(c.contract_value) if c.contract_value else None,
                "contract_currency":c.contract_currency,
                "risk_score":       float(c.risk_score) if c.risk_score else None,
                "risk_level":       c.risk_level,
                "status":           c.status,
                "review_status":    c.review_status,
                "summary":          c.summary,
                "version_number":   c.version_number,
                "is_latest":        c.is_latest,
                "missing_clauses":  c.missing_clauses or [],
                "detected_language":c.detected_language,
                "created_at":       c.created_at.isoformat() if c.created_at else None,
            })

        zf.writestr(
            "contracts/metadata.json",
            json.dumps(contracts_data, indent=2, default=str)
        )

        # ── Include original files ────────────────────────────────
        file_count = 0
        for c in contracts:
            if c.file_path and os.path.exists(c.file_path):
                try:
                    with open(c.file_path, "rb") as f:
                        file_bytes = f.read()
                    safe_name = (c.original_filename or f"contract-{str(c.id)[:8]}.pdf"
                                 ).replace("/", "_")
                    zf.writestr(f"contracts/files/{safe_name}", file_bytes)
                    file_count += 1
                except Exception as fe:
                    logger.warning("export_file_failed", error=str(fe))

        # ── Clauses ───────────────────────────────────────────────
        contract_ids = [c.id for c in contracts]
        clauses_data = []
        if contract_ids:
            clauses_result = await db.execute(
                select(Clause)
                .where(Clause.contract_id.in_(contract_ids))
                .order_by(Clause.contract_id, Clause.risk_score.desc())
            )
            clauses = clauses_result.scalars().all()
            for cl in clauses:
                clauses_data.append({
                    "id":                str(cl.id),
                    "contract_id":       str(cl.contract_id),
                    "clause_type":       cl.clause_type,
                    "title":             cl.title,
                    "summary":           cl.summary,
                    "raw_text":          cl.raw_text,
                    "risk_score":        float(cl.risk_score) if cl.risk_score else None,
                    "risk_level":        cl.risk_level,
                    "risk_reason":       cl.risk_reason,
                    "playbook_match":    float(cl.playbook_match) if cl.playbook_match else None,
                    "deviation_from_std":cl.deviation_from_std,
                    "related_clauses":   cl.related_clauses or [],
                    "section_reference": cl.section_reference,
                })

        zf.writestr(
            "contracts/clauses.json",
            json.dumps(clauses_data, indent=2, default=str)
        )

        # ── Obligations CSV ───────────────────────────────────────
        obs_output = io.StringIO()
        obs_writer = csv.writer(obs_output)
        obs_writer.writerow(["ID", "Contract ID", "Type", "Title", "Party",
                             "Due Date", "Status", "Description"])

        if contract_ids:
            obs_result = await db.execute(
                select(Obligation)
                .where(Obligation.contract_id.in_(contract_ids))
                .order_by(Obligation.due_date.asc())
            )
            obligations = obs_result.scalars().all()
            for ob in obligations:
                obs_writer.writerow([
                    str(ob.id), str(ob.contract_id),
                    ob.obligation_type or "", ob.title or "",
                    ob.party or "",
                    ob.due_date.isoformat() if ob.due_date else "",
                    ob.status or "",
                    (ob.description or "")[:200],
                ])

        zf.writestr("obligations/obligations.csv",
                    obs_output.getvalue().encode().decode())

        # ── Audit log CSV ─────────────────────────────────────────
        audit_output = io.StringIO()
        audit_writer = csv.writer(audit_output)
        audit_writer.writerow(["Timestamp", "Action", "Status", "User ID",
                               "Role", "Resource Type", "Resource ID"])

        audit_result = await db.execute(
            select(AuditLog)
            .where(AuditLog.org_id == user.org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(10000)
        )
        audit_logs = audit_result.scalars().all()
        for log in audit_logs:
            audit_writer.writerow([
                log.created_at.isoformat() if log.created_at else "",
                log.action, log.status,
                str(log.user_id) if log.user_id else "",
                log.user_role or "",
                log.resource_type or "",
                str(log.resource_id) if log.resource_id else "",
            ])

        zf.writestr("audit/audit_log.csv",
                    audit_output.getvalue().encode().decode())

        # ── Export manifest ───────────────────────────────────────
        manifest = {
            "export_id":    hashlib.sha256(str(user.org_id).encode()).hexdigest()[:12],
            "org_id":       str(user.org_id),
            "exported_by":  user.email,
            "exported_at":  datetime.now(timezone.utc).isoformat(),
            "counts": {
                "contracts":   len(contracts_data),
                "clauses":     len(clauses_data),
                "obligations": len(obligations) if contract_ids else 0,
                "audit_logs":  len(audit_logs),
                "files":       file_count,
            }
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buffer.seek(0)
    filename = f"claustor-export-{datetime.now().strftime('%Y%m%d-%H%M')}.zip"

    logger.info("data_export_complete",
               org_id=str(user.org_id),
               contracts=len(contracts_data),
               files=file_count)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

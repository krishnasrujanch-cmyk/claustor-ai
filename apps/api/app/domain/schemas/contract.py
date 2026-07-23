"""
Claustor AI — Contract Schemas
Pydantic models for contract API request/response.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Upload ────────────────────────────────────────────────

class ContractUploadResponse(BaseModel):
    """Response after contract upload — before processing completes."""
    contract_id: UUID
    status: str
    message: str
    queue_position: int | None = None
    estimated_wait_seconds: int | None = None


# ── Contract Detail ───────────────────────────────────────

class ClauseOut(BaseModel):
    id: UUID
    clause_type: str
    title: str | None
    summary: str | None
    risk_score: float
    risk_level: str
    risk_reason: str | None
    section_reference: str | None
    page_number: int | None

    model_config = {"from_attributes": True}


class ContractOut(BaseModel):
    id: UUID
    title: str
    original_filename: str
    contract_type: str | None
    counterparty: str | None
    governing_law: str | None
    language: str | None
    effective_date: date | None
    expiry_date: date | None
    auto_renewal: bool | None
    renewal_notice_days: int | None
    contract_value: float | None
    contract_currency: str | None
    status: str
    risk_score: float | None
    risk_level: str | None
    health_score: float | None
    clause_count: int
    summary: str | None
    version: int
    has_signatures: bool
    has_tracked_changes: bool
    backdating_risk: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractDetailOut(ContractOut):
    clauses: list[ClauseOut] = []


# ── List ──────────────────────────────────────────────────

class ContractListOut(BaseModel):
    contracts: list[ContractOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Processing Status ─────────────────────────────────────

class ProcessingStatus(BaseModel):
    contract_id: UUID
    status: str
    progress_pct: int
    current_step: str
    steps_completed: list[str]
    error: str | None = None
    completed_at: datetime | None = None

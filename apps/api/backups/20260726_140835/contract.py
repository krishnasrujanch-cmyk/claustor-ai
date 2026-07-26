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
    status: str = "pending"
    message: str
    queue_position: int | None = None
    estimated_wait_seconds: int | None = None


# ── Contract Detail ───────────────────────────────────────

class ClauseOut(BaseModel):
    id: UUID
    clause_type: str
    title: str | None = None
    summary: str | None = None
    risk_score: float
    risk_level: str
    risk_reason: str | None = None
    section_reference: str | None = None
    page_number: int | None = None

    model_config = {"from_attributes": True}


class ContractOut(BaseModel):
    id: UUID
    title: str = ""
    original_filename: str = ""
    contract_type: str | None = None
    counterparty: str | None = None
    governing_law: str | None = None
    language: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    auto_renewal: bool | None = None
    renewal_notice_days: int | None = None
    contract_value: float | None = None
    contract_currency: str | None = None
    status: str = "pending"
    risk_score: float | None = None
    risk_level: str | None = None
    health_score: float | None = None
    clause_count: int = 0
    summary: str | None = None
    version: int = 1
    has_signatures: bool = False
    has_tracked_changes: bool = False
    backdating_risk: bool = False
    flagged_for_review: bool | None = False
    review_status: str | None = None
    parent_contract_id: str | None = None
    contract_family_id: str | None = None
    version_number: int = 1
    is_latest: bool = True
    version_note: str | None = None

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Convert UUID fields to str before validation
        if hasattr(obj, '__dict__') or hasattr(obj, '_sa_instance_state'):
            data = {}
            for field in cls.model_fields:
                val = getattr(obj, field, None)
                if val is not None and hasattr(val, 'hex'):  # UUID
                    data[field] = str(val)
                else:
                    data[field] = val
            return cls(**{k:v for k,v in data.items() if v is not None or cls.model_fields[k].default is None})
        return super().model_validate(obj, **kwargs)
    review_notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContractDetailOut(ContractOut):
    clauses: list[ClauseOut] = []


# ── List ──────────────────────────────────────────────────

class ContractListOut(BaseModel):
    contracts: list[ContractOut]
    total: int
    page: int
    page_size: int
    total_pages: int = 1


# ── Processing Status ─────────────────────────────────────

class ProcessingStatus(BaseModel):
    contract_id: UUID
    status: str = "pending"
    progress_pct: int
    current_step: str
    steps_completed: list[str]
    error: str | None = None
    completed_at: datetime | None = None

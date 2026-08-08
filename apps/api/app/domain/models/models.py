"""
Claustor AI — Domain Models
All SQLAlchemy models for multi-tenant contract intelligence platform.
"""

import uuid
from typing import Optional
from datetime import datetime, date
from typing import Any

from sqlalchemy import (
    Boolean, BigInteger, Column, Date, DateTime, Float, ForeignKey,
    Integer, LargeBinary, String, Text, UniqueConstraint,
    func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY, TIMESTAMP as TIMESTAMPTZ
PGUUID = UUID  # alias
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref

from app.infrastructure.database.session import Base


def gen_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ═══════════════════════════════════════════════════════════
# ORGANISATIONS (Tenants)
# ═══════════════════════════════════════════════════════════

class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Plan
    plan: Mapped[str] = mapped_column(String(50), default="free")
    industry: Mapped[str] = mapped_column(String(50), default="general")
    plan_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Billing
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    addon_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_status: Mapped[str] = mapped_column(String(20), default="active")
    next_billing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grace_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_payment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_payment_amount: Mapped[int] = mapped_column(Integer, default=0)
    billing_period: Mapped[str] = mapped_column(String(20), default="monthly")
    reminder_sent_days: Mapped[list] = mapped_column(JSONB, default=list)

    # Plan limits (from plan + extras purchased)
    max_users: Mapped[int] = mapped_column(Integer, default=1)
    max_contracts: Mapped[int] = mapped_column(Integer, default=5)
    max_queries_mo: Mapped[int] = mapped_column(Integer, default=100)
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=100)
    extra_users_purchased: Mapped[int] = mapped_column(Integer, default=0)

    # Usage this month (reset monthly by Celery Beat)
    contracts_used: Mapped[int] = mapped_column(Integer, default=0)
    queries_used: Mapped[int] = mapped_column(Integer, default=0)
    storage_used_mb: Mapped[float] = mapped_column(Float, default=0.0)
    usage_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.date_trunc("month", func.now())
    )

    # Infrastructure isolation
    pinecone_namespace: Mapped[str | None] = mapped_column(String(100))
    gcs_prefix: Mapped[str | None] = mapped_column(String(255))

    # Organisation profile
    gstin: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(20))
    website: Mapped[str | None] = mapped_column(String(255))
    # SSO (Enterprise)
    sso_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sso_provider: Mapped[str | None] = mapped_column(String(50))
    sso_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Settings
    data_region: Mapped[str] = mapped_column(String(20), default="in")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    default_language: Mapped[str] = mapped_column(String(10), default="en")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organisation")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="organisation")
    departments: Mapped[list["Department"]] = relationship("Department", back_populates="organisation")


# ═══════════════════════════════════════════════════════════
# DEPARTMENTS
# ═══════════════════════════════════════════════════════════

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"))
    admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="departments")


# ═══════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # AES-256 encrypted
    full_name: Mapped[str | None] = mapped_column(String(500))       # AES-256 encrypted
    password_hash: Mapped[str | None] = mapped_column(String(255))   # bcrypt-12, null if SSO

    # Role & access
    role: Mapped[str] = mapped_column(String(50), default="business_viewer")
    department_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"))
    manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # External / guest
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)
    guest_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Invitation
    invited_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    invite_token: Mapped[str | None] = mapped_column(String(255))
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # SSO / LDAP / SCIM
    auth0_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    ldap_id: Mapped[str | None] = mapped_column(String(255))
    scim_id: Mapped[str | None] = mapped_column(String(255))

    # MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_user_org_email"),
    )

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="users")


# ═══════════════════════════════════════════════════════════
# CONTRACTS
# ═══════════════════════════════════════════════════════════

class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # File info
    title: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64))        # SHA-256 for dedup
    file_path: Mapped[str | None] = mapped_column(Text)       # GCS path (encrypted)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(100))

    # Contract info (extracted)
    contract_type: Mapped[str | None] = mapped_column(String(100))
    counterparty: Mapped[str | None] = mapped_column(String(500))  # encrypted
    counterparty_normalized: Mapped[str | None] = mapped_column(String(500))
    governing_law: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(10))
    effective_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    auto_renewal: Mapped[bool | None] = mapped_column(Boolean)
    renewal_notice_days: Mapped[int | None] = mapped_column(Integer)
    contract_value: Mapped[float | None] = mapped_column(Float)
    contract_currency: Mapped[str | None] = mapped_column(String(10))

    # AI analysis
    status: Mapped[str] = mapped_column(String(50), default="queued")
    industry: Mapped[str] = mapped_column(String(50), default="general")
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    health_score: Mapped[float | None] = mapped_column(Float)
    clause_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_contract_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id"))

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    # Version control
    parent_contract_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    contract_family_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    version_note: Mapped[str | None] = mapped_column(String(500))
    missing_clauses: Mapped[list | None] = mapped_column(JSONB, default=list)
    detected_language: Mapped[str | None] = mapped_column(String(10), default="en")
    review_status: Mapped[str | None] = mapped_column(String(50))
    review_notes: Mapped[str | None] = mapped_column(Text)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    has_signatures: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tracked_changes: Mapped[bool] = mapped_column(Boolean, default=False)
    has_unresolved_comments: Mapped[bool] = mapped_column(Boolean, default=False)
    backdating_risk: Mapped[bool] = mapped_column(Boolean, default=False)

    # Processing
    processing_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="contracts")
    clauses: Mapped[list["Clause"]] = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")
    chunks: Mapped[list["ContractChunk"]] = relationship("ContractChunk", back_populates="contract", cascade="all, delete-orphan")
    doc_metadata: Mapped["DocumentMetadata"] = relationship("DocumentMetadata", back_populates="contract", uselist=False)
    obligations: Mapped[list["Obligation"]] = relationship("Obligation", back_populates="contract", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="contract")


# ═══════════════════════════════════════════════════════════
# CLAUSES
# ═══════════════════════════════════════════════════════════

class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    clause_type: Mapped[str] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(500))
    raw_text: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    section_reference: Mapped[str | None] = mapped_column(String(100))
    page_number: Mapped[int | None] = mapped_column(Integer)

    # Risk
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    playbook_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_from_std: Mapped[str | None]   = mapped_column(Text, nullable=True)
    adjusted_risk:       Mapped[float | None] = mapped_column(Float, nullable=True)
    industry_weight:     Mapped[float | None] = mapped_column(Float, nullable=True, default=1.0)
    related_clauses:     Mapped[list | None]  = mapped_column(JSONB, nullable=True)
    cross_references:    Mapped[list | None]  = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    risk_reason: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Feedback
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    # Version control
    parent_contract_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    contract_family_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    version_note: Mapped[str | None] = mapped_column(String(500))
    missing_clauses: Mapped[list | None] = mapped_column(JSONB, default=list)
    detected_language: Mapped[str | None] = mapped_column(String(10), default="en")
    review_status: Mapped[str | None] = mapped_column(String(50))
    review_notes: Mapped[str | None] = mapped_column(Text)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_feedback: Mapped[str | None] = mapped_column(String(20))  # positive | negative
    reviewer_score: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="clauses")


# ═══════════════════════════════════════════════════════════
# DOCUMENT METADATA
# ═══════════════════════════════════════════════════════════

class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), unique=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    # Safe metadata (plaintext)
    page_count: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    language: Mapped[str | None] = mapped_column(String(10))
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    revision_count: Mapped[int | None] = mapped_column(Integer)
    creator_tool: Mapped[str | None] = mapped_column(String(255))
    producer: Mapped[str | None] = mapped_column(String(255))
    template_name: Mapped[str | None] = mapped_column(String(255))
    doc_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    doc_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Masked PII
    author_masked: Mapped[str | None] = mapped_column(Text)
    modifier_masked: Mapped[str | None] = mapped_column(Text)
    title_masked: Mapped[str | None] = mapped_column(Text)

    # Sensitive (AES-256 encrypted BYTEA)
    tracked_changes_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    comments_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)

    # Computed alerts
    creation_to_upload_days: Mapped[int | None] = mapped_column(Integer)
    backdating_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    unresolved_comment_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="doc_metadata")


# ═══════════════════════════════════════════════════════════
# OBLIGATIONS
# ═══════════════════════════════════════════════════════════

class Obligation(Base):
    __tablename__ = "obligations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    obligation_type: Mapped[str] = mapped_column(String(100))
    party: Mapped[str | None] = mapped_column(String(100))
    due_date: Mapped[date | None] = mapped_column(Date)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_config: Mapped[dict | None] = mapped_column(JSONB)
    amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    reminder_days: Mapped[list | None] = mapped_column(ARRAY(Integer))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="obligations")


# ═══════════════════════════════════════════════════════════
# CONVERSATIONS (Chat History)
# ═══════════════════════════════════════════════════════════

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="SET NULL"))
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    role: Mapped[str] = mapped_column(String(20))      # user | assistant
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[dict | None] = mapped_column(JSONB)
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="conversations")


# ═══════════════════════════════════════════════════════════
# API KEYS
# ═══════════════════════════════════════════════════════════

class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)   # SHA-256
    key_prefix: Mapped[str] = mapped_column(String(20))              # clst_live_xxx...
    scopes: Mapped[list] = mapped_column(ARRAY(String))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════
# AUDIT LOG (Immutable — append only)
# ═══════════════════════════════════════════════════════════

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_role: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ip_hash: Mapped[str | None] = mapped_column(String(64))         # SHA-256 of IP
    trace_id: Mapped[str | None] = mapped_column(String(100))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))                  # ALLOWED | DENIED | SUCCESS | FAILED
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AIObservability(Base):
    """Tracks every LLM call — cost, latency, quality, guardrails."""
    __tablename__ = "ai_observability"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=True)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    contract_id         = Column(UUID(as_uuid=True), nullable=True)

    # Agent identity
    agent_role          = Column(String(50), nullable=False)
    model               = Column(String(100), nullable=False)
    provider            = Column(String(50), nullable=False)

    # Cost
    prompt_tokens       = Column(Integer, default=0)
    completion_tokens   = Column(Integer, default=0)
    total_tokens        = Column(Integer, default=0)
    cost_usd            = Column(Float, default=0.0)

    # Performance
    latency_ms          = Column(Integer, default=0)
    retrieval_time_ms   = Column(Integer, default=0)
    first_token_ms      = Column(Integer, default=0)

    # Quality
    hallucination       = Column(Boolean, default=False)
    groundedness        = Column(Float, nullable=True)
    confidence          = Column(Float, nullable=True)
    citations_verified  = Column(Integer, default=0)
    citations_total     = Column(Integer, default=0)

    # RAG
    chunks_retrieved    = Column(Integer, default=0)
    chunks_used         = Column(Integer, default=0)
    cache_hit           = Column(Boolean, default=False)

    # Guardrails
    safety_passed       = Column(Boolean, default=True)
    injection_detected  = Column(Boolean, default=False)
    judge_triggered     = Column(Boolean, default=False)

    # User feedback
    user_feedback       = Column(String(20), nullable=True)  # thumbs_up/thumbs_down/null
    query_preview       = Column(String(200), nullable=True)

    created_at          = Column(TIMESTAMPTZ, server_default=func.now())


class ContractChunk(Base):
    """Hierarchical contract chunks for RAG — parent/child structure."""
    __tablename__ = "contract_chunks"

    id          : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    org_id      : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_id   : Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_chunks.id"), nullable=True)
    is_parent   : Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_type  : Mapped[str]  = mapped_column(String(20), default="clause")
    chunk_index : Mapped[int]  = mapped_column(Integer, nullable=False)
    text        : Mapped[str]  = mapped_column(Text, nullable=False)
    heading     : Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    section_ref : Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    page_number : Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risk_score  : Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    importance  : Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cross_refs  : Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    table_json  : Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    pinecone_id : Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at  : Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    contract : Mapped["Contract"] = relationship("Contract", back_populates="chunks")
    children : Mapped[list["ContractChunk"]] = relationship(
        "ContractChunk", backref=backref("parent", remote_side="ContractChunk.id")
    )


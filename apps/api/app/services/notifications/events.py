"""
Claustor AI — Notification Events
All 35 notification event types with payload schemas.
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class NotificationEvent(str, Enum):
    # User Lifecycle
    WELCOME_INVITE        = "welcome_invite"
    INVITATION_ACCEPTED   = "invitation_accepted"
    PASSWORD_RESET        = "password_reset"
    NEW_DEVICE_LOGIN      = "new_device_login"
    PASSWORD_CHANGED      = "password_changed"
    MFA_ENABLED           = "mfa_enabled"

    # Contract Lifecycle
    CONTRACT_UPLOADED     = "contract_uploaded"
    AI_ANALYSIS_COMPLETE  = "ai_analysis_complete"
    HIGH_RISK_DETECTED    = "high_risk_detected"
    CONTRACT_EXPIRING     = "contract_expiring"
    CONTRACT_EXPIRED      = "contract_expired"
    RENEWAL_REQUIRED      = "renewal_required"

    # Review Workflow
    REVIEW_ASSIGNED       = "review_assigned"
    REVIEW_REMINDER       = "review_reminder"
    REVIEW_COMPLETED      = "review_completed"
    REVIEW_REJECTED       = "review_rejected"
    CHANGES_REQUESTED     = "changes_requested"
    APPROVAL_REQUESTED    = "approval_requested"
    CONTRACT_APPROVED     = "contract_approved"
    CONTRACT_REJECTED     = "contract_rejected"

    # Obligations
    OBLIGATION_DUE        = "obligation_due"
    OBLIGATION_OVERDUE    = "obligation_overdue"

    # Collaboration
    USER_MENTIONED        = "user_mentioned"
    COMMENT_ADDED         = "comment_added"

    # Billing
    TRIAL_STARTED         = "trial_started"
    TRIAL_ENDING          = "trial_ending"
    PAYMENT_SUCCESSFUL    = "payment_successful"
    PAYMENT_FAILED        = "payment_failed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    PLAN_DOWNGRADED       = "plan_downgraded"
    INVOICE_GENERATED     = "invoice_generated"
    STORAGE_LIMIT_REACHED = "storage_limit_reached"
    QUERY_LIMIT_REACHED   = "query_limit_reached"

    # System
    AI_SERVICE_DEGRADED   = "ai_service_degraded"
    SCHEDULED_MAINTENANCE = "scheduled_maintenance"


@dataclass
class NotificationPayload:
    """Base payload — all notifications carry these fields."""
    event:          NotificationEvent
    recipient_email: str
    recipient_name: str
    org_name:       str = ""
    action_url:     str = ""

    # Contract context (optional)
    contract_name:  Optional[str] = None
    contract_id:    Optional[str] = None

    # Dynamic fields
    extra:          dict = field(default_factory=dict)

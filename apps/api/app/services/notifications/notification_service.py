"""
Claustor AI — Centralized Notification Service
Single entry point for all email notifications.
Configurable via notifications.yml — no code change to add new templates.
"""
from __future__ import annotations
import os
import re
import structlog
from typing import Optional
from pathlib import Path

from app.services.notifications.events import NotificationEvent, NotificationPayload

logger = structlog.get_logger(__name__)

BASE_URL = os.getenv("BASE_URL", "https://claustor.ai")

# Load config once at startup
_config: dict = {}

def _load_config() -> dict:
    global _config
    if _config:
        return _config
    try:
        import yaml
        config_path = Path(__file__).parent / "config" / "notifications.yml"
        with open(config_path) as f:
            _config = yaml.safe_load(f)
    except Exception as e:
        logger.warning("notification_config_load_failed", error=str(e))
        _config = {}
    return _config


def _render_template(template_str: str, context: dict) -> str:
    """Simple {key} substitution — no Jinja2 dependency needed."""
    result = template_str
    for key, val in context.items():
        result = result.replace(f"{{{key}}}", str(val) if val else "")
    return result


def _render_base(
    subject: str,
    recipient_name: str,
    content_block: str,
    action_url: str,
    cta_label: str,
    accent_color: str,
    category: str,
    secondary_block: str = "",
    unsubscribe_url: str = "",
) -> str:
    """Render the branded base HTML template."""
    template_path = Path(__file__).parent / "templates" / "base.html"
    try:
        with open(template_path) as f:
            base = f.read()
    except Exception:
        # Minimal fallback
        base = "<html><body>{{ content_block }}</body></html>"

    # Replace Jinja-style blocks manually
    result = base
    result = result.replace("{{ subject }}", subject)
    result = result.replace("{{ recipient_name }}", recipient_name)
    result = result.replace("{{ accent_color }}", accent_color)
    result = result.replace("{{ category | upper }}", category.upper())
    result = result.replace("{{ content_block }}", content_block)
    result = result.replace("{{ cta_label }}", cta_label)
    result = result.replace("{{ unsubscribe_url }}", unsubscribe_url or f"{BASE_URL}/unsubscribe")

    # Handle conditional action_url block
    if action_url:
        result = result.replace("{% if action_url %}", "")
        result = result.replace("{% endif %}", "")
        result = result.replace("{{ action_url }}", action_url)
    else:
        # Remove the if block
        result = re.sub(r'{%\s*if action_url\s*%}.*?{%\s*endif\s*%}', '', result, flags=re.DOTALL)

    # Handle secondary_block
    if secondary_block:
        result = result.replace("{% if secondary_block %}", "")
        result = result.replace("{% endif %}", "")
        result = result.replace("{{ secondary_block }}", secondary_block)
    else:
        result = re.sub(r'{%\s*if secondary_block\s*%}.*?{%\s*endif\s*%}', '', result, flags=re.DOTALL)

    return result


# ── Content block builders per event category ──────────────────────────────

def _content_contract_lifecycle(payload: NotificationPayload, event_key: str) -> tuple[str, str]:
    """Returns (content_block, secondary_block)."""
    contract = payload.contract_name or "your contract"
    extra = payload.extra

    if event_key == "contract_uploaded":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          Your contract <strong>{contract}</strong> has been successfully uploaded to Claustor AI.
          Our AI is now analysing the document — you'll receive another notification when the analysis is complete.
        </p>"""
        secondary = f"""
        <p style="font-size:13px;color:#6B7280;margin:0 0 6px;font-weight:600;">WHAT HAPPENS NEXT</p>
        <p style="font-size:13px;color:#374151;margin:0;">
          ✓ Clause extraction (25 types)<br/>
          ✓ Risk scoring + playbook matching<br/>
          ✓ Party identifier extraction<br/>
          ✓ Obligation tracking setup
        </p>"""

    elif event_key == "ai_analysis_complete":
        risk = extra.get("risk_level", "medium")
        clause_count = extra.get("clause_count", 0)
        risk_color = {"high": "#EF4444", "medium": "#F59E0B", "low": "#22C55E"}.get(risk, "#6B7280")
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          AI analysis of <strong>{contract}</strong> is complete.
          We extracted <strong>{clause_count} clauses</strong> and scored the overall risk level as
          <strong style="color:{risk_color};">{risk.upper()}</strong>.
        </p>"""
        secondary = f"""
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Clauses Extracted</td>
            <td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{clause_count}</td>
          </tr>
          <tr>
            <td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Risk Level</td>
            <td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:700;font-size:13px;text-align:right;color:{risk_color};">{risk.upper()}</td>
          </tr>
          <tr>
            <td style="padding:8px 0;color:#6B7280;font-size:13px;">High Risk Clauses</td>
            <td style="padding:8px 0;font-weight:600;font-size:13px;text-align:right;color:#EF4444;">{extra.get("high_risk_count", 0)}</td>
          </tr>
        </table>"""

    elif event_key == "high_risk_detected":
        count = extra.get("high_risk_count", 1)
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          Our AI has detected <strong style="color:#EF4444;">{count} high-risk clause{'s' if count != 1 else ''}</strong>
          in <strong>{contract}</strong> that require your immediate attention.
        </p>"""
        clauses = extra.get("risk_clauses", [])
        rows = "".join([
            f'<tr><td style="padding:6px 0;font-size:13px;color:#374151;">⚠️ {c}</td></tr>'
            for c in clauses[:5]
        ])
        secondary = f"""
        <p style="font-size:13px;color:#EF4444;font-weight:700;margin:0 0 10px;">HIGH RISK CLAUSES</p>
        <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>"""

    elif event_key == "contract_expiring":
        days = extra.get("days", 30)
        expiry = extra.get("expiry_date", "")
        color = "#EF4444" if days <= 7 else "#F59E0B"
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          <strong>{contract}</strong> is expiring in
          <strong style="color:{color};">{days} days</strong>
          {f"on <strong>{expiry}</strong>" if expiry else ""}.
          Please review and take action before the contract expires.
        </p>"""
        secondary = f"""
        <p style="font-size:13px;color:#6B7280;margin:0;">
          <strong>Action Required:</strong> Review the contract and initiate renewal or termination procedures as appropriate.
        </p>"""

    elif event_key == "renewal_required":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          <strong>{contract}</strong> requires renewal. Please initiate the renewal process to avoid any service disruption.
        </p>"""
        secondary = ""

    else:
        content = f'<p style="font-size:15px;color:#374151;margin:0;">{contract} requires your attention.</p>'
        secondary = ""

    return content, secondary


def _content_review(payload: NotificationPayload, event_key: str) -> tuple[str, str]:
    contract = payload.contract_name or "a contract"
    extra = payload.extra

    if event_key == "review_assigned":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          You have been assigned to review <strong>{contract}</strong>.
        </p>"""
        secondary = f"""
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td style="padding:6px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Assigned By</td>
              <td style="padding:6px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{extra.get("assigned_by","")}</td></tr>
          <tr><td style="padding:6px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Due Date</td>
              <td style="padding:6px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{extra.get("due_date","")}</td></tr>
          <tr><td style="padding:6px 0;color:#6B7280;font-size:13px;">Priority</td>
              <td style="padding:6px 0;font-weight:700;font-size:13px;text-align:right;color:#F59E0B;">{extra.get("priority","Normal").upper()}</td></tr>
        </table>"""

    elif event_key == "review_completed":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          <strong>{extra.get("reviewer","")}</strong> has completed the review of
          <strong>{contract}</strong>.
        </p>"""
        secondary = f"""
        <p style="font-size:13px;color:#6B7280;margin:0 0 6px;font-weight:600;">RECOMMENDATION</p>
        <p style="font-size:14px;color:#374151;margin:0;font-weight:600;">{extra.get("recommendation","")}</p>
        {"<p style='font-size:13px;color:#6B7280;margin:8px 0 0;'>" + extra.get("summary","") + "</p>" if extra.get("summary") else ""}"""

    elif event_key in ("review_rejected", "changes_requested"):
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          {"Changes have been requested" if event_key == "changes_requested" else "The review has been rejected"} for
          <strong>{contract}</strong>.
          Please review the feedback and make the necessary updates.
        </p>"""
        secondary = f"""
        <p style="font-size:13px;color:#6B7280;margin:0 0 6px;font-weight:600;">FEEDBACK</p>
        <p style="font-size:13px;color:#374151;margin:0;">{extra.get("feedback","Please see the review comments.")}</p>"""

    elif event_key == "approval_requested":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          Your approval is required for <strong>{contract}</strong>.
          Requested by <strong>{extra.get("requested_by","")}</strong>.
        </p>"""
        secondary = ""

    elif event_key in ("contract_approved", "contract_rejected"):
        approved = event_key == "contract_approved"
        status_color = "#22C55E" if approved else "#EF4444"
        status_text = "APPROVED" if approved else "REJECTED"
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          <strong>{contract}</strong> has been
          <strong style="color:{status_color};">{status_text}</strong>
          by <strong>{extra.get("reviewer","")}</strong>.
        </p>"""
        secondary = f'<p style="font-size:13px;color:#374151;margin:0;">{extra.get("notes","")}</p>' if extra.get("notes") else ""

    else:
        content = f'<p style="font-size:15px;color:#374151;margin:0;">Review update for {contract}.</p>'
        secondary = ""

    return content, secondary


def _content_billing(payload: NotificationPayload, event_key: str) -> tuple[str, str]:
    extra = payload.extra
    org = payload.org_name

    if event_key == "payment_successful":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          Payment of <strong style="color:#22C55E;">{extra.get("amount","")}</strong> for
          <strong>{org}</strong>'s {extra.get("plan","").title()} plan has been received successfully.
        </p>"""
        secondary = f"""
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td style="padding:6px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Plan</td>
              <td style="padding:6px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{extra.get("plan","").title()}</td></tr>
          <tr><td style="padding:6px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Amount</td>
              <td style="padding:6px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{extra.get("amount","")}</td></tr>
          <tr><td style="padding:6px 0;color:#6B7280;font-size:13px;">Next Billing</td>
              <td style="padding:6px 0;font-weight:600;font-size:13px;text-align:right;">{extra.get("next_date","")}</td></tr>
        </table>"""

    elif event_key == "payment_failed":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          We were unable to process the payment for <strong>{org}</strong>'s subscription.
          Please update your payment details to avoid service interruption.
        </p>"""
        secondary = f"""
        <p style="font-size:13px;color:#EF4444;font-weight:600;margin:0 0 8px;">⚠️ ACTION REQUIRED</p>
        <p style="font-size:13px;color:#374151;margin:0;">
          We will retry the payment in 3 days. If unsuccessful, your account may be downgraded.
          Update your payment method to prevent any disruption.
        </p>"""

    elif event_key == "trial_started":
        days = extra.get("trial_days", 14)
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          Your <strong>{extra.get("plan","Starter").title()} plan trial</strong> for
          <strong>{org}</strong> has started! You have <strong>{days} days</strong>
          to explore all features.
        </p>"""
        secondary = """
        <p style="font-size:13px;color:#6B7280;margin:0 0 8px;font-weight:600;">QUICK START</p>
        <p style="font-size:13px;color:#374151;margin:0;">
          ✓ Upload your first contract<br/>
          ✓ Ask the AI Copilot a question<br/>
          ✓ Review the risk report<br/>
          ✓ Set up obligation alerts
        </p>"""

    elif event_key == "invoice_generated":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          Your invoice for <strong>{extra.get("amount","")}</strong>
          ({extra.get("plan","").title()} Plan — {extra.get("period","")}) is ready.
        </p>"""
        secondary = ""

    else:
        content = f'<p style="font-size:15px;color:#374151;margin:0;">Billing update for {org}.</p>'
        secondary = ""

    return content, secondary


def _content_user(payload: NotificationPayload, event_key: str) -> tuple[str, str]:
    extra = payload.extra

    if event_key == "welcome_invite":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          You've been invited to join <strong>{payload.org_name}</strong> on Claustor AI —
          the enterprise contract intelligence platform.
        </p>
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          Click the button below to set up your account and get started.
        </p>"""
        secondary = """
        <p style="font-size:13px;color:#6B7280;margin:0 0 8px;font-weight:600;">WITH CLAUSTOR AI YOU CAN</p>
        <p style="font-size:13px;color:#374151;margin:0;">
          ✓ Analyse contracts in under 30 seconds<br/>
          ✓ Ask questions in plain English<br/>
          ✓ Detect high-risk clauses automatically<br/>
          ✓ Never miss a renewal deadline
        </p>"""

    elif event_key == "password_reset":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          We received a request to reset the password for your Claustor AI account.
          Click the button below to create a new password.
        </p>
        <p style="font-size:13px;color:#9CA3AF;margin:0;">
          This link expires in <strong>1 hour</strong>. If you didn't request this, you can safely ignore this email.
        </p>"""
        secondary = ""

    elif event_key == "new_device_login":
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          A new sign-in to your Claustor AI account was detected from a new device or location.
        </p>"""
        secondary = f"""
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td style="padding:6px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Device</td>
              <td style="padding:6px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{extra.get("device","Unknown")}</td></tr>
          <tr><td style="padding:6px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Location</td>
              <td style="padding:6px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{extra.get("location","Unknown")}</td></tr>
          <tr><td style="padding:6px 0;color:#6B7280;font-size:13px;">Time</td>
              <td style="padding:6px 0;font-weight:600;font-size:13px;text-align:right;">{extra.get("time","")}</td></tr>
        </table>
        <p style="font-size:13px;color:#EF4444;font-weight:600;margin:12px 0 0;">
          If this wasn't you, secure your account immediately.
        </p>"""

    else:
        content = f'<p style="font-size:15px;color:#374151;margin:0;">Account update from Claustor AI.</p>'
        secondary = ""

    return content, secondary


def _content_obligation(payload: NotificationPayload, event_key: str) -> tuple[str, str]:
    extra = payload.extra
    contract = payload.contract_name or "your contract"
    days = extra.get("days", 1)

    if event_key == "obligation_due":
        days_label = "Tomorrow" if days == 1 else f"in {days} days"
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          An obligation from <strong>{contract}</strong> is due <strong style="color:#F59E0B;">{days_label}</strong>.
        </p>"""
    else:
        content = f"""
        <p style="font-size:15px;color:#374151;line-height:1.7;margin:0 0 16px;">
          An obligation from <strong>{contract}</strong> is <strong style="color:#EF4444;">overdue</strong>.
          Please take immediate action.
        </p>"""

    secondary = f"""
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;font-size:13px;">Obligation</td>
          <td style="padding:6px 0;border-bottom:1px solid #E5E7EB;font-weight:600;font-size:13px;text-align:right;">{extra.get("obligation_title","")}</td></tr>
      <tr><td style="padding:6px 0;color:#6B7280;font-size:13px;">Due Date</td>
          <td style="padding:6px 0;font-weight:600;font-size:13px;text-align:right;">{extra.get("due_date","")}</td></tr>
    </table>"""

    return content, secondary


# ── Main dispatcher ────────────────────────────────────────────────────────

CONTENT_BUILDERS = {
    "contract": _content_contract_lifecycle,
    "review":   _content_review,
    "billing":  _content_billing,
    "user":     _content_user,
    "security": _content_user,
    "obligation": _content_obligation,
}

EVENT_CATEGORIES = {
    NotificationEvent.WELCOME_INVITE:       "user",
    NotificationEvent.INVITATION_ACCEPTED:  "user",
    NotificationEvent.PASSWORD_RESET:       "security",
    NotificationEvent.NEW_DEVICE_LOGIN:     "security",
    NotificationEvent.PASSWORD_CHANGED:     "security",
    NotificationEvent.MFA_ENABLED:          "security",
    NotificationEvent.CONTRACT_UPLOADED:    "contract",
    NotificationEvent.AI_ANALYSIS_COMPLETE: "contract",
    NotificationEvent.HIGH_RISK_DETECTED:   "contract",
    NotificationEvent.CONTRACT_EXPIRING:    "contract",
    NotificationEvent.CONTRACT_EXPIRED:     "contract",
    NotificationEvent.RENEWAL_REQUIRED:     "contract",
    NotificationEvent.REVIEW_ASSIGNED:      "review",
    NotificationEvent.REVIEW_REMINDER:      "review",
    NotificationEvent.REVIEW_COMPLETED:     "review",
    NotificationEvent.REVIEW_REJECTED:      "review",
    NotificationEvent.CHANGES_REQUESTED:    "review",
    NotificationEvent.APPROVAL_REQUESTED:   "review",
    NotificationEvent.CONTRACT_APPROVED:    "review",
    NotificationEvent.CONTRACT_REJECTED:    "review",
    NotificationEvent.OBLIGATION_DUE:       "obligation",
    NotificationEvent.OBLIGATION_OVERDUE:   "obligation",
    NotificationEvent.USER_MENTIONED:       "collaboration",
    NotificationEvent.COMMENT_ADDED:        "collaboration",
    NotificationEvent.TRIAL_STARTED:        "billing",
    NotificationEvent.TRIAL_ENDING:         "billing",
    NotificationEvent.PAYMENT_SUCCESSFUL:   "billing",
    NotificationEvent.PAYMENT_FAILED:       "billing",
    NotificationEvent.SUBSCRIPTION_EXPIRING:"billing",
    NotificationEvent.PLAN_DOWNGRADED:      "billing",
    NotificationEvent.INVOICE_GENERATED:    "billing",
    NotificationEvent.STORAGE_LIMIT_REACHED:"billing",
    NotificationEvent.QUERY_LIMIT_REACHED:  "billing",
    NotificationEvent.AI_SERVICE_DEGRADED:  "system",
    NotificationEvent.SCHEDULED_MAINTENANCE:"system",
}


async def send_notification(payload: NotificationPayload) -> bool:
    """
    Central notification dispatcher.
    Resolves config, builds HTML, sends via email service.
    """
    from app.services.email_service import send_email

    config = _load_config()
    event_key = payload.event.value
    event_config = config.get(event_key, {})

    # Resolve subject with template vars
    subject_template = event_config.get("subject", f"Claustor AI Notification")
    subject = _render_template(subject_template, {
        **payload.extra,
        "contract_name": payload.contract_name or "",
        "recipient_name": payload.recipient_name,
        "org_name": payload.org_name,
    })

    accent_color = event_config.get("color", "#0066FF")
    cta_label = event_config.get("cta_label", "View in Claustor")
    category = event_config.get("category", "system")

    # Build content block
    category_key = EVENT_CATEGORIES.get(payload.event, "system")
    builder = CONTENT_BUILDERS.get(category_key, CONTENT_BUILDERS["user"])
    content_block, secondary_block = builder(payload, event_key)

    # Resolve action URL
    action_url = payload.action_url or f"{BASE_URL}/dashboard"

    # Render full email
    html = _render_base(
        subject=subject,
        recipient_name=payload.recipient_name,
        content_block=content_block,
        action_url=action_url,
        cta_label=cta_label,
        accent_color=accent_color,
        category=category,
        secondary_block=secondary_block,
        unsubscribe_url=f"{BASE_URL}/unsubscribe",
    )

    # Send
    success = await send_email(
        to=payload.recipient_email,
        subject=subject,
        html=html,
    )

    logger.info("notification_sent",
                event=event_key,
                to=payload.recipient_email,
                success=success)
    return success

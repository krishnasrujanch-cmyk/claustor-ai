"""
Claustor AI — Email Service
Shared email sending via Resend.
"""

import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)


async def send_email(to: str, subject: str, html: str) -> bool:
    """
    Send email via Resend.
    Returns True if sent, False if failed/skipped.
    """
    if not settings.RESEND_API_KEY:
        logger.warning("email_skipped", reason="no_resend_key", to=to, subject=subject)
        return False

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY

        resend.Emails.send({
            "from":    "Claustor AI <onboarding@resend.dev>",
            "to":      [to],
            "subject": subject,
            "html":    html,
        })
        logger.info("email_sent", to=to, subject=subject[:50])
        return True

    except Exception as e:
        logger.warning("email_failed", to=to, subject=subject[:50], error=str(e))
        return False


def review_assigned_html(
    reviewer_name: str,
    contract_title: str,
    priority: str,
    due_date: str,
    assigned_by: str,
) -> str:
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
      <div style="background:#5B4BFF;padding:20px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:20px">📋 Review Assignment</h1>
      </div>
      <div style="background:#FFFFFF;border:1px solid #E5E7EB;padding:24px;border-radius:0 0 12px 12px">
        <p style="color:#374151">Hi {reviewer_name},</p>
        <p style="color:#374151">{assigned_by} has assigned a contract for your review:</p>
        <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin:16px 0">
          <div style="font-size:16px;font-weight:700;color:#111827;margin-bottom:8px">{contract_title}</div>
          <div style="color:#6B7280;font-size:14px">Priority: <strong style="color:{'#EF4444' if priority=='high' else '#F59E0B'}">{priority.upper()}</strong></div>
          <div style="color:#6B7280;font-size:14px">Due: {due_date}</div>
        </div>
        <a href="http://localhost:3000/dashboard/reviews"
           style="display:inline-block;background:#5B4BFF;color:white;padding:12px 24px;
                  border-radius:8px;text-decoration:none;font-weight:600;margin-top:8px">
          Review Now →
        </a>
        <p style="color:#9CA3AF;font-size:12px;margin-top:24px">
          Claustor AI Contract Intelligence Platform
        </p>
      </div>
    </div>
    """


def contract_analyzed_html(
    user_name: str,
    contract_title: str,
    risk_level: str,
    clause_count: int,
) -> str:
    risk_color = {"high":"#EF4444","medium":"#F59E0B","low":"#22C55E"}.get(risk_level,"#6B7280")
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
      <div style="background:#5B4BFF;padding:20px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:20px">✅ Contract Analysis Complete</h1>
      </div>
      <div style="background:#FFFFFF;border:1px solid #E5E7EB;padding:24px;border-radius:0 0 12px 12px">
        <p style="color:#374151">Hi {user_name},</p>
        <p style="color:#374151">Your contract has been analyzed:</p>
        <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin:16px 0">
          <div style="font-size:16px;font-weight:700;color:#111827;margin-bottom:8px">{contract_title}</div>
          <div style="color:#6B7280;font-size:14px">Risk: <strong style="color:{risk_color}">{risk_level.upper()}</strong></div>
          <div style="color:#6B7280;font-size:14px">Clauses extracted: {clause_count}</div>
        </div>
        <a href="http://localhost:3000/dashboard/contracts"
           style="display:inline-block;background:#5B4BFF;color:white;padding:12px 24px;
                  border-radius:8px;text-decoration:none;font-weight:600;margin-top:8px">
          View Contract →
        </a>
      </div>
    </div>
    """

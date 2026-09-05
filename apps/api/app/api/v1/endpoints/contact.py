"""
Claustor AI — Public Contact Endpoint
======================================
Landing page contact forms — no auth required, rate limited.
"""
import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from datetime import datetime

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])

# Simple in-memory rate limit — max 5 per IP per hour
_rate_limit: dict[str, list[float]] = {}
MAX_REQUESTS_PER_HOUR = 5


def _check_rate_limit(ip: str) -> bool:
    now = datetime.utcnow().timestamp()
    if ip not in _rate_limit:
        _rate_limit[ip] = []
    # Remove entries older than 1 hour
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < 3600]
    if len(_rate_limit[ip]) >= MAX_REQUESTS_PER_HOUR:
        return False
    _rate_limit[ip].append(now)
    return True


class ContactRequest(BaseModel):
    name: str = ""
    contact_name: str = ""
    email: str = ""
    business_email: str = ""
    company: str = ""
    business_name: str = ""
    size: str = ""
    company_size: str = ""
    message: str = ""
    industry: str = ""
    usecase: str = ""
    source: str = "landing_page"
    country: str = ""
    mobile: str = ""
    contracts_per_month: str = ""

    @property
    def resolved_name(self) -> str:
        return self.contact_name or self.name or "Unknown"

    @property
    def resolved_email(self) -> str:
        return self.business_email or self.email or ""

    @property
    def resolved_company(self) -> str:
        return self.business_name or self.company or ""

    @property
    def resolved_size(self) -> str:
        return self.company_size or self.size or ""


@router.post("/inquiry")
async def public_contact(req: ContactRequest, request: Request):
    """
    Public contact form — no auth required.
    Rate limited: 5 requests per IP per hour.
    """
    client_ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")

    if not req.resolved_name or not req.resolved_email:
        raise HTTPException(status_code=400, detail="Name and email are required.")

    try:
        import httpx
        from app.core.config import settings

        # Send notification to support
        await _send_email(
            settings=settings,
            to="support@claustor.com",
            subject=f"New Inquiry — {req.resolved_name} ({req.resolved_company or 'No company'})",
            html=f"""
            <h2>New Contact Form Submission</h2>
            <table style="border-collapse:collapse;width:100%">
                <tr><td style="padding:8px;border:1px solid #ddd"><strong>Name</strong></td><td style="padding:8px;border:1px solid #ddd">{req.resolved_name}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd"><strong>Email</strong></td><td style="padding:8px;border:1px solid #ddd">{req.resolved_email}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd"><strong>Company</strong></td><td style="padding:8px;border:1px solid #ddd">{req.resolved_company or '—'}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd"><strong>Team Size</strong></td><td style="padding:8px;border:1px solid #ddd">{req.resolved_size or '—'}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd"><strong>Message</strong></td><td style="padding:8px;border:1px solid #ddd">{req.message or '—'}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd"><strong>Source</strong></td><td style="padding:8px;border:1px solid #ddd">{req.source}</td></tr>
            </table>
            """,
        )

        # Send auto-reply to user
        await _send_email(
            settings=settings,
            to=req.resolved_email,
            subject="Thanks for contacting Claustor AI",
            html=f"""
            <div style="font-family:sans-serif;max-width:600px">
                <h2 style="color:#5B4BFF">Thanks for reaching out, {req.resolved_name}!</h2>
                <p>We've received your inquiry and our team will get back to you within 4 business hours.</p>
                <p>In the meantime, feel free to explore our platform at <a href="https://claustor.com">claustor.com</a>.</p>
                <br>
                <p style="color:#64748B;font-size:13px">— The Claustor AI Team</p>
            </div>
            """,
        )

        logger.info("public_contact_received",
                     name=req.resolved_name, email=req.resolved_email, source=req.source)

        return {"status": "sent", "message": "We'll get back to you within 4 business hours."}

    except Exception as e:
        logger.error("public_contact_failed", error=str(e)[:200])
        raise HTTPException(status_code=500, detail="Failed to send. Please email support@claustor.com directly.")


async def _send_email(settings, to: str, subject: str, html: str):
    """Send email via Resend."""
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": f"Claustor AI <{settings.RESEND_FROM}>",
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        r.raise_for_status()

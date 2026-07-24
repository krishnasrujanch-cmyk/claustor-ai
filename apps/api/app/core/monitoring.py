"""
Claustor AI — Monitoring & Error Tracking
Sentry integration for production error tracking.
Activate: set SENTRY_DSN in .env
"""

import structlog

logger = structlog.get_logger(__name__)


def init_sentry(dsn: str, environment: str = "production") -> None:
    """
    Initialize Sentry error tracking.
    Called once at app startup.
    """
    if not dsn:
        logger.info("sentry_disabled", reason="SENTRY_DSN not set")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.asyncio import AsyncioIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                AsyncioIntegration(),
            ],
            traces_sample_rate=0.1,   # 10% of requests
            profiles_sample_rate=0.1,
            send_default_pii=False,    # GDPR: no PII
            before_send=_filter_events,
        )
        logger.info("sentry_initialized", environment=environment)

    except ImportError:
        logger.warning("sentry_sdk_not_installed", hint="pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.error("sentry_init_failed", error=str(e))


def _filter_events(event, hint):
    """
    Filter out noise before sending to Sentry.
    Don't send: 404s, 401s, rate limit errors.
    """
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        # Skip expected HTTP errors
        from fastapi import HTTPException
        if isinstance(exc_value, HTTPException):
            if exc_value.status_code in (401, 403, 404, 422, 429):
                return None

    return event


def capture_exception(error: Exception, context: dict | None = None) -> None:
    """Manually capture an exception to Sentry."""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if context:
                for k, v in context.items():
                    scope.set_extra(k, v)
            sentry_sdk.capture_exception(error)
    except Exception:
        pass  # Never let Sentry break the app

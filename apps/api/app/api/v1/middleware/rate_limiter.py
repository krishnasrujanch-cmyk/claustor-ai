"""
Claustor AI — Rate Limiting Middleware
Protects auth and API endpoints from brute force.
Uses Redis (Upstash) for distributed rate limiting.
"""
from __future__ import annotations
import time
import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

# Rate limit rules: (requests, window_seconds)
RATE_LIMITS = {
    "/api/v1/auth/login":    (5,  60),   # 5 per minute
    "/api/v1/auth/register": (3,  60),   # 3 per minute
    "/api/v1/auth/":         (10, 60),   # 10 per minute for other auth
    "/api/v1/chat/":         (60, 60),   # 60 per minute
    "/api/v1/":              (120, 60),  # 120 per minute general
}


def _get_client_ip(request: Request) -> str:
    """Get real client IP, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _match_rule(path: str) -> tuple[int, int] | None:
    """Find matching rate limit rule for path."""
    for pattern, limit in RATE_LIMITS.items():
        if path.startswith(pattern):
            return limit
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed rate limiting middleware."""

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self._redis = redis_client

    async def _get_redis(self):
        if self._redis:
            return self._redis
        try:
            from app.core.config import settings
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            return self._redis
        except Exception:
            return None

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        rule = _match_rule(path)
        print(f"[RateLimit] path={path} rule={rule}")

        if not rule:
            return await call_next(request)

        max_requests, window = rule
        ip = _get_client_ip(request)
        key = f"rate:{ip}:{path.split('?')[0]}"

        try:
            redis = await self._get_redis()
            if redis:
                current = await redis.incr(key)
                if current == 1:
                    await redis.expire(key, window)

                if current > max_requests:
                    logger.warning("rate_limit_exceeded",
                                   ip=ip, path=path, count=current)
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Too many requests. Please wait before trying again.",
                            "retry_after": window,
                        },
                        headers={"Retry-After": str(window)},
                    )
        except Exception as e:
            logger.warning("rate_limit_check_failed", error=str(e))
            # Fail open — don't block if Redis unavailable

        return await call_next(request)

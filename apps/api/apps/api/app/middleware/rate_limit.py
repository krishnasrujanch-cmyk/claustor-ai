"""
Claustor AI — Rate Limiting
Redis-based sliding window rate limiting.
Per-user + per-IP limits to prevent abuse.
"""

import time
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

# Rate limits per endpoint type
RATE_LIMITS = {
    "auth":      {"requests": 10,   "window_secs": 60},    # 10/min
    "upload":    {"requests": 20,   "window_secs": 3600},  # 20/hr
    "chat":      {"requests": 100,  "window_secs": 3600},  # 100/hr
    "api":       {"requests": 1000, "window_secs": 3600},  # 1000/hr
    "default":   {"requests": 200,  "window_secs": 60},    # 200/min
}

PLAN_MULTIPLIERS = {
    "free":         1.0,
    "starter":      2.0,
    "professional": 5.0,
    "enterprise":   20.0,
}


def get_limit_type(path: str) -> str:
    if "/auth/" in path:       return "auth"
    if "/contracts/" in path:  return "upload"
    if "/chat/" in path:       return "chat"
    return "default"


async def rate_limit_middleware(request: Request, call_next):
    """
    Sliding window rate limiting using Redis.
    Falls back gracefully if Redis unavailable.
    """
    try:
        from app.infrastructure.database.redis import get_redis
        redis = await get_redis()

        # Get identifier — prefer user ID from JWT, fallback to IP
        client_ip = request.client.host if request.client else "unknown"
        user_id = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                from app.core.config import settings
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, settings.JWT_SECRET_KEY,
                                    algorithms=[settings.JWT_ALGORITHM])
                user_id = payload.get("sub")
            except Exception:
                pass

        identifier = f"user:{user_id}" if user_id else f"ip:{client_ip}"
        limit_type = get_limit_type(request.url.path)
        limit_config = RATE_LIMITS[limit_type]

        # Sliding window counter
        now = int(time.time())
        window = limit_config["window_secs"]
        max_requests = limit_config["requests"]

        key = f"rl:{limit_type}:{identifier}"

        # Increment and expire
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        current_count = results[0]

        # Add rate limit headers
        remaining = max(0, max_requests - current_count)
        reset_time = now + window

        if current_count > max_requests:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                limit_type=limit_type,
                count=current_count,
                limit=max_requests,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after": window,
                },
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        return response

    except Exception as e:
        # Never block requests due to rate limiter failure
        logger.warning("rate_limiter_error", error=str(e))
        return await call_next(request)

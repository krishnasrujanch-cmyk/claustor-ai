"""
Claustor AI — Semantic Cache
Caches RAG answers in Redis to avoid repeat LLM calls.
Same query + same contract = instant response.

Cache key: hash(normalized_query + contract_id)
TTL: 1 hour (contract content doesn't change that often)
Invalidated: on contract re-upload/re-process
"""
import hashlib
import json
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

CACHE_TTL = 3600  # 1 hour
CACHE_PREFIX = "claustor:answer:"


def _build_cache_key(query: str, contract_id: str | None) -> str:
    """Build deterministic cache key from query + contract."""
    normalized = query.strip().lower()
    # Remove extra whitespace
    normalized = " ".join(normalized.split())
    raw = f"{normalized}:{contract_id or 'cross'}"
    return CACHE_PREFIX + hashlib.sha256(raw.encode()).hexdigest()[:24]


async def get_cached_answer(
    query: str,
    contract_id: str | None,
) -> Optional[dict]:
    """Check cache for existing answer. Returns dict or None."""
    try:
        from app.infrastructure.database.redis import get_redis
        redis = await get_redis()
        key = _build_cache_key(query, contract_id)
        cached = await redis.get(key)
        if cached:
            data = json.loads(cached)
            logger.info("cache_hit", query=query[:40], contract_id=str(contract_id)[:8] if contract_id else "cross")
            return data
    except Exception as e:
        logger.warning("cache_read_failed", error=str(e)[:60])
    return None


async def set_cached_answer(
    query: str,
    contract_id: str | None,
    answer: str,
    provider: str = "",
    tokens_used: int = 0,
) -> None:
    """Cache an answer for future identical queries."""
    try:
        from app.infrastructure.database.redis import get_redis
        redis = await get_redis()
        key = _build_cache_key(query, contract_id)
        data = {
            "answer": answer,
            "provider": f"cache:{provider}",
            "tokens_used": 0,
            "cached": True,
        }
        await redis.set(key, json.dumps(data), ex=CACHE_TTL)
        logger.info("cache_set", query=query[:40], key=key[-8:])
    except Exception as e:
        logger.warning("cache_write_failed", error=str(e)[:60])


async def invalidate_contract_cache(contract_id: str) -> int:
    """Invalidate all cached answers for a contract (on re-upload)."""
    try:
        from app.infrastructure.database.redis import get_redis
        redis = await get_redis()
        # Scan and delete all cache keys (prefix match)
        deleted = 0
        async for key in redis.scan_iter(match=f"{CACHE_PREFIX}*", count=100):
            await redis.delete(key)
            deleted += 1
        logger.info("cache_invalidated", contract_id=str(contract_id)[:8], deleted=deleted)
        return deleted
    except Exception as e:
        logger.warning("cache_invalidate_failed", error=str(e)[:60])
        return 0

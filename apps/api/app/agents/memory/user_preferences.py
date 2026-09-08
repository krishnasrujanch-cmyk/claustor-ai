"""
Claustor AI — Long-term User Preferences
Tracks what users ask about most and adjusts behavior.
Stored in Redis with long TTL (30 days).
"""
import json
import structlog
from typing import Optional
from uuid import UUID

logger = structlog.get_logger(__name__)

PREF_PREFIX = "claustor:prefs:"
PREF_TTL = 86400 * 30  # 30 days


async def track_query_topic(user_id: UUID, query: str) -> None:
    """Track which topics a user queries about most."""
    try:
        from app.infrastructure.database.redis import get_redis
        redis = await get_redis()
        key = f"{PREF_PREFIX}{user_id}:topics"
        
        # Detect topic from query keywords
        topic = _detect_topic(query)
        if topic:
            await redis.hincrby(key, topic, 1)
            await redis.expire(key, PREF_TTL)
    except Exception as e:
        logger.warning("pref_track_failed", error=str(e)[:60])


async def get_user_focus_areas(user_id: UUID, top_n: int = 3) -> list[str]:
    """Get the user's most-queried topics."""
    try:
        from app.infrastructure.database.redis import get_redis
        redis = await get_redis()
        key = f"{PREF_PREFIX}{user_id}:topics"
        
        topics = await redis.hgetall(key)
        if not topics:
            return []
        
        sorted_topics = sorted(topics.items(), key=lambda x: int(x[1]), reverse=True)
        return [t[0] for t in sorted_topics[:top_n]]
    except Exception as e:
        logger.warning("pref_load_failed", error=str(e)[:60])
        return []


def format_preferences_for_prompt(focus_areas: list[str]) -> str:
    """Format user preferences as LLM context."""
    if not focus_areas:
        return ""
    return f"USER FOCUS AREAS: This user frequently asks about: {', '.join(focus_areas)}. Prioritize these topics in your analysis."


def _detect_topic(query: str) -> Optional[str]:
    """Detect the primary topic of a query."""
    q = query.lower()
    topic_keywords = {
        "payment": ["payment", "invoice", "billing", "fee", "charge", "price", "cost", "amount"],
        "liability": ["liability", "cap", "limit", "indemnity", "damages"],
        "termination": ["terminat", "cancel", "exit", "end", "expire", "renew"],
        "risk": ["risk", "danger", "concern", "red flag", "issue"],
        "compliance": ["compliance", "regulatory", "gdpr", "dpdp", "audit"],
        "data_protection": ["data protection", "privacy", "personal data", "breach notification"],
        "sla": ["sla", "service level", "uptime", "availability", "performance"],
        "ip": ["intellectual property", "ip rights", "copyright", "patent", "license"],
        "confidentiality": ["confidential", "nda", "non-disclosure", "secret"],
        "insurance": ["insurance", "coverage", "policy", "indemnity"],
        "obligations": ["obligation", "duty", "must", "shall", "requirement"],
    }
    
    best_topic = None
    best_score = 0
    for topic, keywords in topic_keywords.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > best_score:
            best_score = score
            best_topic = topic
    
    return best_topic

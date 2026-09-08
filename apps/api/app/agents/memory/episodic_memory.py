"""
Claustor AI — Episodic Memory
Stores conversation summaries for cross-session recall.
"What did I ask about this contract last time?"
"""
import structlog
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

MAX_EPISODES = 10  # per user per contract


async def save_episode(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    contract_id: UUID | None,
    query: str,
    answer_summary: str,
) -> None:
    """Save a conversation episode after each interaction."""
    try:
        # Truncate summary to save space
        summary = answer_summary[:500] if answer_summary else ""
        await db.execute(text("""
            INSERT INTO conversation_episodes 
            (org_id, user_id, contract_id, query, answer_summary, created_at)
            VALUES (:org, :user, :contract, :query, :summary, NOW())
        """), {
            "org": str(org_id),
            "user": str(user_id),
            "contract": str(contract_id) if contract_id else None,
            "query": query[:200],
            "summary": summary,
        })
        await db.commit()
        logger.info("episode_saved", query=query[:40])
    except Exception as e:
        logger.warning("episode_save_failed", error=str(e)[:80])


async def get_past_episodes(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    contract_id: UUID | None = None,
    limit: int = 5,
) -> list[dict]:
    """Retrieve past conversation episodes for context."""
    try:
        if contract_id:
            r = await db.execute(text("""
                SELECT query, answer_summary, created_at
                FROM conversation_episodes
                WHERE org_id = :org AND user_id = :user AND contract_id = :contract
                ORDER BY created_at DESC LIMIT :lim
            """), {
                "org": str(org_id), "user": str(user_id),
                "contract": str(contract_id), "lim": limit,
            })
        else:
            r = await db.execute(text("""
                SELECT query, answer_summary, created_at
                FROM conversation_episodes
                WHERE org_id = :org AND user_id = :user
                ORDER BY created_at DESC LIMIT :lim
            """), {"org": str(org_id), "user": str(user_id), "lim": limit})

        episodes = []
        for row in r.fetchall():
            episodes.append({
                "query": row[0],
                "summary": row[1],
                "when": str(row[2]),
            })
        if episodes:
            logger.info("episodes_loaded", count=len(episodes))
        return episodes
    except Exception as e:
        logger.warning("episode_load_failed", error=str(e)[:80])
        return []


def format_episodes_for_prompt(episodes: list[dict]) -> str:
    """Format past episodes as context for the LLM prompt."""
    if not episodes:
        return ""
    lines = ["PAST CONVERSATIONS (for context):"]
    for ep in episodes:
        lines.append(f"- Q: {ep['query']} → {ep['summary'][:100]}")
    return "\n".join(lines)

"""
Claustor AI — Entity Memory
Tracks key entities (vendors, amounts, dates, clauses) across conversations.
Enables: "Who is the vendor in my last 3 contracts?"
         "What liability caps have I seen across contracts?"
"""
import json
import re
import structlog
from uuid import UUID
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


async def extract_and_save_entities(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    contract_id: UUID | None,
    query: str,
    answer: str,
) -> int:
    """Extract entities from Q&A and save to DB."""
    entities = _extract_entities(query, answer)
    if not entities:
        return 0

    saved = 0
    for entity in entities:
        try:
            await db.execute(text("""
                INSERT INTO entity_memory
                (org_id, user_id, contract_id, entity_type, entity_value, context, created_at)
                VALUES (:org, :user, :contract, :etype, :evalue, :ctx, NOW())
                ON CONFLICT DO NOTHING
            """), {
                "org": str(org_id),
                "user": str(user_id),
                "contract": str(contract_id) if contract_id else None,
                "etype": entity["type"],
                "evalue": entity["value"],
                "ctx": entity.get("context", "")[:200],
            })
            saved += 1
        except Exception as e:
            logger.warning("entity_save_failed", error=str(e)[:60])
    
    if saved:
        await db.commit()
        logger.info("entities_saved", count=saved)
    return saved


async def get_entities(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    entity_type: str | None = None,
    contract_id: UUID | None = None,
    limit: int = 20,
) -> list[dict]:
    """Retrieve stored entities, optionally filtered."""
    try:
        conditions = ["org_id = :org"]
        params = {"org": str(org_id), "lim": limit}

        if contract_id:
            conditions.append("contract_id = :contract")
            params["contract"] = str(contract_id)
        if entity_type:
            conditions.append("entity_type = :etype")
            params["etype"] = entity_type

        where = " AND ".join(conditions)
        r = await db.execute(text(f"""
            SELECT entity_type, entity_value, context, contract_id, created_at
            FROM entity_memory
            WHERE {where}
            ORDER BY created_at DESC LIMIT :lim
        """), params)

        entities = []
        for row in r.fetchall():
            entities.append({
                "type": row[0],
                "value": row[1],
                "context": row[2],
                "contract_id": str(row[3]) if row[3] else None,
                "when": str(row[4]),
            })
        if entities:
            logger.info("entities_loaded", count=len(entities))
        return entities
    except Exception as e:
        logger.warning("entity_load_failed", error=str(e)[:60])
        return []


async def get_cross_contract_entities(
    db: AsyncSession,
    org_id: UUID,
    entity_type: str,
    limit: int = 10,
) -> list[dict]:
    """Get entities of a type across ALL contracts in an org."""
    try:
        r = await db.execute(text("""
            SELECT em.entity_value, em.context, em.contract_id, c.title
            FROM entity_memory em
            LEFT JOIN contracts c ON em.contract_id = c.id
            WHERE em.org_id = :org AND em.entity_type = :etype
            ORDER BY em.created_at DESC LIMIT :lim
        """), {"org": str(org_id), "etype": entity_type, "lim": limit})

        results = []
        for row in r.fetchall():
            results.append({
                "value": row[0],
                "context": row[1],
                "contract_id": str(row[2]) if row[2] else None,
                "contract_title": row[3] or "Unknown",
            })
        return results
    except Exception as e:
        logger.warning("cross_entity_failed", error=str(e)[:60])
        return []


def format_entities_for_prompt(entities: list[dict]) -> str:
    """Format entities as context for the LLM."""
    if not entities:
        return ""
    lines = ["KNOWN ENTITIES FROM PAST INTERACTIONS:"]
    for e in entities[:10]:
        lines.append(f"- {e['type']}: {e['value']} ({e.get('context', '')[:60]})")
    return "\n".join(lines)


def _extract_entities(query: str, answer: str) -> list[dict]:
    """Extract structured entities from query + answer text."""
    entities = []
    combined = f"{query}\n{answer}"

    # Money amounts
    for match in re.finditer(r'(?:USD|INR|EUR|GBP|\$|₹|£)\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|lakh|crore))?', combined, re.IGNORECASE):
        val = match.group().strip()
        # Get surrounding context
        start = max(0, match.start() - 40)
        end = min(len(combined), match.end() + 40)
        ctx = combined[start:end].replace("\n", " ").strip()
        entities.append({"type": "amount", "value": val, "context": ctx})

    # Percentages
    for match in re.finditer(r'\d+(?:\.\d+)?%', combined):
        val = match.group()
        start = max(0, match.start() - 40)
        end = min(len(combined), match.end() + 40)
        ctx = combined[start:end].replace("\n", " ").strip()
        entities.append({"type": "percentage", "value": val, "context": ctx})

    # Dates (ISO and common formats)
    for match in re.finditer(r'\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', combined, re.IGNORECASE):
        val = match.group()
        start = max(0, match.start() - 40)
        end = min(len(combined), match.end() + 40)
        ctx = combined[start:end].replace("\n", " ").strip()
        entities.append({"type": "date", "value": val, "context": ctx})

    # Time periods
    for match in re.finditer(r'\d+\s*(?:days?|months?|years?|hours?|weeks?|business days?)', combined, re.IGNORECASE):
        val = match.group().strip()
        start = max(0, match.start() - 40)
        end = min(len(combined), match.end() + 40)
        ctx = combined[start:end].replace("\n", " ").strip()
        entities.append({"type": "time_period", "value": val, "context": ctx})

    # Clause references
    for match in re.finditer(r'(?:Clause|Section|Article|Schedule)\s+[\d.]+', combined, re.IGNORECASE):
        val = match.group().strip()
        start = max(0, match.start() - 40)
        end = min(len(combined), match.end() + 40)
        ctx = combined[start:end].replace("\n", " ").strip()
        entities.append({"type": "clause_ref", "value": val, "context": ctx})

    # Deduplicate by value
    seen = set()
    unique = []
    for e in entities:
        key = f"{e['type']}:{e['value']}"
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique[:30]  # cap at 30 entities per interaction

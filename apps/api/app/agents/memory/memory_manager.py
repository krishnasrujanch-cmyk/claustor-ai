"""
Claustor AI — Memory Manager

Three tiers:
  Tier 1: Short-term  — sliding window + summarization
  Tier 2: Long-term   — user query patterns per user
  Tier 3: Org-level   — cross-contract insights
"""

import uuid
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import Base

logger = structlog.get_logger(__name__)

SUMMARY_THRESHOLD = {
    "free":         4,
    "starter":      12,
    "professional": 24,
    "enterprise":   48,
}


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    id            = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id        = Column(PGUUID(as_uuid=True), nullable=False)
    user_id       = Column(PGUUID(as_uuid=True), nullable=False)
    contract_id   = Column(PGUUID(as_uuid=True), nullable=True)
    summary       = Column(Text, nullable=False)
    turns_covered = Column(Integer, default=0)
    tokens_saved  = Column(Integer, default=0)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserQueryMemory(Base):
    __tablename__ = "user_query_memory"
    id            = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id        = Column(PGUUID(as_uuid=True), nullable=False)
    user_id       = Column(PGUUID(as_uuid=True), nullable=False)
    topic         = Column(String(100), nullable=False)
    query_count   = Column(Integer, default=1)
    last_query    = Column(Text)
    last_seen_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class OrgInsight(Base):
    __tablename__ = "org_insights"
    id            = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id        = Column(PGUUID(as_uuid=True), nullable=False)
    insight_type  = Column(String(50), nullable=False)
    title         = Column(String(255), nullable=False)
    description   = Column(Text, nullable=False)
    severity      = Column(String(20), default="info")
    contract_ids  = Column(JSONB, default=list)
    generated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active     = Column(Boolean, default=True)


class MemoryManager:
    """Manages all three memory tiers."""

    def __init__(self, db: AsyncSession, llm=None):
        self.db  = db
        self.llm = llm

    # ── TIER 1: Sliding window + summarization ─────────

    async def get_context(
        self,
        org_id: UUID,
        user_id: UUID,
        contract_id: UUID | None,
        plan: str,
    ) -> dict:
        """Load recent history + any summary of older turns."""
        from app.domain.models import Conversation

        threshold = SUMMARY_THRESHOLD.get(plan, 12)

        # Count total turns
        count_q = select(func.count(Conversation.id)).where(
            Conversation.org_id == org_id,
            Conversation.user_id == user_id,
        )
        if contract_id:
            count_q = count_q.where(Conversation.contract_id == contract_id)
        total = (await self.db.execute(count_q)).scalar() or 0

        # Load recent turns
        recent_q = (
            select(Conversation.role, Conversation.content)
            .where(Conversation.org_id == org_id, Conversation.user_id == user_id)
        )
        if contract_id:
            recent_q = recent_q.where(Conversation.contract_id == contract_id)
        recent_q = recent_q.order_by(Conversation.created_at.desc()).limit(threshold)
        rows = (await self.db.execute(recent_q)).fetchall()
        recent = [{"role": r.role, "content": r.content} for r in reversed(rows)]

        # Load existing summary
        summary = None
        if total > threshold:
            s_result = await self.db.execute(
                select(ConversationSummary.summary)
                .where(
                    ConversationSummary.org_id == org_id,
                    ConversationSummary.user_id == user_id,
                    ConversationSummary.contract_id == contract_id,
                )
                .order_by(ConversationSummary.created_at.desc())
                .limit(1)
            )
            row = s_result.fetchone()
            if row:
                summary = row.summary

        return {
            "recent":      recent,
            "summary":     summary,
            "total_turns": total,
        }

    async def maybe_summarize(
        self,
        org_id: UUID,
        user_id: UUID,
        contract_id: UUID | None,
        plan: str,
    ) -> None:
        """Summarize old turns when history gets long."""
        if not self.llm:
            return

        threshold = SUMMARY_THRESHOLD.get(plan, 12)
        ctx = await self.get_context(org_id, user_id, contract_id, plan)

        if ctx["total_turns"] <= threshold * 2:
            return

        from app.domain.models import Conversation
        old_q = (
            select(Conversation.role, Conversation.content)
            .where(Conversation.org_id == org_id, Conversation.user_id == user_id)
        )
        if contract_id:
            old_q = old_q.where(Conversation.contract_id == contract_id)
        old_q = old_q.order_by(Conversation.created_at.asc()).limit(
            ctx["total_turns"] - threshold
        )
        old_rows = (await self.db.execute(old_q)).fetchall()
        if not old_rows:
            return

        conv_text = "\n".join(
            f"{r.role.upper()}: {r.content[:300]}" for r in old_rows
        )

        try:
            from app.infrastructure.llm.router import AgentRole, LLMMessage
            resp = await self.llm.complete(
                messages=[LLMMessage(role="user", content=
                    f"Summarize this conversation in under 150 words. "
                    f"Focus on key questions, facts, and decisions:\n\n{conv_text}\n\nSUMMARY:"
                )],
                role=AgentRole.EXTRACTOR,
                org_id=org_id,
            )
            self.db.add(ConversationSummary(
                org_id=org_id, user_id=user_id,
                contract_id=contract_id,
                summary=resp.content,
                turns_covered=len(old_rows),
                tokens_saved=len(conv_text) // 4,
            ))
            await self.db.commit()
            logger.info("history_summarized", turns=len(old_rows), org_id=str(org_id))
        except Exception as e:
            logger.warning("summarization_failed", error=str(e))

    # ── TIER 2: User query memory ──────────────────────

    TOPIC_KEYWORDS = {
        "liability":       ["liability", "liable", "damages", "cap"],
        "payment":         ["payment", "invoice", "price", "cost", "fee"],
        "termination":     ["terminat", "cancel", "end", "exit"],
        "confidentiality": ["confidential", "nda", "secret"],
        "ip_ownership":    ["ip ", "intellectual property", "copyright", "patent"],
        "governing_law":   ["governing law", "jurisdiction"],
        "sla":             ["sla", "uptime", "service level"],
        "auto_renewal":    ["auto renew", "renewal"],
        "indemnification": ["indemnif"],
        "dispute":         ["dispute", "arbitration"],
    }

    def _extract_topic(self, query: str) -> str | None:
        q = query.lower()
        for topic, kws in self.TOPIC_KEYWORDS.items():
            if any(kw in q for kw in kws):
                return topic
        return None

    async def track_query(self, org_id: UUID, user_id: UUID, query: str) -> None:
        """Track user query topic for personalization."""
        topic = self._extract_topic(query)
        if not topic:
            return
        try:
            result = await self.db.execute(
                select(UserQueryMemory).where(
                    UserQueryMemory.org_id == org_id,
                    UserQueryMemory.user_id == user_id,
                    UserQueryMemory.topic == topic,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.query_count += 1
                existing.last_query   = query[:500]
                existing.last_seen_at = datetime.now(timezone.utc)
            else:
                self.db.add(UserQueryMemory(
                    org_id=org_id, user_id=user_id,
                    topic=topic, last_query=query[:500],
                ))
            await self.db.commit()
        except Exception as e:
            logger.warning("query_tracking_failed", error=str(e))
            await self.db.rollback()

    async def get_user_interests(
        self, org_id: UUID, user_id: UUID, top_n: int = 3
    ) -> list[dict]:
        """Get user's top query topics."""
        result = await self.db.execute(
            select(UserQueryMemory)
            .where(UserQueryMemory.org_id == org_id, UserQueryMemory.user_id == user_id)
            .order_by(UserQueryMemory.query_count.desc())
            .limit(top_n)
        )
        return [{"topic": r.topic, "count": r.query_count}
                for r in result.scalars().all()]

    # ── TIER 3: Org insights ───────────────────────────

    async def generate_org_insights(self, org_id: UUID) -> list[dict]:
        """Generate cross-contract insights — works with any risk level."""
        from app.domain.models import Contract, Clause

        insights = []

        # Get total contracts
        result = await self.db.execute(
            select(func.count(Contract.id)).where(
                Contract.org_id == org_id, Contract.status == "analyzed"
            )
        )
        total = result.scalar() or 0

        if total == 0:
            return []

        # Pattern 1: Portfolio overview
        insights.append({
            "type": "portfolio",
            "title": f"Portfolio: {total} contracts analyzed",
            "desc": f"Your organisation has {total} analyzed contracts. All currently rated low risk.",
            "severity": "info",
        })

        # Pattern 2: Most common clause types
        result2 = await self.db.execute(
            select(Clause.clause_type, func.count(Clause.id).label("cnt"))
            .join(Contract, Clause.contract_id == Contract.id)
            .where(Contract.org_id == org_id, Contract.status == "analyzed")
            .group_by(Clause.clause_type)
            .order_by(func.count(Clause.id).desc())
            .limit(5)
        )
        top_clauses = result2.fetchall()
        if top_clauses:
            clause_summary = ", ".join(
                f"{r.clause_type.replace('_',' ')} ({r.cnt})" for r in top_clauses
            )
            insights.append({
                "type": "clause_pattern",
                "title": f"Most frequent clause types across {total} contracts",
                "desc": f"Top clauses: {clause_summary}. Consider standardising templates.",
                "severity": "info",
            })

        # Pattern 3: Missing critical clauses
        result3 = await self.db.execute(
            select(Clause.clause_type, func.count(func.distinct(Clause.contract_id)).label("cnt"))
            .join(Contract, Clause.contract_id == Contract.id)
            .where(Contract.org_id == org_id, Contract.status == "analyzed")
            .group_by(Clause.clause_type)
        )
        present = {r.clause_type: r.cnt for r in result3.fetchall()}

        critical = ["liability", "termination", "confidentiality", "governing_law"]
        missing = []
        for ct in critical:
            count = present.get(ct, 0)
            if count < total:
                missing.append(f"{ct.replace('_',' ')} (missing in {total - count}/{total})")

        if missing:
            insights.append({
                "type": "clause_gap",
                "title": f"Missing critical clauses in some contracts",
                "desc": f"Gaps found: {', '.join(missing)}. Review contracts and add missing clauses.",
                "severity": "warning" if len(missing) > 2 else "info",
            })

        # Pattern 4: Contract value summary
        result4 = await self.db.execute(
            select(func.sum(Contract.contract_value), func.count(Contract.id))
            .where(
                Contract.org_id == org_id,
                Contract.status == "analyzed",
                Contract.contract_value.isnot(None),
            )
        )
        row = result4.fetchone()
        if row and row[0]:
            total_value = row[0]
            value_contracts = row[1]
            insights.append({
                "type": "portfolio",
                "title": f"Total contract value: {total_value/1000000:.1f}M across {value_contracts} contracts",
                "desc": f"Portfolio value tracked. Highest exposure contracts should be reviewed first.",
                "severity": "info",
            })

        # Pattern 5: High-risk if any
        result5 = await self.db.execute(
            select(func.count(Contract.id)).where(
                Contract.org_id == org_id,
                Contract.status == "analyzed",
                Contract.risk_level == "high",
            )
        )
        high = result5.scalar() or 0
        if high > 0:
            insights.append({
                "type": "risk_pattern",
                "title": f"{high} high-risk contracts need immediate review",
                "desc": f"{high} of {total} contracts are high risk. Assign to legal team immediately.",
                "severity": "critical",
            })

        # Save new insights (skip duplicates)
        saved = 0
        for i in insights:
            ex = await self.db.execute(
                select(OrgInsight).where(
                    OrgInsight.org_id == org_id,
                    OrgInsight.title == i["title"],
                    OrgInsight.is_active == True,
                )
            )
            if not ex.scalar_one_or_none():
                self.db.add(OrgInsight(
                    org_id=org_id, insight_type=i["type"],
                    title=i["title"], description=i["desc"], severity=i["severity"],
                ))
                saved += 1
        try:
            await self.db.commit()
            logger.info("org_insights_saved", org_id=str(org_id), saved=saved, total=len(insights))
        except Exception as e:
            logger.warning("insights_save_failed", error=str(e))
            await self.db.rollback()

        return insights

    async def get_org_insights(self, org_id: UUID) -> list[dict]:
        result = await self.db.execute(
            select(OrgInsight)
            .where(OrgInsight.org_id == org_id, OrgInsight.is_active == True)
            .order_by(OrgInsight.generated_at.desc())
            .limit(10)
        )
        return [
            {"id": str(i.id), "type": i.insight_type, "title": i.title,
             "desc": i.description, "severity": i.severity,
             "date": i.generated_at.isoformat() if i.generated_at else None}
            for i in result.scalars().all()
        ]

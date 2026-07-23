"""
Claustor AI — Contract Processing Pipeline
Orchestrates all AI processing steps for a contract.
Steps: Parse → Extract Clauses → Score Risk → Extract Obligations → Index

This runs in Celery worker (production) or inline (development).
"""

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.domain.models import Contract, Clause, Obligation
from app.infrastructure.llm.base import AgentRole, LLMMessage
from app.infrastructure.llm.router import get_llm_router
from app.infrastructure.parsers.document_parser import get_document_parser
from app.infrastructure.vector_store.pinecone_store import get_vector_store
from app.infrastructure.storage.gcs import get_storage_client

logger = structlog.get_logger(__name__)


class ContractPipeline:
    """
    Full contract processing pipeline.

    Step 1: Download from GCS + parse document
    Step 2: Extract clauses using LLM (batch)
    Step 3: Score risks using LLM (batch)
    Step 4: Extract obligations using LLM
    Step 5: Index chunks in Pinecone
    Step 6: Update DB with results
    """

    def __init__(self):
        self.llm = get_llm_router()
        self.parser = get_document_parser()
        self.vector_store = get_vector_store()

    async def process(
        self,
        contract_id: UUID,
        org_id: UUID,
        file_hash: str,
        db: AsyncSession,
    ) -> None:
        """Run full pipeline. Updates contract status at each step."""

        try:
            # ── Step 1: Download + Parse ──────────────────
            await self._update_status(db, contract_id, "parsing")
            logger.info("pipeline_step", step="parsing", contract_id=str(contract_id))

            file_bytes = await self._download_file(org_id, contract_id, file_hash)
            parsed = await self.parser.parse(file_bytes, "contract.pdf")

            # ── Step 2: Extract Clauses ───────────────────
            await self._update_status(db, contract_id, "extracting")
            logger.info("pipeline_step", step="extracting", contract_id=str(contract_id))

            clauses_data = await self._extract_clauses(parsed.full_text, parsed.tables)

            # ── Step 3: Score Risks ───────────────────────
            await self._update_status(db, contract_id, "scoring")
            logger.info("pipeline_step", step="scoring", contract_id=str(contract_id))

            scored_clauses = await self._score_risks(clauses_data)

            # ── Step 4: Extract Contract Metadata ─────────
            contract_meta = await self._extract_contract_metadata(parsed.full_text)

            # ── Step 5: Extract Obligations ───────────────
            obligations_data = await self._extract_obligations(parsed.full_text)

            # ── Step 6: Index in Pinecone ─────────────────
            await self._update_status(db, contract_id, "indexing")
            logger.info("pipeline_step", step="indexing", contract_id=str(contract_id))

            await self.vector_store.upsert_contract(
                org_id=org_id,
                contract_id=contract_id,
                chunks=parsed.chunks,
            )

            # ── Step 7: Save Results to DB ────────────────
            await self._save_results(
                db=db,
                contract_id=contract_id,
                org_id=org_id,
                scored_clauses=scored_clauses,
                obligations_data=obligations_data,
                contract_meta=contract_meta,
                parsed=parsed,
            )

            await self._update_status(db, contract_id, "analyzed")
            logger.info(
                "pipeline_complete",
                contract_id=str(contract_id),
                clauses=len(scored_clauses),
                obligations=len(obligations_data),
            )

        except Exception as e:
            logger.error(
                "pipeline_failed",
                contract_id=str(contract_id),
                error=str(e),
                exc_info=True,
            )
            await self._update_status(db, contract_id, "failed", error=str(e))
            raise

    async def _download_file(
        self,
        org_id: UUID,
        contract_id: UUID,
        file_hash: str,
    ) -> bytes:
        """Download contract from GCS."""
        try:
            storage = get_storage_client()
            return await storage.download_contract(org_id, contract_id)
        except Exception as e:
            logger.warning("gcs_download_failed", error=str(e))
            raise FileNotFoundError(f"Could not download contract file: {e}")

    async def _extract_clauses(
        self,
        full_text: str,
        tables: list[dict],
    ) -> list[dict]:
        """
        Extract all clauses from contract text using LLM.
        Uses batching to minimize API calls.
        """
        # Truncate to fit context window
        text_sample = full_text[:8000]

        table_summary = ""
        if tables:
            table_summary = f"\n\nTABLES FOUND ({len(tables)}):\n"
            for t in tables[:3]:  # first 3 tables
                table_summary += t.get("text", "")[:500] + "\n"

        prompt = f"""Analyze this contract and extract all important clauses.

CONTRACT TEXT:
{text_sample}
{table_summary}

Extract clauses and return as JSON array. Each clause must have:
- clause_type: one of [liability, indemnification, termination, payment, confidentiality, ip_ownership, governing_law, dispute_resolution, auto_renewal, warranty, force_majeure, non_compete, data_protection, change_of_control, audit_rights, assignment, limitation_of_liability, representations, other]
- title: short descriptive title
- summary: 1-2 sentence summary of what the clause says
- raw_text: the actual clause text (max 500 chars)
- section_reference: section number if visible (e.g. "Section 8.2")

Return ONLY valid JSON array, no other text."""

        response = await self.llm.complete(
            messages=[
                LLMMessage(role="system", content="You are a legal contract analyst. Return only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            role=AgentRole.EXTRACTOR,
            json_mode=True,
        )

        import json
        try:
            content = response.content.strip()
            # Handle if response is wrapped in object
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                # Try common keys
                for key in ["clauses", "data", "results", "items"]:
                    if key in parsed:
                        parsed = parsed[key]
                        break
            if isinstance(parsed, list):
                return parsed
            return []
        except json.JSONDecodeError as e:
            logger.warning("clause_extraction_json_error", error=str(e))
            return []

    async def _score_risks(self, clauses: list[dict]) -> list[dict]:
        """
        Score risk for all clauses in ONE LLM call (batch).
        Much cheaper than calling LLM per clause.
        """
        if not clauses:
            return []

        # Prepare compact clause list for batch scoring
        clause_list = "\n".join([
            f"{i+1}. [{c.get('clause_type', 'other')}] {c.get('summary', '')[:200]}"
            for i, c in enumerate(clauses)
        ])

        prompt = f"""Score the risk level for each of these contract clauses.

CLAUSES TO SCORE:
{clause_list}

For each clause, return a JSON array with objects containing:
- index: clause number (1-based)
- risk_score: 0-100 (0=no risk, 100=critical risk)
- risk_level: "low" (0-33), "medium" (34-66), or "high" (67-100)
- risk_reason: one sentence explaining why this is risky (or why it's safe)

Consider:
- Unusual liability caps (too low = high risk)
- Broad indemnification without carve-outs = high risk
- Auto-renewal with long notice periods = medium-high risk
- Missing dispute resolution = medium risk
- Standard governing law clause = low risk

Return ONLY valid JSON array."""

        response = await self.llm.complete(
            messages=[
                LLMMessage(role="system", content="You are a legal risk analyst. Return only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            role=AgentRole.REASONER,
            json_mode=True,
        )

        import json
        try:
            scores = json.loads(response.content.strip())
            if isinstance(scores, dict):
                for key in ["scores", "data", "results"]:
                    if key in scores:
                        scores = scores[key]
                        break

            # Merge scores back into clauses
            score_map = {s["index"]: s for s in scores if isinstance(s, dict)}
            for i, clause in enumerate(clauses):
                score = score_map.get(i + 1, {})
                clause["risk_score"] = score.get("risk_score", 30.0)
                clause["risk_level"] = score.get("risk_level", "low")
                clause["risk_reason"] = score.get("risk_reason", "")

            return clauses

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("risk_scoring_error", error=str(e))
            # Default all to low risk on error
            for clause in clauses:
                clause.setdefault("risk_score", 30.0)
                clause.setdefault("risk_level", "low")
                clause.setdefault("risk_reason", "Could not score automatically")
            return clauses

    async def _extract_contract_metadata(self, full_text: str) -> dict:
        """Extract key contract metadata (parties, dates, value etc)."""
        prompt = f"""Extract key metadata from this contract.

CONTRACT TEXT (first 3000 chars):
{full_text[:3000]}

Return JSON with these fields (use null if not found):
- contract_type: type of contract (MSA, NDA, SLA, Employment, Vendor, License, Lease, Loan, Other)
- counterparty: name of the other party (not our company)
- effective_date: contract start date (YYYY-MM-DD format or null)
- expiry_date: contract end date (YYYY-MM-DD format or null)
- auto_renewal: true/false/null
- renewal_notice_days: number of days notice required for termination (integer or null)
- governing_law: jurisdiction/state/country
- contract_value: numeric value if mentioned (number or null)
- contract_currency: currency code (INR, USD, EUR etc or null)
- language: primary language (en, hi, etc)
- summary: 2-3 sentence executive summary of what this contract is about

Return ONLY valid JSON."""

        response = await self.llm.complete(
            messages=[
                LLMMessage(role="system", content="You are a contract analyst. Return only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            role=AgentRole.EXTRACTOR,
            json_mode=True,
        )

        import json
        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            return {}

    async def _extract_obligations(self, full_text: str) -> list[dict]:
        """Extract obligations with due dates."""
        prompt = f"""Extract all obligations and important dates from this contract.

CONTRACT TEXT (first 4000 chars):
{full_text[:4000]}

Return JSON array of obligations. Each must have:
- title: short obligation title
- description: what needs to be done
- obligation_type: one of [payment, reporting, audit, renewal, certification, delivery, notice, compliance, other]
- party: who must perform this (us/counterparty/both)
- due_date: specific date if mentioned (YYYY-MM-DD or null)
- recurring: true if this repeats (monthly, quarterly, annually)
- amount: monetary amount if applicable (number or null)
- currency: currency code if applicable

Return ONLY valid JSON array. Focus on actionable obligations with dates or deadlines."""

        response = await self.llm.complete(
            messages=[
                LLMMessage(role="system", content="You are a contract analyst. Return only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            role=AgentRole.EXTRACTOR,
            json_mode=True,
        )

        import json
        try:
            parsed = json.loads(response.content.strip())
            if isinstance(parsed, dict):
                for key in ["obligations", "data", "results"]:
                    if key in parsed:
                        parsed = parsed[key]
                        break
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    async def _save_results(
        self,
        db: AsyncSession,
        contract_id: UUID,
        org_id: UUID,
        scored_clauses: list[dict],
        obligations_data: list[dict],
        contract_meta: dict,
        parsed,
    ) -> None:
        """Save all extracted data to database."""
        from datetime import date as date_type

        # Calculate overall risk score
        risk_scores = [c.get("risk_score", 0) for c in scored_clauses]
        overall_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        high_risk_count = sum(1 for s in risk_scores if s >= 67)
        risk_level = "high" if overall_risk >= 67 else "medium" if overall_risk >= 34 else "low"

        # Parse dates safely
        def safe_date(val):
            if not val:
                return None
            try:
                from datetime import datetime
                return datetime.strptime(val, "%Y-%m-%d").date()
            except Exception:
                return None

        # Update contract record
        await db.execute(
            __import__("sqlalchemy").update(Contract)
            .where(Contract.id == contract_id)
            .values(
                title=contract_meta.get("title") or (
                    await db.execute(
                        __import__("sqlalchemy").select(Contract.title).where(Contract.id == contract_id)
                    )
                ).scalar() or "Contract",
                contract_type=contract_meta.get("contract_type"),
                counterparty=contract_meta.get("counterparty"),
                governing_law=contract_meta.get("governing_law"),
                language=contract_meta.get("language", "en"),
                effective_date=safe_date(contract_meta.get("effective_date")),
                expiry_date=safe_date(contract_meta.get("expiry_date")),
                auto_renewal=contract_meta.get("auto_renewal"),
                renewal_notice_days=contract_meta.get("renewal_notice_days"),
                contract_value=contract_meta.get("contract_value"),
                contract_currency=contract_meta.get("contract_currency"),
                summary=contract_meta.get("summary"),
                risk_score=round(overall_risk, 2),
                risk_level=risk_level,
                clause_count=len(scored_clauses),
                status="analyzed",
            )
        )

        # Save clauses
        for clause_data in scored_clauses:
            clause = Clause(
                contract_id=contract_id,
                org_id=org_id,
                clause_type=clause_data.get("clause_type", "other"),
                title=clause_data.get("title", "")[:500],
                summary=clause_data.get("summary"),
                raw_text=clause_data.get("raw_text", "")[:5000],
                section_reference=clause_data.get("section_reference"),
                risk_score=float(clause_data.get("risk_score", 30)),
                risk_level=clause_data.get("risk_level", "low"),
                risk_reason=clause_data.get("risk_reason"),
                confidence=0.85,
            )
            db.add(clause)

        # Save obligations
        for ob_data in obligations_data:
            obligation = Obligation(
                contract_id=contract_id,
                org_id=org_id,
                title=ob_data.get("title", "Obligation")[:500],
                description=ob_data.get("description"),
                obligation_type=ob_data.get("obligation_type", "other"),
                party=ob_data.get("party"),
                due_date=safe_date(ob_data.get("due_date")),
                recurring=ob_data.get("recurring", False),
                amount=ob_data.get("amount"),
                currency=ob_data.get("currency"),
                status="pending",
            )
            db.add(obligation)

        await db.commit()

        logger.info(
            "results_saved",
            contract_id=str(contract_id),
            clauses=len(scored_clauses),
            obligations=len(obligations_data),
            risk_score=round(overall_risk, 2),
            risk_level=risk_level,
        )

    async def _update_status(
        self,
        db: AsyncSession,
        contract_id: UUID,
        status: str,
        error: str | None = None,
    ) -> None:
        """Update contract processing status."""
        import sqlalchemy
        from datetime import datetime, timezone

        values = {"status": status}
        if error:
            values["processing_error"] = error[:1000]
        if status == "analyzed":
            values["processed_at"] = datetime.now(timezone.utc)

        await db.execute(
            sqlalchemy.update(Contract)
            .where(Contract.id == contract_id)
            .values(**values)
        )
        await db.commit()

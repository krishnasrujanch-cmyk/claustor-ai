"""
Claustor AI — Contract Processing Pipeline
Orchestrates all AI processing steps for a contract.
Steps: Parse → Extract Clauses → Score Risk → Extract Obligations → Index

This runs in Celery worker (production) or inline (development).
"""

import asyncio
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
            await asyncio.sleep(0.3)  # Let frontend poll catch this step

            file_bytes = await self._download_file(org_id, contract_id, file_hash, db)

            # Use DocumentProcessor (models pre-loaded at startup)
            from app.infrastructure.document.processor import DocumentProcessor
            from app.domain.models import Organisation
            from sqlalchemy import select as _sel_org

            # Get org plan for feature gating
            _org_result = await db.execute(
                _sel_org(Organisation.plan).where(Organisation.id == org_id)
            )
            _org_plan = _org_result.scalar() or "free"

            # Get original filename from DB
            from app.domain.models import Contract as _Contract
            _fname_result = await db.execute(
                _sel_org(_Contract.original_filename).where(_Contract.id == contract_id)
            )
            _filename = _fname_result.scalar() or "contract.pdf"

            # Parse with plan-gated features
            _doc_processor = DocumentProcessor.get()
            _parsed_doc = _doc_processor.parse(
                file_bytes=file_bytes,
                filename=_filename,
                plan=_org_plan,
            )

            # Template matching (Professional+)
            _template_match = {}
            if _org_plan in ("professional", "enterprise"):
                _template_match = _doc_processor.match_template(
                    _parsed_doc["full_text"], str(org_id)
                )
                logger.info("template_matched",
                           template=_template_match.get("template"),
                           confidence=_template_match.get("confidence"))

            # Signature detection (All plans)
            _sig_info = _doc_processor.detect_signatures(file_bytes)

            # Metadata extraction (All plans)
            _meta = _doc_processor.extract_metadata(file_bytes, _filename)

            # Build parsed object compatible with existing pipeline
            class _ParsedDoc:
                def __init__(self, doc_result, meta, sig_info, template):
                    self.full_text    = doc_result.get("full_text", "")
                    self.chunks       = self._make_chunks(self.full_text)
                    self.tables       = doc_result.get("tables", [])
                    self.page_count   = meta.get("page_count", 0)
                    self.metadata     = meta
                    self.has_signatures = sig_info.get("has_signatures", False)
                    self.pii_masked   = doc_result.get("pii_masked", False)
                    self.is_scanned   = doc_result.get("is_scanned", False)
                    self.template     = template

                def _make_chunks(self, text, chunk_size=1000, overlap=100):
                    if not text:
                        return []
                    chunks = []
                    words  = text.split()
                    step   = chunk_size - overlap
                    for i in range(0, len(words), step):
                        chunk_words = words[i:i+chunk_size]
                        chunks.append({"text": " ".join(chunk_words),
                                       "chunk_index": len(chunks)})
                    return chunks

            parsed = _ParsedDoc(_parsed_doc, _meta, _sig_info, _template_match)

            # ── Vision analysis for embedded images (Pro+) ──────
            if _org_plan in ("professional", "enterprise"):
                _raw_images = _parsed_doc.get("_raw_images", [])
                if _raw_images:
                    try:
                        vision_text = await _doc_processor.analyze_images_with_vision(
                            _raw_images, _org_plan
                        )
                        if vision_text:
                            parsed.full_text += f"\n\n=== IMAGE ANALYSIS ===\n{vision_text}"
                            logger.info("vision_analysis_complete",
                                       images=len(_raw_images),
                                       chars=len(vision_text))
                    except Exception as _ve:
                        logger.warning("vision_analysis_skipped", error=str(_ve))

            # Log parsing results
            logger.info("document_parsed",
                       contract_id=str(contract_id),
                       plan=_org_plan,
                       pages=parsed.page_count,
                       tables=len(parsed.tables),
                       is_scanned=parsed.is_scanned,
                       pii_masked=parsed.pii_masked,
                       has_signatures=parsed.has_signatures,
                       text_chars=len(parsed.full_text))

            # Save metadata to DB
            try:
                from app.domain.models import DocumentMetadata
                from sqlalchemy import update as _upd
                await db.execute(
                    _upd(_Contract)
                    .where(_Contract.id == contract_id)
                    .values(
                        has_signatures=parsed.has_signatures,
                    )
                )
                await db.commit()
            except Exception as _me:
                logger.warning("metadata_save_failed", error=str(_me))

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

            # Enrich chunks with contract metadata for better AI responses
            contract_title   = contract_meta.get("title", "") or ""
            counterparty     = contract_meta.get("counterparty", "") or ""
            contract_value   = str(contract_meta.get("contract_value", "") or "")
            enriched_chunks  = [
                {
                    **chunk,
                    "contract_title": contract_title,
                    "counterparty":   counterparty,
                    "contract_value": contract_value,
                }
                for chunk in parsed.chunks
            ]

            # Get contract family info for versioning
            from app.domain.models import Contract as _CM
            from sqlalchemy import select as _sel_cm
            _cv_result = await db.execute(
                _sel_cm(_CM.contract_family_id, _CM.version_number, _CM.parent_contract_id)
                .where(_CM.id == contract_id)
            )
            _cv_row = _cv_result.fetchone()
            _family_id = _cv_row.contract_family_id if _cv_row else None
            _version_num = _cv_row.version_number if _cv_row else 1

            # If this is a new version, delete old vectors first
            if _family_id and _version_num > 1:
                await self.vector_store.delete_contract_family(org_id, _family_id)
                logger.info("old_version_vectors_deleted",
                           family_id=str(_family_id), new_version=_version_num)

            await self.vector_store.upsert_contract(
                org_id=org_id,
                contract_id=contract_id,
                chunks=enriched_chunks,
                family_id=_family_id or contract_id,
                version_number=_version_num or 1,
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

            # Trigger webhook event
            try:
                from app.api.v1.endpoints.webhooks import trigger_webhook_event
                await trigger_webhook_event(
                    org_id=org_id,
                    event="contract.analyzed",
                    data={
                        "contract_id": str(contract_id),
                        "clause_count": len(scored_clauses),
                        "obligation_count": len(obligations_data),
                        "risk_level": "low",
                    },
                    db=db,
                )
            except Exception as we:
                logger.warning("webhook_trigger_failed", error=str(we))

        except Exception as e:
            logger.error(
                "pipeline_failed",
                contract_id=str(contract_id),
                error=str(e),
                exc_info=True,
            )
            await self._update_status(db, contract_id, "failed", error=str(e))
            try:
                from app.api.v1.endpoints.webhooks import trigger_webhook_event
                await trigger_webhook_event(
                    org_id=org_id,
                    event="contract.failed",
                    data={"contract_id": str(contract_id), "error": str(e)[:200]},
                    db=db,
                )
            except Exception:
                pass
            raise

    async def _download_file(
        self,
        org_id: UUID,
        contract_id: UUID,
        file_hash: str,
        db: AsyncSession,
    ) -> bytes:
        """
        Download contract file.
        Strategy:
          1. Look up file_path from DB contract record
          2. Try storage client (GCS or local) with that path
          3. Fallback: scan /tmp/claustor-uploads for the file
        """
        from sqlalchemy import select, text
        from pathlib import Path

        # Strategy 1: Look up stored file_path from DB
        try:
            result = await db.execute(
                text("SELECT file_path FROM contracts WHERE id = :id"),
                {"id": str(contract_id)}
            )
            row = result.fetchone()
            stored_path = row[0] if row else None
        except Exception as e:
            logger.warning("db_lookup_failed", error=str(e))
            stored_path = None

        # Strategy 2: Download using stored path
        if stored_path:
            try:
                # Handle relative "local/org_id/contract_id/filename" paths
                if stored_path.startswith("local/"):
                    abs_path = Path("/tmp/claustor-uploads") / stored_path[len("local/"):]
                    if abs_path.exists():
                        logger.info("file_found_local_path", path=str(abs_path))
                        return abs_path.read_bytes()
                else:
                    storage = get_storage_client()
                    return await storage.download_contract(stored_path)
            except Exception as e:
                logger.warning("storage_download_failed", path=stored_path, error=str(e))

        # Strategy 3: Scan local tmp directory
        local_base = Path.home() / "claustor-uploads"
        org_dir = local_base / str(org_id) / str(contract_id)
        if org_dir.exists():
            files = [f for f in org_dir.iterdir() if f.is_file()]
            if files:
                logger.info("file_found_local", path=str(files[0]))
                return files[0].read_bytes()

        # Strategy 4: Search all of tmp for contract_id
        if local_base.exists():
            for f in local_base.rglob("*"):
                if str(contract_id) in str(f) and f.is_file():
                    logger.info("file_found_by_scan", path=str(f))
                    return f.read_bytes()

        raise FileNotFoundError(
            f"Contract file not found for {contract_id}. "
            f"stored_path={stored_path}"
        )

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
        
        # Add contract value context for better risk calibration
        contract_value_context = ""
        if hasattr(self, "_current_contract_value") and self._current_contract_value:
            contract_value_context = f"\nCONTRACT VALUE: {self._current_contract_value} (higher value = higher stakes)"

        prompt = f"""Score each contract clause. Return ONLY a JSON array, nothing else.

CLAUSES:
{clause_list}

Return this exact format:
[
  {{"index": 1, "risk_score": 75, "risk_level": "high", "risk_reason": "reason"}},
  {{"index": 2, "risk_score": 45, "risk_level": "medium", "risk_reason": "reason"}}
]

RULES:
- risk_score: 0-100 integer
- risk_level: exactly "low" OR "medium" OR "high"
- HIGH (67-100): unlimited liability, no liability cap, unilateral termination, uncapped indemnification, exclusive license, IP auto-vesting to other party, 18+ month notice periods
- MEDIUM (34-66): liability cap below 3 months value, auto-renewal >60 days notice, broad confidentiality >5 years, short termination notice <30 days
- LOW (0-33): standard caps, mutual termination 60-90 days, clear IP ownership, standard payment terms
- DO NOT default everything to 30. Use the full 0-100 range.
- Return ONLY the JSON array. No markdown, no explanation."""

        response = await self.llm.complete(
            messages=[
                LLMMessage(role="system", content="You are a legal risk analyst. Return only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            role=AgentRole.REASONER,
            json_mode=True,
        )

        import json, re
        try:
            raw = response.content.strip()
            # Strip markdown code blocks if present
            raw = re.sub(r"```(?:json)?", "", raw).strip()
            # Extract JSON array
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                raw = match.group(0)
            scores = json.loads(raw)
            if isinstance(scores, dict):
                for key in ["scores", "data", "results", "clauses"]:
                    if key in scores:
                        scores = scores[key]
                        break

            # Merge scores back into clauses
            score_map = {s["index"]: s for s in scores if isinstance(s, dict)}
            logger.info("risk_scores_parsed",
                       count=len(score_map),
                       sample=[{"idx":k,"score":v.get("risk_score")} for k,v in list(score_map.items())[:3]])

            for i, clause in enumerate(clauses):
                score = score_map.get(i + 1, {})
                clause["risk_score"] = float(score.get("risk_score", 50.0))
                clause["risk_level"] = score.get("risk_level", "medium")
                clause["risk_reason"] = score.get("risk_reason", "")

            return clauses

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("risk_scoring_error", error=str(e), raw=response.content[:200])
            # Smart fallback scoring based on clause type
            HIGH_RISK_CLAUSES   = {"liability", "indemnification", "ip_ownership", "exclusivity"}
            MEDIUM_RISK_CLAUSES = {"termination", "auto_renewal", "payment", "confidentiality", "dispute_resolution"}
            for clause in clauses:
                ct = clause.get("clause_type", "other")
                if ct in HIGH_RISK_CLAUSES:
                    clause.setdefault("risk_score", 70.0)
                    clause.setdefault("risk_level", "high")
                elif ct in MEDIUM_RISK_CLAUSES:
                    clause.setdefault("risk_score", 50.0)
                    clause.setdefault("risk_level", "medium")
                else:
                    clause.setdefault("risk_score", 30.0)
                    clause.setdefault("risk_level", "low")
                clause.setdefault("risk_reason", "Auto-scored based on clause type")
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
        high_risk_count  = sum(1 for s in risk_scores if s >= 67)
        medium_risk_count = sum(1 for s in risk_scores if 34 <= s < 67)

        # If ANY clause is high risk → contract is at least medium
        # If 2+ clauses are high risk → contract is high
        if high_risk_count >= 2 or overall_risk >= 67:
            risk_level = "high"
        elif high_risk_count >= 1 or medium_risk_count >= 2 or overall_risk >= 34:
            risk_level = "medium"
        else:
            risk_level = "low"

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

"""
Claustor AI — Contract Processing Pipeline
Orchestrates all AI processing steps for a contract.
Steps: Parse → Extract Clauses → Score Risk → Extract Obligations → Index

This runs in Celery worker (production) or inline (development).
"""

import asyncio
from uuid import UUID

import structlog
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.db_utils import db_op_with_retry, is_connection_alive
from app.infrastructure.database.session_manager import PipelineSessionManager
from sqlalchemy import select, update

from app.domain.models import Contract, Clause, Obligation
from app.infrastructure.llm.base import AgentRole, LLMMessage
from app.infrastructure.llm.router import get_llm_router
from app.infrastructure.parsers.document_parser import get_document_parser
from app.infrastructure.vector_store.pinecone_store import get_vector_store
from app.agents.clause_engine import ClauseEngine, detect_missing_clauses
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
        session_factory=None,
        session_manager: "PipelineSessionManager | None" = None,
    ) -> None:
        """
        Process contract pipeline.
        Uses PipelineSessionManager for fresh sessions per DB operation.
        Each phase gets its own session — no long-lived sessions held.
        """
        from app.core.config import settings
        # Create session manager if not provided
        if session_manager is None:
            session_manager = PipelineSessionManager(settings.DATABASE_URL)
            await session_manager.initialize()
            _owns_manager = True
        else:
            _owns_manager = False
        self._session_manager = session_manager
        self._session_factory = session_factory
        """Run full pipeline. Updates contract status at each step."""

        try:
            # ── Step 1: Download + Parse ──────────────────
            try:
                await self._session_manager.update_status(contract_id, "parsing")
            except Exception as _se:
                logger.warning("status_update_skipped", step="parsing", error=str(_se)[:100])
            logger.info("pipeline_step", step="parsing", contract_id=str(contract_id))
            await asyncio.sleep(0.3)  # Let frontend poll catch this step

            file_bytes = await self._download_file(org_id, contract_id, file_hash, db)

            # Use DocumentProcessor (models pre-loaded at startup)
            from app.infrastructure.document.processor import DocumentProcessor
            from app.domain.models import Organisation
            from sqlalchemy import select as _sel_org

            # Get org plan + filename via session_manager (fresh session)
            from app.domain.models import Contract as _Contract
            async def _get_init_data(fresh_db):
                from sqlalchemy import select as _s2
                r1 = await fresh_db.execute(_s2(Organisation.plan).where(Organisation.id == org_id))
                r2 = await fresh_db.execute(_s2(_Contract.original_filename).where(_Contract.id == contract_id))
                return r1.scalar() or 'free', r2.scalar() or 'contract.pdf'
            _org_plan, _filename = await self._session_manager.execute(
                _get_init_data, operation_name='get_init_data'
            )
            logger.info("pipeline_init", contract_id=str(contract_id), plan=_org_plan, file=_filename)

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
            from app.infrastructure.document.processor_utils import (
                extract_document_enhanced, make_chunks,
                extract_tables_as_markdown, remove_headers_footers,
            )

            class _ParsedDoc:
                def __init__(self, doc_result, meta, sig_info, template, plan="free", file_bytes=b"", filename=""):
                    self.full_text      = doc_result.get("full_text", "")
                    self.tables         = doc_result.get("tables", [])
                    self.page_count     = meta.get("page_count", 0)
                    self.metadata       = meta
                    self.has_signatures = sig_info.get("has_signatures", False)
                    self.pii_masked     = doc_result.get("pii_masked", False)
                    self.is_scanned     = doc_result.get("is_scanned", False)
                    self.template       = template
                    self.form_fields    = doc_result.get("form_fields", {})
                    self.has_images     = doc_result.get("has_images", False)
                    # Use enhanced chunker with table awareness
                    self.chunks         = make_chunks(
                        self.full_text,
                        tables=self.tables,
                        chunk_size=1000,
                        overlap=150,
                    )

            # Use enhanced extraction
            _enhanced = extract_document_enhanced(file_bytes, _filename, plan=_org_plan)
            # Merge with existing doc_result (keep OCR, PII masking from existing processor)
            _merged = {**_parsed_doc, **_enhanced}
            # Prefer enhanced full_text if longer (better extraction)
            if len(_enhanced.get("full_text","")) > len(_parsed_doc.get("full_text","")):
                _merged["full_text"] = _enhanced["full_text"]
            else:
                _merged["full_text"] = _parsed_doc.get("full_text","")
            # Always use enhanced tables (markdown format)
            _merged["tables"] = _enhanced.get("tables", [])

            parsed = _ParsedDoc(_merged, _meta, _sig_info, _template_match,
                               plan=_org_plan, file_bytes=file_bytes, filename=_filename)

            # ── Vision analysis for embedded images (Pro+) ──────
            if _org_plan in ("professional", "enterprise"):
                _raw_images = _parsed_doc.get("_raw_images") or _merged.get("_raw_images", [])
                logger.info(f"vision_check: plan={_org_plan} images={len(_raw_images)}")
                print(f"VISION_CHECK: plan={_org_plan} images={len(_raw_images)} raw_images_keys={list(_parsed_doc.keys())[:5]}", flush=True)
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

            # Extract Indian tax identifiers and append to searchable text
            try:
                from app.infrastructure.document.processor import DocumentProcessor
                _ids = DocumentProcessor.extract_indian_identifiers(parsed.full_text)
                if _ids:
                    _id_lines = []
                    if _ids.get("gstins"):
                        _id_lines.append(f"GSTIN numbers in this contract: {', '.join(_ids['gstins'])}")
                    if _ids.get("cins"):
                        _id_lines.append(f"CIN numbers: {', '.join(_ids['cins'])}")
                    if _ids.get("pans"):
                        _id_lines.append(f"PAN numbers: {', '.join(_ids['pans'])}")
                    if _id_lines:
                        parsed.full_text += "\n\n=== INDIAN TAX IDENTIFIERS ===\n" + "\n".join(_id_lines)
                        logger.info("identifiers_extracted", count=len(_id_lines))
            except Exception as _ie:
                logger.warning(f"identifier_extraction_failed: {_ie}")
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
                async def _save_meta(fresh_db):
                    await fresh_db.execute(
                        _upd(_Contract)
                        .where(_Contract.id == contract_id)
                        .values(has_signatures=parsed.has_signatures)
                    )
                await self._session_manager.execute(
                    _save_meta, operation_name="save_metadata"
                )
            except Exception as _me:
                logger.warning("metadata_save_failed", error=str(_me))

            # ── Step 2: Extract Clauses ───────────────────
            try:
                await self._session_manager.update_status(contract_id, "extracting")
            except Exception:
                logger.warning("status_update_skipped", step="extracting")
            logger.info("pipeline_step", step="extracting", contract_id=str(contract_id))

            # ── ClauseEngine — All 3 Phases ──────────────
            _clause_engine = ClauseEngine(self.llm)
            _engine_result = await _clause_engine.analyze(
                full_text=parsed.full_text,
                tables=parsed.tables if hasattr(parsed, "tables") else [],
                contract_type="general",
                industry=org_industry if "org_industry" in dir() else "general",
                contract_value=None,
            )
            scored_clauses   = _engine_result["clauses"]
            _missing_clauses = _engine_result["missing_clauses"]
            _detected_lang   = _engine_result["language"]
            logger.info("clause_engine_complete",
                       total=len(scored_clauses),
                       missing=len(_missing_clauses),
                       language=_detected_lang)
            clauses_data = scored_clauses
            logger.info("scored_clauses_sample", sample=scored_clauses[0] if scored_clauses else {})

            # ── Step 3: Score Risks ───────────────────────
            try:
                await self._session_manager.update_status(contract_id, "scoring")
            except Exception:
                logger.warning("status_update_skipped", step="scoring")
            logger.info("pipeline_step", step="scoring", contract_id=str(contract_id))

            # Risk scoring done by ClauseEngine above

            # ── Step 4: Extract Contract Metadata ─────────
            contract_meta = await self._extract_contract_metadata(parsed.full_text)

            # ── Step 5: Extract Obligations ───────────────
            obligations_data = await self._extract_obligations(parsed.full_text)

            # ── Step 6: Index in Pinecone ─────────────────
            try:
                await self._session_manager.update_status(contract_id, "indexing")
            except Exception:
                logger.warning("status_update_skipped", step="indexing")
            logger.info(f"pipeline_step: step=indexing contract_id={contract_id}")

            # ── Hierarchical chunking — parent/child with rich metadata ──
            # ── Step 6b: Extract Party Identifiers (Option B) ────
            _party_ids = []
            try:
                from app.infrastructure.identifiers.party_extractor import (
                    extract_party_identifiers, build_identifier_summary
                )
                _party_ids = await extract_party_identifiers(
                    parsed.full_text, plan=_org_plan
                )
                if _party_ids:
                    parsed.full_text += build_identifier_summary(_party_ids)
                    logger.info("party_identifiers_extracted", parties=len(_party_ids))
            except Exception as _pe:
                logger.warning(f"party_extraction_failed: {_pe}")
            # Auto-detect industry from contract text
            try:
                from app.agents.profiles.industry_detector import detect_industry, detect_contract_type_enhanced
                _detected_industry = detect_industry(full_text, org_industry if "org_industry" in dir() else "general")
                _enhanced_type = detect_contract_type_enhanced(full_text, contract_meta.get("contract_type", "Other"))
                contract_meta["industry"] = _detected_industry
                contract_meta["contract_type"] = _enhanced_type
                logger.info("industry_detected", industry=_detected_industry, contract_type=_enhanced_type)
            except Exception as _ide:
                logger.warning("industry_detection_failed", error=str(_ide)[:80])

            from app.infrastructure.document.hierarchical_chunker import build_hierarchical_chunks
            from app.infrastructure.vector_store.chunk_indexer import index_chunks

            _chunk_meta = {
                "counterparty":  contract_meta.get("counterparty"),
                "risk_level":    None,  # updated after scoring below
                "contract_type": contract_meta.get("contract_type"),
                "effective_date":contract_meta.get("effective_date"),
                "expiry_date":   contract_meta.get("expiry_date"),
            }

            _hier_chunks = build_hierarchical_chunks(
                full_text=parsed.full_text,
                tables=parsed.tables,
                contract_id=contract_id,
                org_id=org_id,
                contract_meta=_chunk_meta,
            )

            # Enrich child chunks with risk scores after clause scoring
            _risk_map = {c.get("clause_type","").lower(): float(c.get("risk_score",0))
                        for c in scored_clauses if isinstance(c, dict)}
            for _hc in _hier_chunks:
                if not _hc.is_parent and _hc.heading:
                    _h = (_hc.heading or "").lower()
                    for _ct, _rs in _risk_map.items():
                        if _ct in _h:
                            _hc.risk_score = _rs
                            break

            # index_chunks — pass session_manager for its own DB saves
            await index_chunks(
                chunks=_hier_chunks,
                contract_id=contract_id,
                org_id=org_id,
                db=None,
                vector_store=self.vector_store,
                session_manager=self._session_manager,
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
                party_ids=_party_ids,
            )

            await self._session_manager.update_status(contract_id, "analyzed")
            logger.info(
                "pipeline_complete",
                contract_id=str(contract_id),
                clauses=len(scored_clauses),
                obligations=len(obligations_data),
            )

            # Trigger webhook event — use fresh session
            try:
                from app.api.v1.endpoints.webhooks import trigger_webhook_event
                async def _webhook_success(fresh_db):
                    await trigger_webhook_event(
                        org_id=org_id,
                        event="contract.analyzed",
                        data={
                            "contract_id": str(contract_id),
                            "clause_count": len(scored_clauses),
                            "obligation_count": len(obligations_data),
                            "risk_level": "low",
                        },
                        db=fresh_db,
                    )
                await self._session_manager.execute(
                    _webhook_success, operation_name="webhook_analyzed"
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
            # Rollback any pending transaction before updating status
            try:
                await db.rollback()
            except Exception:
                pass
            await self._session_manager.update_status(contract_id, "failed", error=str(e))
            try:
                from app.api.v1.endpoints.webhooks import trigger_webhook_event
                async def _webhook_failed(fresh_db):
                    await trigger_webhook_event(
                        org_id=org_id,
                        event="contract.failed",
                        data={"contract_id": str(contract_id), "error": str(e)[:200]},
                        db=fresh_db,
                    )
                await self._session_manager.execute(
                    _webhook_failed, operation_name="webhook_failed"
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

        # Strategy 1: Look up stored file_path via session_manager
        try:
            async def _get_file_path(fresh_db):
                r = await fresh_db.execute(
                    text("SELECT file_path FROM contracts WHERE id = :id"),
                    {"id": str(contract_id)}
                )
                return r.fetchone()
            _fp_row = await self._session_manager.execute(
                _get_file_path, operation_name="get_file_path"
            )
            stored_path = _fp_row[0] if _fp_row else None
        except Exception as e:
            logger.warning("db_lookup_failed", error=str(e))
            stored_path = None


        # Strategy 1b: If DB lookup failed, scan GCS directly
        if stored_path is None:
            try:
                from google.cloud import storage as gcs_lib
                from google.auth import default as _gauth
                _creds, _proj = _gauth()
                _gclient = gcs_lib.Client(project=_proj or "claustor-ai-prod", credentials=_creds)
                _prefix = f"orgs/{org_id}/contracts/{contract_id}/"
                _blobs = list(_gclient.list_blobs("claustor-contracts-prod", prefix=_prefix))
                if _blobs:
                    _blob = _blobs[0]
                    import asyncio as _aio
                    _data = await _aio.get_event_loop().run_in_executor(None, _blob.download_as_bytes)
                    logger.info("file_downloaded_gcs_scan", path=_blob.name, size=len(_data))
                    return _data
                else:
                    logger.warning("gcs_scan_no_blobs", prefix=_prefix)
            except Exception as _e2:
                logger.warning("gcs_scan_failed", error=str(_e2))

        # Strategy 2: Download using stored path
        if stored_path:
            try:
                if stored_path.startswith("local/"):
                    abs_path = Path("/tmp/claustor-uploads") / stored_path[len("local/"):]
                    if abs_path.exists():
                        logger.info("file_found_local_path", path=str(abs_path))
                        return abs_path.read_bytes()
                elif stored_path.startswith("gs://"):
                    # Direct GCS download — bypass StorageClient
                    import asyncio
                    from google.cloud import storage as gcs_lib
                    from google.auth import default as _gauth_default2
                    _creds2, _proj2 = _gauth_default2()
                    client = gcs_lib.Client(project=_proj2 or "claustor-ai-prod", credentials=_creds2)
                    parts = stored_path.replace("gs://", "").split("/", 1)
                    blob = client.bucket(parts[0]).blob(parts[1])
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, blob.download_as_bytes
                    )
                    logger.info("file_downloaded_gcs", path=stored_path, size=len(data))
                    return data
                else:
                    storage = get_storage_client()
                    return await storage.download_contract(stored_path)
            except Exception as e:
                logger.warning("storage_download_failed", path=stored_path,
                               error=str(e), error_type=type(e).__name__)

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
        Processes full document in overlapping batches — generic for any contract type.
        """
        import json

        # Generic clause types — covers all contract categories universally
        CLAUSE_TYPES = (
            "payment, termination, liability, indemnification, confidentiality, "
            "governing_law, dispute_resolution, force_majeure, warranty, "
            "representations, notices, assignment, amendment, entire_agreement, "
            "ip_ownership, license, non_compete, data_protection, audit_rights, "
            "sla, acceptance_testing, change_order, auto_renewal, "
            "limitation_of_liability, insurance, change_of_control, "
            "payment_schedule, penalty, security_deposit, non_solicitation, "
            "benefits, severance, possession, construction_timeline, "
            "registration, maintenance, handover, other"
        )

        # Size-based batching with overlap — reliable for all contract types
        BATCH_SIZE = 8000    # ~2000 tokens — proven to work well
        OVERLAP = 500        # catch clauses split across boundaries
        MAX_BATCHES = 15     # cap: 15 * 8000 = 120K chars max coverage

        batches = []
        pos = 0
        while pos < len(full_text):
            end_pos = min(pos + BATCH_SIZE, len(full_text))
            batches.append(full_text[pos:end_pos])
            if end_pos == len(full_text):
                break
            pos = end_pos - OVERLAP

        # For very large docs, merge to stay within MAX_BATCHES
        if len(batches) > MAX_BATCHES:
            step = len(batches) // MAX_BATCHES + 1
            batches = [
                "\n\n".join(batches[i:i+step])
                for i in range(0, len(batches), step)
            ][:MAX_BATCHES]

        logger.info("clause_extraction_plan",
                    doc_chars=len(full_text),
                    batches=len(batches))

        # Table summary for context
        table_summary = ""
        if tables:
            table_summary = f"\n\nTABLES IN CONTRACT ({len(tables)}):\n"
            for t in tables[:5]:
                table_summary += t.get("text", "")[:300] + "\n"

        all_clauses = []
        seen_keys = set()

        for batch_idx, batch_text in enumerate(batches):
            prompt = f"""Extract ALL important clauses from this contract section.
This is section {batch_idx + 1} of {len(batches)} of the full contract.

CONTRACT TEXT:
{batch_text}
{table_summary if batch_idx == 0 else ""}

Return a JSON array of clauses found in this section. Each clause:
- clause_type: one of [{CLAUSE_TYPES}]
- title: short descriptive title
- summary: 1-2 sentence summary of what the clause says
- raw_text: actual clause text from the contract (max 500 chars)
- section_reference: section number if visible (e.g. "6", "11.2")

Rules:
- Extract ALL substantive clauses present, do not skip any
- Use "other" for domain-specific clauses not in the type list
- Do NOT duplicate clauses already extracted in earlier sections
Return ONLY valid JSON array, no other text."""

            try:
                response = await self.llm.complete(
                    messages=[
                        LLMMessage(role="system", content="You are a legal contract analyst. Extract all clauses accurately. Return only valid JSON array."),
                        LLMMessage(role="user", content=prompt),
                    ],
                    role=AgentRole.EXTRACTOR,
                    json_mode=True,
                )
                batch_clauses = json.loads(response.content.strip())
                if not isinstance(batch_clauses, list):
                    continue
                for clause in batch_clauses:
                    ct = str(clause.get("clause_type", "other"))
                    title = str(clause.get("title", ""))[:40]
                    key = f"{ct}:{title.lower()}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_clauses.append(clause)
            except Exception as e:
                logger.warning(f"clause_extraction_batch_{batch_idx}_failed: {e}")
                continue

        logger.info("clauses_extracted",
                    count=len(all_clauses),
                    batches=len(batches),
                    doc_chars=len(full_text))

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
        import re

        # Smart excerpt: first 4000 chars + any section with term/expiry keywords
        excerpts = [full_text[:4000]]
        term_keywords = ["term and terminat", "initial term", "expiry", "expiration",
                         "effective date", "commencement", "duration", "period of agreement",
                         "governing law", "jurisdiction", "contract value", "total value"]
        for kw in term_keywords:
            idx = full_text.lower().find(kw)
            if idx > 0:
                excerpt = full_text[max(0, idx-100):idx+500]
                if excerpt not in excerpts:
                    excerpts.append(excerpt)

        combined = "\n\n---\n\n".join(excerpts)[:12000]

        prompt = f"""Extract key metadata from this contract.
CONTRACT TEXT (key sections):
{combined}
Return JSON with these fields (use null if not found):
- title: official name/title of the contract (e.g. "Agreement for Sale", "Non-Disclosure Agreement", "Master Services Agreement")
- contract_type: type of contract (MSA, NDA, SLA, Employment, Vendor, License, Lease, Loan, Other)
- counterparty: name of the other party (not our company)
- effective_date: contract start date (YYYY-MM-DD format or null)
- expiry_date: contract end date (YYYY-MM-DD format or null). IMPORTANT: If not explicitly stated, calculate from effective_date + term duration. Examples: "10-year term" from 2026-06-01 = 2036-06-01, "3 years" from 2026-01-01 = 2029-01-01
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
        import json as _json
        try:
            result = _json.loads(response.content.strip())
            print(f"METADATA EXTRACTED: expiry={result.get('expiry_date')} effective={result.get('effective_date')}")
            return result
        except Exception:
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


    async def _save_results(self, db: AsyncSession, *args, **kwargs) -> None:
        """
        Save results using PipelineSessionManager.
        Fresh NullPool connection — guaranteed alive after 10+ min pipeline.
        """
        mgr = getattr(self, "_session_manager", None)
        if mgr:
            await mgr.execute(
                lambda fresh_db: self._save_results_inner(fresh_db, *args, **kwargs),
                operation_name="save_pipeline_results"
            )
        else:
            await self._save_results_inner(db, *args, **kwargs)

    async def _save_results_inner(
        self,
        db: AsyncSession,
        contract_id: UUID,
        org_id: UUID,
        scored_clauses: list[dict],
        obligations_data: list[dict],
        contract_meta: dict,
        parsed,
        party_ids: list = None,
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
                title=contract_meta.get("title") or "Contract",
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
                missing_clauses=_missing_clauses if "_missing_clauses" in dir() else [],
                detected_language=_detected_lang if "_detected_lang" in dir() else "en",
                party_identifiers=party_ids or [],
            )
        )

        # Delete existing clauses first (idempotent — safe for retries)
        await db.execute(
            __import__("sqlalchemy").delete(Clause).where(Clause.contract_id == contract_id)
        )
        await db.execute(
            __import__("sqlalchemy").delete(Obligation).where(Obligation.contract_id == contract_id)
        )

        # Build all clause objects
        all_clauses = []
        all_obligations = []
        for _ci, clause_data in enumerate(scored_clauses):
            clause = Clause(
                contract_id=contract_id,
                org_id=org_id,
                clause_type=clause_data.get("clause_type", "other"),
                title=clause_data.get("title", "")[:500],
                summary=clause_data.get("summary"),
                raw_text=clause_data.get("raw_text", "")[:10000],
                section_reference=str(clause_data.get("section_reference", "") or ""),
                risk_score=float(clause_data.get("risk_score", 30)),
                risk_level=clause_data.get("risk_level", "low"),
                risk_reason=clause_data.get("risk_reason"),
                confidence=0.85,
                # Phase 2: Playbook + industry
                playbook_match=clause_data.get("playbook_match"),
                deviation_from_std=clause_data.get("deviation"),
                adjusted_risk=clause_data.get("adjusted_risk"),
                industry_weight=clause_data.get("industry_weight", 1.0),
                # Phase 3: Relationships
                related_clauses=clause_data.get("related_clauses", []),
                cross_references=clause_data.get("cross_references", []),
            )
            all_clauses.append(clause)

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
            all_obligations.append(obligation)

        # Atomic bulk insert — all or nothing
        db.add_all(all_clauses)
        db.add_all(all_obligations)
        await db.flush()
        # commit handled by PipelineSessionManager.session() context manager

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
        # Fire high risk + analysis complete notification — read from DB
        if status == "analyzed":
            try:
                from app.services.notifications import send_notification, NotificationEvent, NotificationPayload
                from sqlalchemy import text as _nt2
                # Get contract + user data from DB
                _cr = (await db.execute(_nt2("""
                    SELECT c.title, c.risk_level, u.email, u.full_name, o.name
                    FROM contracts c
                    JOIN organisations o ON o.id = c.org_id
                    JOIN users u ON u.org_id = o.id
                    WHERE c.id = :cid AND u.role IN ('admin','super_admin')
                    LIMIT 1
                """), {"cid": str(contract_id)})).fetchone()
                if _cr:
                    _payload_base = dict(
                        recipient_email=_cr[2],
                        recipient_name=_cr[3] or _cr[2].split("@")[0].title(),
                        org_name=_cr[4] or "",
                        contract_id=str(contract_id),
                        contract_name=_cr[0] or "Contract",
                        action_url=f"{settings.FRONTEND_URL}/dashboard/contracts/{contract_id}",
                    )
                    # High risk notification
                    if _cr[1] == "high":
                        _hc = (await db.execute(_nt2("""
                            SELECT clause_type FROM clauses
                            WHERE contract_id = :cid AND risk_level = 'high'
                            LIMIT 5
                        """), {"cid": str(contract_id)})).fetchall()
                        await send_notification(NotificationPayload(
                            event=NotificationEvent.HIGH_RISK_DETECTED,
                            extra={
                                "high_risk_count": len(_hc),
                                "risk_clauses": [r[0] for r in _hc],
                            },
                            **_payload_base
                        ))
            except Exception as _ne2:
                logger.warning(f"notification_failed: {_ne2}")
        if status == "analyzed":
            try:
                from app.services.notifications import send_notification, NotificationEvent, NotificationPayload
                from sqlalchemy import text as _nt
                _user_row = await db.execute(_nt("""
                    SELECT u.email, u.full_name, o.name
                    FROM users u JOIN organisations o ON o.id = u.org_id
                    WHERE u.org_id = :org_id AND u.role IN ('admin','super_admin')
                    LIMIT 1
                """), {"org_id": str(org_id)})
                _ur = _user_row.fetchone()
                if _ur:
                    await send_notification(NotificationPayload(
                        event=NotificationEvent.AI_ANALYSIS_COMPLETE,
                        recipient_email=_ur[0],
                        recipient_name=_ur[1] or _ur[0].split("@")[0].title(),
                        org_name=_ur[2] or "",
                        contract_id=str(contract_id),
                        contract_name=contract_meta.get("title","Contract"),
                        action_url=f"{settings.FRONTEND_URL}/dashboard/contracts/{contract_id}",
                        extra={
                            "risk_level": contract_meta.get("risk_level","medium"),
                            "clause_count": len(scored_clauses),
                            "high_risk_count": sum(1 for c in scored_clauses if c.get("risk_level")=="high"),
                        }
                    ))
            except Exception as _ne:
                logger.warning(f"analysis_notification_failed: {_ne}")
        if status == "analyzed":
            values["processed_at"] = datetime.now(timezone.utc)

        await db.execute(
            sqlalchemy.update(Contract)
            .where(Contract.id == contract_id)
            .values(**values)
        )
        await db.commit()

"""
Claustor AI — Structured Synthesis Pipeline
=============================================
Multi-step extraction for broad analytical queries.
Replaces single-pass LLM synthesis that inverts parties and drops facts.

Pipeline:
  Step 1: Fact Extraction (per chunk)
  Step 2: Party Comparison (cross-clause)
  Step 3: Risk Assessment (ranked)
  Step 4: Grounding Validation (code, no LLM)
  Step 5: Final Synthesis (one LLM call)
"""
import json
import re
import structlog
from typing import Optional

from app.infrastructure.llm.router import LLMRouter, get_llm_router
from app.infrastructure.llm.base import LLMMessage, AgentRole

logger = structlog.get_logger(__name__)

# ── Step 1: Fact Extraction Prompt ────────────────────────

EXTRACT_PROMPT = """You are a contract clause extractor. Read this single chunk and extract ALL contractual facts as JSON.

CHUNK [{chunk_num}]:
{chunk_text}

Return a JSON array of objects. Each object represents ONE clause or provision:
{{
  "clause_ref": "clause number, section number, table name, schedule reference, or row identifier — use whatever reference appears in the text",
  "topic": "one of: payment, liability, indemnity, termination, renewal, service_level, ip, data_protection, confidentiality, insurance, force_majeure, acceptance, billing, compliance, other",
  "obligor": "the party who MUST do something — use the EXACT name from the text",
  "beneficiary": "the party who BENEFITS — use the EXACT name from the text",
  "provision": "what the clause requires or permits — one sentence using exact language from the text",
  "amounts": ["any monetary amounts, percentages, or time periods — exact figures only"],
  "cap": "capped_standard/capped_reduced/uncapped/not_applicable — use capped_reduced when a clause sets a LOWER cap than the general limit, use uncapped ONLY when text explicitly says unlimited or states the general cap does not apply",
  "direction": "mutual/one_sided/not_applicable"
}}

RULES:
- Extract EVERY provision, not just risks
- Use EXACT party names as they appear in the text — do not substitute or generalise
- Use EXACT numbers from the text — never approximate
- If a provision applies to BOTH parties equally, set direction to "mutual"
- If you cannot determine obligor/beneficiary, set both to "unclear"
- Return ONLY a valid JSON array. No markdown, no explanation, no preamble.

DOCUMENT METADATA — IGNORE THESE (they are NOT contractual content):
- Law firm names, solicitor names, or preparer attributions
- Page headers, footers, page numbers, watermarks
- Matter references, file numbers, document IDs
- Confidentiality markings or classification labels
- "Prepared by", "Drafted by", or similar attributions
These entities are NOT contracting parties and must NEVER appear as obligor or beneficiary.

SECTION CONTEXT — PRESERVE THIS:
- If the chunk mentions a specific section, schedule, exhibit, or statement of work,
  include it in clause_ref (e.g. "Section 3.2", "Appendix A, Table 1")
- Do NOT merge facts from different sections into a single extraction
- Each section/schedule/statement of work should produce separate fact entries
- Dates, milestones, and amounts belong to the specific section they appear in —
  do not combine across sections"""

# ── Step 2: Party Comparison Prompt ───────────────────────

COMPARE_PROMPT = """You are a contract analyst. Given these extracted clause facts, identify ASYMMETRIES — provisions where one party has rights or obligations the other does not.

EXTRACTED FACTS:
{facts_json}

For each topic area, compare what each party can do vs what they must do.
Return a JSON array of asymmetries:
{{
  "topic": "the contract topic",
  "party_a": "exact party name from the facts",
  "party_a_position": "what this party can do or is protected from",
  "party_b": "exact party name from the facts",
  "party_b_position": "what this party can do or must do",
  "asymmetry_type": "one of: favors_obligor, favors_beneficiary, mutual, unclear",
  "severity": "critical/high/medium/low",
  "clause_refs": ["relevant clause numbers from the facts"]
}}

Focus on:
- Rights that differ between the two parties
- Obligations that apply to only one party
- Caps or limits that apply differently
- Mechanisms that favour one party (retroactive billing, deemed acceptance, etc.)

IMPORTANT:
- Only compare the actual CONTRACTING PARTIES (the parties who signed the agreement)
- Ignore law firms, preparers, or other entities mentioned in document metadata
- If a party name appears only in footers, headers, or "prepared by" text, it is NOT a contracting party

Return ONLY a valid JSON array. No markdown, no explanation."""

# ── Step 3: Risk Assessment Prompt ────────────────────────

ASSESS_PROMPT = """You are a contract risk assessor. Given the extracted clause facts and identified party asymmetries, produce a comprehensive answer.

EXTRACTED FACTS:
{facts_json}

PARTY ASYMMETRIES:
{asymmetries_json}

USER QUESTION: {query}

Produce a comprehensive answer with these sections:

1. FINANCIAL OBLIGATIONS
   - List EVERY monetary amount found in the extracted facts
   - Include payment terms, due dates, interest rates, billing frequency
   - Include any minimum spend, true-up, or retroactive billing mechanisms
   - Use EXACT figures from the facts — never round or approximate
   - If multiple amounts exist, list each separately with its source

2. KEY RISKS (ranked by severity)
   For each risk:
   - State the clause reference from the extracted facts
   - State EXACTLY which party bears the risk and which party benefits
     using their names as they appear in the facts
   - Quote the provision language from the extracted facts
   - Explain the severity using the asymmetry analysis
   
   CRITICAL DIRECTION RULE:
   - An indemnity FROM party A TO party B means party A PAYS, party B is PROTECTED
   - A termination right held BY party A means party A CAN EXIT, party B CANNOT
   - An "uncapped" obligation ON party A is a RISK for party A, a PROTECTION for party B
   - NEVER invert these directions. Check the obligor and beneficiary fields.

3. SERVICE LEVELS & REMEDIES
   - Credit caps, sole remedy clauses
   - Any thresholds that trigger escalation or termination

Convert all internal references to simple numbered citations: [Chunk 1] becomes [1], [Chunk 2] becomes [2], etc.
Never expose internal field names, JSON keys, classification labels, or analysis methodology in the answer.
State conclusions directly — never narrate the analysis process.
Every claim must have a citation where available.
For table data without clause numbers, cite the table or schedule name instead.
Never repeat the same point.
Never contradict yourself — if two facts seem to conflict, present both and explain.

RISK SEVERITY — STATE ONLY WHAT THE TEXT SAYS:
- Describe what the clause ACTUALLY provides — do not amplify or inflate
- If a clause sets a specific scope (e.g. named entities, defined list),
  state that scope — do not describe it as "unlimited" or "expanding"
- If a clause contains a qualifying condition (e.g. "unless agreed otherwise"),
  include that qualifier in your description
- Never use "unlimited" unless the extracted fact explicitly states uncapped/unlimited
- Never describe a risk as "expanding" or "growing" unless the contract
  text itself describes an expansion mechanism
- When a provision references another section for details (a schedule,
  appendix, or definition), note that the referenced section should be
  consulted — do not assume its contents

CRITICAL — ABSENCE vs NOT RETRIEVED:
- You are working from EXTRACTED FACTS, not the complete contract.
- If a topic is missing from the extracted facts, it means it was NOT EXTRACTED — 
  it does NOT mean the contract lacks that provision.
- NEVER say "no [provision] exists" or "the contract does not contain [provision]."
- NEVER draw legal conclusions from the absence of extracted facts 
  (e.g., concluding that a provision does not exist because it was not extracted is WRONG).
- Instead say: "No [provision] was identified in the analysed sections. 
  The full contract should be reviewed for this topic."
- NEVER speculate about what a clause "typically" contains. If you do not have
  the extracted fact, state that it was not identified — do not guess."""


class StructuredSynthesizer:
    """
    Multi-step synthesis pipeline for broad analytical queries.
    Each step is a focused LLM call with structured output.
    """

    def __init__(self):
        self.llm: LLMRouter = get_llm_router()

    async def synthesize(
        self,
        query: str,
        chunks: list,
        citations: list,
        complexity: str = "complex",
    ) -> str:
        """
        Run the full structured pipeline:
        Extract → Compare → Assess → Ground → Answer
        """
        logger.info("structured_pipeline_start",
                     query=query[:50], chunks=len(chunks))

        # Limit extraction by complexity — balance speed vs completeness
        # simple: 15 chunks (~30s), medium: 20 (~40s), complex: all (~60s)
        _max_extract = {"simple": 8, "medium": 15, "complex": len(chunks)}
        _extract_count = min(len(chunks), _max_extract.get(complexity, len(chunks)))
        extract_chunks = chunks[:_extract_count]
        
        # Step 1: Extract facts from each chunk
        all_facts = await self._extract_facts(extract_chunks)
        if not all_facts:
            logger.warning("structured_no_facts_extracted")
            return ""

        # Remove facts with no useful content (but keep table rows)
        all_facts = [
            f for f in all_facts
            if f.get("provision") or f.get("amounts")
        ]
        logger.info("structured_facts_extracted", count=len(all_facts))

        if complexity != "complex":
            answer = await self._focused_answer(query, all_facts)
        else:
            asymmetries = await self._compare_parties(all_facts)
            logger.info("structured_asymmetries_found", count=len(asymmetries))
            answer = await self._assess_risks(query, all_facts, asymmetries)

        # Step 3b: Clean internal metadata from answer
        answer = self._clean_metadata(answer)

        # Step 4: Grounding validation (code, no LLM)
        answer = self._ground_check(answer, chunks)

        logger.info("structured_pipeline_complete",
                     facts=len(all_facts),
                     complexity=complexity,
                     answer_len=len(answer))

        return answer

    def _strip_document_metadata(self, text: str) -> str:
        """Remove document metadata that is not contractual content."""
        import re
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            # Skip lines that are purely document metadata
            if re.match(r"^(Page\s+\d+|\d+\s+of\s+\d+)$", stripped, re.IGNORECASE):
                continue
            if re.match(r"^(STRICTLY CONFIDENTIAL|CONFIDENTIAL|PRIVILEGED|DRAFT)$", stripped, re.IGNORECASE):
                continue
            if re.match(r"^(Prepared|Drafted|Drawn up)\s+by\b", stripped, re.IGNORECASE):
                continue
            if re.match(r"^Matter\s+[A-Z]{2}/", stripped):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    async def _fast_extract_and_answer(self, query: str, chunks: list) -> str:
        """
        FAST mode: 1 extraction call + 1 answer call (~10s total).
        Extract structured facts from context in ONE call,
        then answer using those facts.
        """
        # Combine all chunk text
        combined = "\n---\n".join(
            self._detect_clause_refs(
                self._strip_document_metadata(
                    c.text if hasattr(c, "text") else str(c)
                )
            )
            for c in chunks
            if len((c.text if hasattr(c, "text") else str(c)).strip()) > 50
        )

        # Step 1: Query-aware fact extraction in ONE call
        extract_prompt = f"""You are answering: "{query}"

Extract ALL facts relevant to this question from the contract text below.
Return a JSON array. For each fact:
- "value": the exact number, date, percentage, or term
- "type": what it represents (e.g. payment_due_date, interest_rate, liability_cap, notice_period, cure_period, committed_spend, billing_frequency)
- "clause": the clause or section reference
- "context": one sentence explaining what this value means

IMPORTANT: Extract EVERY numerical value, date, percentage, and time period
you find in the text. Do not skip any. Pay special attention to values
directly relevant to the question.

CONTRACT TEXT:
{combined}

Return ONLY a valid JSON array. No markdown, no explanation."""

        facts_json = "[]"
        try:
            result = await self.llm.complete(
                messages=[LLMMessage(role="user", content=extract_prompt)],
                role=AgentRole.EXTRACTOR,
            )
            facts_json = result.content.strip()
            facts_json = facts_json.replace("```json", "").replace("```", "").strip()
            logger.info("fast_facts_extracted", count=facts_json.count('"value"'))
        except Exception as e:
            logger.warning("fast_extraction_failed", error=str(e)[:80])

        # Step 2: Answer using extracted facts
        answer_prompt = f"""Answer this question using ONLY the extracted facts below.

QUESTION: {query}

EXTRACTED FACTS:
{facts_json}

ORIGINAL CONTRACT TEXT (for citation):
{combined}

RULES:
- Use exact values from the extracted facts
- Each value has a type and clause reference — use them correctly
- Do not confuse values of different types
  (e.g. a cure_period is NOT a payment_due_date)
- Cite clause references
- Answer the question as asked — state the direct fact first, then add
  context or qualifications. Never contradict a stated fact with your
  own interpretation of what it means in practice
- If the answer is not in the extracted facts, state that it was
  not identified in the analysed sections"""

        try:
            result = await self.llm.complete(
                messages=[LLMMessage(role="user", content=answer_prompt)],
                role=AgentRole.ANSWERER,
                max_tokens=2000,
            )
            return result.content
        except Exception as e:
            logger.error("fast_answer_failed", error=str(e)[:80])
            return ""

    async def _standard_extract_and_answer(self, query: str, chunks: list) -> str:
        """
        STANDARD mode: per-chunk extraction + focused answer (~20s total).
        More thorough than FAST, less expensive than DEEP.
        """
        # Extract from top chunks (parallel, batched)
        facts = await self._extract_facts(chunks)
        if not facts:
            return ""

        # Filter facts by query relevance
        _stop = set("what does is the a an in of for to and or this that how are can my our about cover mean say do it".split())
        _qwords = [w.lower().strip("?,. ") for w in query.split() if w.lower().strip("?,. ") not in _stop and len(w.strip("?,. ")) > 2]

        if _qwords:
            scored = []
            for f in facts:
                f_text = json.dumps(f).lower()
                score = sum(1 for w in _qwords if w in f_text)
                if score > 0:
                    if f.get("amounts"):
                        score += 1
                    topic = f.get("topic", "").lower().replace("_", " ")
                    if any(w in topic for w in _qwords):
                        score += 2
                    if len(f.get("provision", "")) > 50:
                        score += 1
                    scored.append((score, f))
            scored.sort(key=lambda x: -x[0])
            relevant = [f for _, f in scored[:30]]
        else:
            relevant = facts[:30]

        facts_json = json.dumps(relevant, indent=2)

        prompt = f"""Answer this question using the extracted contract facts.

QUESTION: {query}

EXTRACTED FACTS:
{facts_json}

RULES:
- Use exact values from the facts
- Each fact has a clause_ref and topic — do not mix values across topics
- Cite clause references
- Answer the question as asked — state the direct fact first, then add
  context or qualifications. Never contradict a stated fact with your
  own interpretation of what it means in practice
- If the question cannot be answered from these facts, state that
  the relevant provision was not identified in the analysed sections"""

        try:
            result = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                role=AgentRole.ANSWERER,
                max_tokens=2000,
            )
            return result.content
        except Exception as e:
            logger.error("standard_answer_failed", error=str(e)[:80])
            return ""


    def _get_industry_guidance(self, industry: str, contract_type: str) -> str:
        """Build concise industry risk guidance for answer prompts."""
        if industry == "general" and contract_type == "Other":
            return ""
        try:
            from app.agents.profiles.industry_playbooks import get_playbook
            playbook = get_playbook(industry)
            if not playbook or playbook.get("display_name") == "General":
                return ""
            parts = []
            parts.append(f"INDUSTRY CONTEXT: {playbook['display_name']}")
            if playbook.get("red_flags"):
                flags = playbook["red_flags"][:5]
                parts.append("Industry-specific red flags to watch for:")
                for f in flags:
                    parts.append(f"  - {f}")
            if playbook.get("risk_multipliers"):
                high_risk = [k for k, v in playbook["risk_multipliers"].items() if v >= 1.5]
                if high_risk:
                    parts.append(f"High-weight risk areas for this industry: {', '.join(high_risk)}")
            if playbook.get("mandatory_clauses"):
                parts.append(f"Mandatory clauses: {', '.join(playbook['mandatory_clauses'][:6])}")
            return "\n".join(parts)
        except Exception:
            return ""

    def _detect_clause_refs(self, text: str) -> str:
        """Detect clause/section numbers in chunk text and prepend as context."""
        import re
        # Find all clause-style references (N.N pattern) in text
        refs = re.findall(r'(?:^|\s)(\d{1,3}\.\d{1,2})\s', text)
        unique_refs = sorted(set(refs), key=lambda x: float(x) if '.' in x else 0)
        if unique_refs:
            return f"[CLAUSES IN THIS CHUNK: {', '.join(unique_refs[:10])}]\n\n{text}"
        return text

    async def _extract_facts(self, chunks: list) -> list[dict]:
        """Step 1: Extract structured facts from each chunk — parallel."""
        import asyncio as _aio

        async def _extract_one(i: int, chunk) -> list[dict]:
            chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)
            chunk_text = self._strip_document_metadata(chunk_text)
            if len(chunk_text.strip()) < 50:
                return []
            chunk_text = self._detect_clause_refs(chunk_text)
            prompt = EXTRACT_PROMPT.format(
                chunk_num=i + 1,
                chunk_text=chunk_text[:6000],
            )
            try:
                result = await self.llm.complete(
                    messages=[LLMMessage(role="user", content=prompt)],
                    role=AgentRole.EXTRACTOR,
                )
                parsed = self._parse_json(result.content)
                if isinstance(parsed, list):
                    for fact in parsed:
                        fact["source_chunk"] = i + 1
                    return parsed
            except Exception as e:
                logger.warning("fact_extraction_failed",
                               chunk=i, error=str(e)[:80])
            return []

        # Run all extractions in parallel (batches of 5 to avoid rate limits)
        all_facts = []
        batch_size = 10
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            tasks = [_extract_one(start + i, c) for i, c in enumerate(batch)]
            results = await _aio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_facts.extend(r)

        return all_facts

    async def _compare_parties(self, facts: list[dict]) -> list[dict]:
        """Step 2: Identify party asymmetries across all clauses."""
        relevant = [f for f in facts
                     if f.get("direction") != "not_applicable"
                     and f.get("topic") != "other"]

        if len(relevant) < 2:
            return []

        facts_json = json.dumps(relevant[:30], indent=2)

        try:
            result = await self.llm.complete(
                messages=[LLMMessage(role="user",
                                     content=COMPARE_PROMPT.format(facts_json=facts_json))],
                role=AgentRole.EXTRACTOR,
            )
            parsed = self._parse_json(result.content)
            return parsed if isinstance(parsed, list) else []
        except Exception as e:
            logger.warning("party_comparison_failed", error=str(e)[:80])
            return []

    async def _assess_risks(
        self, query: str, facts: list[dict], asymmetries: list[dict],
    ) -> str:
        """Step 3: Two focused calls — financials + risks — then combine."""
        # Split facts: any fact with amounts goes to financial, all facts go to risk
        financial_facts = [f for f in facts if f.get("amounts")]
        risk_facts = facts  # risk assessment sees everything for full context

        # Call 1: Financial summary
        financial_section = ""
        if financial_facts:
            fin_prompt = f"""Given these extracted financial facts from a contract, list ALL monetary obligations.

FINANCIAL FACTS:
{json.dumps(financial_facts[:30], indent=2)}

List EVERY monetary amount, payment term, due date, interest rate, billing mechanism,
committed spend, and true-up provision found in the facts.
Use exact figures — never approximate.
Convert chunk references: [Chunk N] becomes [N].
If multiple statements of work or schedules exist, list each separately.
Do not omit any amount.
If a financial topic you would expect (such as service credits, penalty caps, 
or late payment terms) is not present in the extracted facts, state that it 
was not identified in the analysed sections — never claim it does not exist.
State only amounts and terms that appear in the extracted facts.
Do not characterise a financial obligation as larger or smaller than stated."""

            try:
                result = await self.llm.complete(
                    messages=[LLMMessage(role="user", content=fin_prompt)],
                    role=AgentRole.ANSWERER,
                    max_tokens=2000,
                )
                financial_section = result.content
            except Exception as e:
                logger.warning("financial_summary_failed", error=str(e)[:80])

        # Call 2: Risk assessment
        risk_section = ""
        risk_json = json.dumps(risk_facts[:30], indent=2)
        asym_json = json.dumps(asymmetries[:15], indent=2)

        risk_prompt = ASSESS_PROMPT.format(
            facts_json=risk_json,
            asymmetries_json=asym_json,
            query=query,
        )

        try:
            result = await self.llm.complete(
                messages=[LLMMessage(role="user", content=risk_prompt)],
                role=AgentRole.ANSWERER,
                max_tokens=3000,
            )
            risk_section = result.content
        except Exception as e:
            logger.error("risk_assessment_failed", error=str(e)[:80])

        # Combine
        if financial_section and risk_section:
            return f"## Financial Obligations\n\n{financial_section}\n\n---\n\n{risk_section}"
        return financial_section or risk_section or ""

    def _clean_metadata(self, answer: str) -> str:
        """Remove any leaked internal labels from the answer."""
        import re
        answer = re.sub(r"\bfavors?_\w+\b", "", answer)
        answer = re.sub(r'\s*""\s*', " ", answer)
        answer = re.sub(r"\s*''\s*", " ", answer)
        answer = re.sub(r"\basymmetry_type\b", "", answer)
        answer = re.sub(r"\bsource_chunk\b", "", answer)
        answer = re.sub(r"\[Asymmetries\]", "", answer)
        answer = re.sub(r"\[Chunk (\d+)\]", r"[\1]", answer)
        answer = re.sub(r"The asymmetry analysis[^.]*\.", "", answer)
        answer = re.sub(r"\[asymmetry analysis[^\]]*\]", "", answer, flags=re.IGNORECASE)
        answer = re.sub(r'and\s+"+"\s+asymmetry', "", answer)
        answer = re.sub(r'Classified as[^.]*severity[^.]*\.', "", answer)
        answer = re.sub(r'"+"\s+(?:asymmetry|severity)', "", answer)
        answer = re.sub(r"  +", " ", answer)
        answer = re.sub(r"\n{3,}", "\n\n", answer)
        return answer.strip()

    def _ground_check(self, answer: str, chunks: list) -> str:
        """Step 4: Validate party directions and amounts against source text."""
        source = " ".join(
            c.text if hasattr(c, "text") else str(c)
            for c in chunks
        ).lower()

        warnings = []

        # Check monetary amounts in answer exist in source
        amounts = re.findall(r"[\$\₹\€\£][\d,]+(?:\.\d+)?", answer)
        for amt in amounts:
            num = amt.replace("$", "").replace("₹", "").replace("€", "").replace("£", "").replace(",", "")
            if num and num not in source.replace(",", ""):
                warnings.append(f"⚠️ Amount {amt} not found in source text.")

        # Check time periods appear near same context in source
        time_pattern = r"(\w+(?:\s+\w+){0,3})\s+(\d+)\s*(days?|months?|years?|weeks?|hours?|business\s+days?)"
        for match in re.finditer(time_pattern, answer.lower()):
            preceding = match.group(1).strip()
            num = match.group(2)
            unit = match.group(3)
            context_words = [w for w in preceding.split() if len(w) > 3]
            if not context_words:
                continue
            found = False
            for cw in context_words:
                pattern = f"(?:{re.escape(cw)}.{{0,80}}{num}|{num}.{{0,80}}{re.escape(cw)})"
                if re.search(pattern, source):
                    found = True
                    break
            if not found:
                warnings.append(
                    f"⚠️ '{num} {unit}' not found near '{preceding}' in source text."
                )

        if warnings:
            return answer + "\n\n---\n" + "\n".join(warnings[:3])
        return answer

    def _parse_json(self, text: str) -> list | dict:
        """Parse JSON from LLM output, handling markdown fences."""
        text = text.strip()
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        text = text.strip()
        return json.loads(text)


# Singleton
_synthesizer: StructuredSynthesizer | None = None


def get_structured_synthesizer() -> StructuredSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = StructuredSynthesizer()
    return _synthesizer

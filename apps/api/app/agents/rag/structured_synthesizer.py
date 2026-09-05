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
  "clause_ref": "the clause/section number if stated, or 'unstated'",
  "topic": "one of: payment, liability, indemnity, termination, renewal, service_level, ip, data_protection, confidentiality, insurance, force_majeure, acceptance, billing, compliance, other",
  "obligor": "the party who MUST do something — use the EXACT name from the text",
  "beneficiary": "the party who BENEFITS — use the EXACT name from the text",
  "provision": "what the clause requires or permits — one sentence using exact language from the text",
  "amounts": ["any monetary amounts, percentages, or time periods — exact figures only"],
  "cap": "capped/uncapped/not_applicable",
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
Every claim must have a citation — if a fact has no clause reference, omit it entirely.
Never include a fact marked as "unstated" or without a specific clause/section reference.
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
    ) -> str:
        """
        Run the full structured pipeline:
        Extract → Compare → Assess → Ground → Answer
        """
        logger.info("structured_pipeline_start",
                     query=query[:50], chunks=len(chunks))

        # Step 1: Extract facts from each chunk
        all_facts = await self._extract_facts(chunks)
        if not all_facts:
            logger.warning("structured_no_facts_extracted")
            return ""

        # Remove facts that could not be properly attributed
        all_facts = [
            f for f in all_facts
            if f.get("clause_ref", "unstated").lower() != "unstated"
            and f.get("obligor", "unclear").lower() != "unclear"
        ]
        logger.info("structured_facts_extracted", count=len(all_facts))

        # Step 2: Compare parties
        asymmetries = await self._compare_parties(all_facts)
        logger.info("structured_asymmetries_found", count=len(asymmetries))

        # Step 3: Risk assessment + final answer
        answer = await self._assess_risks(query, all_facts, asymmetries)

        # Step 3b: Clean internal metadata from answer
        answer = self._clean_metadata(answer)

        # Step 4: Grounding validation (code, no LLM)
        answer = self._ground_check(answer, chunks)

        logger.info("structured_pipeline_complete",
                     facts=len(all_facts),
                     asymmetries=len(asymmetries),
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
        """Step 1: Extract structured facts from each chunk."""
        all_facts = []

        for i, chunk in enumerate(chunks):
            chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)
            chunk_text = self._strip_document_metadata(chunk_text)
            if len(chunk_text.strip()) < 50:
                continue
            # Enrich with detected clause numbers
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
                    all_facts.extend(parsed)
            except Exception as e:
                logger.warning("fact_extraction_failed",
                               chunk=i, error=str(e)[:80])

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

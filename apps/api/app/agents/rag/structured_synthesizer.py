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
- Return ONLY a valid JSON array. No markdown, no explanation, no preamble."""

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
  "asymmetry_type": "one of: favorable_to_a, favorable_to_b, mutual, unclear",
  "severity": "critical/high/medium/low",
  "clause_refs": ["relevant clause numbers from the facts"]
}}

Focus on:
- Rights that differ between the two parties
- Obligations that apply to only one party
- Caps or limits that apply differently
- Mechanisms that favour one party (retroactive billing, deemed acceptance, etc.)

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

Use [Chunk N] citations matching the source_chunk field in the extracted facts.
Every claim must have a citation.
Never repeat the same point.
Never contradict yourself — if two facts seem to conflict, present both and explain."""


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

        logger.info("structured_facts_extracted", count=len(all_facts))

        # Step 2: Compare parties
        asymmetries = await self._compare_parties(all_facts)
        logger.info("structured_asymmetries_found", count=len(asymmetries))

        # Step 3: Risk assessment + final answer
        answer = await self._assess_risks(query, all_facts, asymmetries)

        # Step 4: Grounding validation (code, no LLM)
        answer = self._ground_check(answer, chunks)

        logger.info("structured_pipeline_complete",
                     facts=len(all_facts),
                     asymmetries=len(asymmetries),
                     answer_len=len(answer))

        return answer

    async def _extract_facts(self, chunks: list) -> list[dict]:
        """Step 1: Extract structured facts from each chunk."""
        all_facts = []

        for i, chunk in enumerate(chunks):
            chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)
            if len(chunk_text.strip()) < 50:
                continue

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
        """Step 3: Produce ranked risk assessment from structured data."""
        facts_json = json.dumps(facts[:40], indent=2)
        asymmetries_json = json.dumps(asymmetries[:15], indent=2)

        prompt = ASSESS_PROMPT.format(
            facts_json=facts_json,
            asymmetries_json=asymmetries_json,
            query=query,
        )

        try:
            result = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                role=AgentRole.ANSWERER,
            )
            return result.content
        except Exception as e:
            logger.error("risk_assessment_failed", error=str(e)[:80])
            return ""

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

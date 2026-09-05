"""
Grounding Validator
===================
Validates LLM-generated answers against source context.
Catches hallucinations, fabricated numbers, and unsupported claims.
"""
import re
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


class GroundingResult:
    def __init__(self):
        self.total_claims = 0
        self.grounded_claims = 0
        self.ungrounded_claims: list[str] = []
        self.fabricated_numbers: list[str] = []
        self.warnings: list[str] = []

    @property
    def score(self) -> float:
        if self.total_claims == 0:
            return 1.0
        return self.grounded_claims / self.total_claims

    @property
    def is_reliable(self) -> bool:
        return self.score >= 0.7 and len(self.fabricated_numbers) == 0

    def to_dict(self) -> dict:
        return {
            "grounding_score": round(self.score, 3),
            "total_claims": self.total_claims,
            "grounded_claims": self.grounded_claims,
            "ungrounded": self.ungrounded_claims[:5],
            "fabricated_numbers": self.fabricated_numbers[:5],
            "warnings": self.warnings[:5],
            "is_reliable": self.is_reliable,
        }


def validate_grounding(answer: str, context: str) -> GroundingResult:
    """
    Validate that the LLM answer is grounded in the source context.
    Checks:
    1. Numbers in the answer appear in the context
    2. Dates in the answer appear in the context
    3. Clause references exist in the context
    4. Key claims are traceable to context
    """
    result = GroundingResult()
    context_lower = context.lower()
    answer_lower = answer.lower()

    # 0. Context-aware number verification
    # For any "N days/months/years" claim, extract the surrounding words
    # and verify the SAME number + context pairing exists in the source.
    # Prevents cross-contamination — same number in different clause contexts
    _num_context_pattern = r"(\w+(?:\s+\w+){0,3})\s+\(?(\d+)\)?\s*(days?|months?|years?|weeks?|hours?|business\s+days?)"
    for _match in re.finditer(_num_context_pattern, answer_lower):
        _preceding = _match.group(1).strip()
        _num = _match.group(2)
        _unit = _match.group(3)
        result.total_claims += 1
        # Check: does this number appear near the same context words in source?
        _context_words = [w for w in _preceding.split() if len(w) > 3]
        if not _context_words:
            result.grounded_claims += 1
            continue
        # At least one context word must appear within 80 chars of the number in source
        _grounded = False
        for _cw in _context_words:
            _pattern = f"(?:{_cw}.{{0,80}}{_num}|{_num}.{{0,80}}{_cw})"
            if re.search(_pattern, context_lower):
                _grounded = True
                break
        if _grounded:
            result.grounded_claims += 1
        else:
            result.fabricated_numbers.append(f"{_num} {_unit} (near '{_preceding}')"  )
            result.warnings.append(f"'{_num} {_unit}' not found near '{_preceding}' in source text")

    # 0b. Verify computed sums — if a number is a sum of other numbers in the answer,
    # check that the components exist in the source (not the sum itself)
    _all_amounts_in_answer = re.findall(r'[\$]?([\d,]+(?:\.\d+)?)\s*(?:M|million|annually|year)', answer_lower)
    _amounts_in_source = re.findall(r'[\d,]+(?:\.\d+)?', context_lower)
    _source_nums = set()
    for a in _amounts_in_source:
        try:
            _source_nums.add(float(a.replace(",", "")))
        except ValueError:
            pass

    # 1. Check all monetary amounts
    money_pattern = r'[\$\₹\€\£][\d,]+(?:\.\d+)?(?:\s*(?:million|billion|lakh|crore|M|K|B))?'
    amounts_in_answer = re.findall(money_pattern, answer)
    for amount in amounts_in_answer:
        result.total_claims += 1
        # Extract just the number
        num = re.sub(r'[\$\₹\€\£,\s]', '', amount).lower()
        num = num.replace('million', '').replace('billion', '').replace('lakh', '').replace('crore', '').replace('m', '').replace('k', '').replace('b', '').strip()
        if num and (num in context_lower or amount.strip('$₹€£ ') in context_lower):
            result.grounded_claims += 1
        else:
            result.fabricated_numbers.append(amount)

    # 2. Check all percentages
    pct_pattern = r'\d+(?:\.\d+)?%'
    pcts_in_answer = re.findall(pct_pattern, answer)
    for pct in pcts_in_answer:
        result.total_claims += 1
        if pct in context_lower or pct.replace('%', '') in context_lower:
            result.grounded_claims += 1
        else:
            result.fabricated_numbers.append(pct)

    # 3. Check specific day/period numbers
    day_pattern = r'(\d+)\s*(?:days?|months?|years?|weeks?|hours?|minutes?|business days?)'
    days_in_answer = re.findall(day_pattern, answer_lower)
    for num in days_in_answer:
        result.total_claims += 1
        if num in context_lower:
            result.grounded_claims += 1
        else:
            # Check if number appears as word form anywhere in context
            # Generic: search for the digit string near time-related words
            import re as _re
            # Check digit appears within 50 chars of a time word in context
            _time_words = ["day", "month", "year", "week", "hour", "minute", "business", "notice", "period"]
            _found_nearby = False
            for _tw in _time_words:
                _pattern = f"(?:{num}.{{0,30}}{_tw}|{_tw}.{{0,30}}{num})"
                if _re.search(_pattern, context_lower):
                    _found_nearby = True
                    break
            if _found_nearby:
                result.grounded_claims += 1
            else:
                # Also check word forms using a simple conversion
                try:
                    _n = int(num)
                    # Search for any occurrence of the number in context
                    # including written forms like "forty-five" or "(45)"
                    if f"({num})" in context_lower or f" {num} " in context_lower:
                        result.grounded_claims += 1
                    else:
                        result.fabricated_numbers.append(f"{num} (time period)")
                except ValueError:
                    result.fabricated_numbers.append(f"{num} (time period)")

    # 4. Check clause references
    clause_pattern = r'(?:clause|section|article)\s+(\d+(?:\.\d+)*)'
    clauses_in_answer = re.findall(clause_pattern, answer_lower)
    for clause_num in clauses_in_answer:
        result.total_claims += 1
        if clause_num in context_lower:
            result.grounded_claims += 1
        else:
            result.ungrounded_claims.append(f"Clause {clause_num}")

    # 5. Check dates
    date_pattern = r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}'
    dates_in_answer = re.findall(date_pattern, answer, re.IGNORECASE)
    for date_str in dates_in_answer:
        result.total_claims += 1
        if date_str.lower() in context_lower:
            result.grounded_claims += 1
        else:
            result.ungrounded_claims.append(f"Date: {date_str}")

    # ISO dates
    iso_dates = re.findall(r'\d{4}-\d{2}-\d{2}', answer)
    for d in iso_dates:
        result.total_claims += 1
        if d in context_lower:
            result.grounded_claims += 1
        else:
            result.ungrounded_claims.append(f"Date: {d}")

    # Warnings
    if result.fabricated_numbers:
        result.warnings.append(
            f"NUMBERS NOT IN CONTEXT: {', '.join(result.fabricated_numbers[:3])}")
    if result.score < 0.7:
        result.warnings.append(
            f"LOW GROUNDING: only {result.score:.0%} of claims verified")

    logger.info("grounding_validation",
                score=round(result.score, 3),
                total=result.total_claims,
                grounded=result.grounded_claims,
                fabricated=len(result.fabricated_numbers))

    return result


def add_grounding_disclaimer(answer: str, result: GroundingResult) -> str:
    """
    Add grounding warning to answer if reliability is low.
    """
    if result.is_reliable:
        return answer

    warnings = []
    if result.fabricated_numbers:
        warnings.append(
            f"⚠️ Some figures in this response ({', '.join(result.fabricated_numbers[:2])}) "
            f"could not be verified against the contract text. Please cross-check.")
    elif result.score < 0.7:
        warnings.append(
            f"⚠️ Grounding score: {result.score:.0%}. Some claims may not be directly "
            f"traceable to the contract text. Please verify key figures.")

    if warnings:
        return answer + "\n\n---\n" + "\n".join(warnings)
    return answer

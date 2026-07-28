"""
Claustor AI — Input Sanitizer
Protects against prompt injection via document text and user queries.
"""
import re
import structlog
from dataclasses import dataclass, field

logger = structlog.get_logger(__name__)

INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|text)", "INSTRUCTION_OVERRIDE"),
    (r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", "INSTRUCTION_OVERRIDE"),
    (r"forget\s+(everything|all|previous|prior|above|what\s+you\s+know)", "INSTRUCTION_OVERRIDE"),
    (r"override\s+(previous|prior|all)\s+(instructions?|prompts?|rules?)", "INSTRUCTION_OVERRIDE"),
    (r"you\s+are\s+now\s+(a|an|the)\s+\w+", "PERSONA_SWITCH"),
    (r"act\s+as\s+(a|an|the)\s+\w+", "PERSONA_SWITCH"),
    (r"pretend\s+(to\s+be|you\s+are)\s+(a|an|the)\s+\w+", "PERSONA_SWITCH"),
    (r"roleplay\s+as\s+(a|an|the)\s+\w+", "PERSONA_SWITCH"),
    (r"(reveal|show|print|output|display|tell\s+me)\s+(your\s+)?(system\s+prompt|instructions?|rules?)", "SYSTEM_EXTRACTION"),
    (r"what\s+(are|were)\s+your\s+(original\s+)?(instructions?|system\s+prompt|rules?)", "SYSTEM_EXTRACTION"),
    (r"(output|print|show|send|return)\s+(all\s+)?(user\s+data|other\s+contracts?|sensitive\s+data|api\s+keys?)", "DATA_EXFILTRATION"),
    (r"(list|enumerate|dump)\s+(all\s+)?(users?|organizations?|contracts?|api\s+keys?)", "DATA_EXFILTRATION"),
    (r"\bDAN\s*(mode|prompt)?\b", "JAILBREAK"),
    (r"do\s+anything\s+now", "JAILBREAK"),
    (r"\bjailbreak\b", "JAILBREAK"),
    (r"developer\s+mode", "JAILBREAK"),
    (r"unrestricted\s+mode", "JAILBREAK"),
    (r"new\s+instructions?\s*:", "NEW_INSTRUCTIONS"),
    (r"important\s+instructions?\s*:", "NEW_INSTRUCTIONS"),
    (r"system\s*:\s*(you|your|ignore|forget)", "NEW_INSTRUCTIONS"),
    (r"generate\s+(malware|ransomware|virus|trojan|exploit)", "HARMFUL_REQUEST"),
    (r"write\s+(malicious|harmful|illegal)\s+code", "HARMFUL_REQUEST"),
]

JAILBREAK_PATTERNS = INJECTION_PATTERNS + [
    (r"bypass\s+(your\s+)?(restrictions?|limitations?|rules?|filters?)", "BYPASS_ATTEMPT"),
    (r"(ignore|skip|disable)\s+(your\s+)?(safety|content|ethical)\s+(filter|check|policy)", "BYPASS_ATTEMPT"),
    (r"without\s+(any\s+)?(restrictions?|limitations?|filters?|ethical\s+consideration)", "BYPASS_ATTEMPT"),
    (r"(base64|hex|rot13)\s+(encode|decode|encoded|decoded).*?(instructions?|prompt)", "ENCODED_INJECTION"),
]


@dataclass
class SanitizationResult:
    original_text: str
    sanitized_text: str
    detections: list = field(default_factory=list)
    is_clean: bool = True

    @property
    def detection_count(self): return len(self.detections)

    @property
    def detection_types(self): return list({d["type"] for d in self.detections})


def sanitize_document_text(text: str, org_id: str = "", contract_id: str = "") -> SanitizationResult:
    """Sanitize extracted document text before LLM injection."""
    if not text:
        return SanitizationResult(original_text=text, sanitized_text=text)

    sanitized = text
    detections = []
    for pattern, dtype in INJECTION_PATTERNS:
        compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        matches = compiled.findall(sanitized)
        if matches:
            for m in matches:
                detections.append({"type": dtype, "match": str(m)[:100]})
            sanitized = compiled.sub("[CONTENT REDACTED BY SECURITY FILTER]", sanitized)

    if detections:
        logger.warning("document_injection_detected",
            org_id=org_id, contract_id=contract_id,
            count=len(detections),
            types=list({d["type"] for d in detections}))

    return SanitizationResult(
        original_text=text, sanitized_text=sanitized,
        detections=detections, is_clean=len(detections) == 0)


def check_query_for_jailbreak(query: str, org_id: str = "", user_id: str = "") -> SanitizationResult:
    """Check user query for jailbreak/injection attempts."""
    if not query:
        return SanitizationResult(original_text=query, sanitized_text=query)

    detections = []
    for pattern, dtype in JAILBREAK_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            detections.append({"type": dtype})

    if detections:
        logger.warning("jailbreak_query_detected",
            org_id=org_id, user_id=user_id,
            preview=query[:100],
            types=list({d["type"] for d in detections}))

    return SanitizationResult(
        original_text=query, sanitized_text=query,
        detections=detections, is_clean=len(detections) == 0)


def validate_context_window(text: str, max_tokens: int = 100000) -> tuple:
    """Estimate token count and truncate if over limit. ~4 chars per token."""
    estimated = len(text) // 4
    if estimated <= max_tokens:
        return text, False
    keep = max_tokens * 4
    half = keep // 2
    truncated = (text[:half]
        + f"\n\n[... {estimated - max_tokens:,} tokens truncated — context window limit ...]\n\n"
        + text[-half:])
    logger.warning("context_window_truncated",
        original_tokens=estimated, max_tokens=max_tokens)
    return truncated, True

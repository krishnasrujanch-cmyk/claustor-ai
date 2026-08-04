"""
Claustor AI — Hierarchical Contract Chunker
Produces parent-child chunks with rich metadata for legal contracts.

Parent chunks: full ARTICLE/SECTION (context retrieval)
Child chunks:  ≤300 words (semantic search, fits bge-large 512 tokens)
Special types: table, title, appendix, signature (excluded from search)
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# Chunk types
CHUNK_TYPE_CLAUSE    = "clause"
CHUNK_TYPE_TABLE     = "table"
CHUNK_TYPE_TITLE     = "title"
CHUNK_TYPE_APPENDIX  = "appendix"
CHUNK_TYPE_SIGNATURE = "signature"

# Max child chunk size (words) — safe for bge-large-en-v1.5 (512 tokens)
MAX_CHILD_WORDS = 300
OVERLAP_SENTENCES = 2  # sentences to overlap between child chunks


@dataclass
class ContractChunkData:
    """Represents a single chunk ready for storage."""
    chunk_id:    UUID
    parent_id:   Optional[UUID]
    is_parent:   bool
    chunk_type:  str
    chunk_index: int
    text:        str
    heading:     Optional[str]
    section_ref: Optional[str]
    page_number: Optional[int]
    importance:  str
    cross_refs:  list
    table_json:  Optional[dict]

    # Contract metadata (denormalized for Pinecone filtering)
    contract_id:    UUID
    org_id:         UUID
    counterparty:   Optional[str]
    risk_level:     Optional[str]
    contract_type:  Optional[str]
    effective_date: Optional[str]
    expiry_date:    Optional[str]
    risk_score:     Optional[float] = None
    pinecone_id:    Optional[str] = None


# ── Structure Detection ────────────────────────────────────────────────────────

BOUNDARY_PATTERN = re.compile(
    r'(?=\n(?:ARTICLE|SECTION|SCHEDULE|EXHIBIT|ANNEX|APPENDIX|PART|CHAPTER)'
    r'\s+[\dA-Z]+[.:]?)',
    re.IGNORECASE
)

SIGNATURE_PATTERN = re.compile(
    r'(IN WITNESS WHEREOF|SIGNED BY|SIGNATURE PAGE|EXECUTED BY'
    r'|By:\s*_{3,}|Name:\s*_{3,}|Title:\s*_{3,})',
    re.IGNORECASE
)

APPENDIX_PATTERN = re.compile(
    r'^(?:SCHEDULE|EXHIBIT|ANNEX|APPENDIX)\s+[A-Z\d]+',
    re.IGNORECASE | re.MULTILINE
)

TABLE_ROW_PATTERN = re.compile(
    r'(\|[^\n]+\|[^\n]*\n){2,}|(\S[^\t\n]+\t[^\t\n]+\t[^\n]*\n){2,}',
    re.MULTILINE
)

HEADING_PATTERN = re.compile(
    r'^(?:ARTICLE|SECTION|SCHEDULE|EXHIBIT|ANNEX|APPENDIX|PART)\s+[\dA-Z]+[.:]?\s+(.+)$',
    re.IGNORECASE | re.MULTILINE
)

CROSS_REF_PATTERN = re.compile(
    r'(?:pursuant to|as defined in|subject to|in accordance with|'
    r'referred to in|set forth in|described in)\s+'
    r'(?:Section|Article|Clause|Schedule|Exhibit)\s+[\d.]+',
    re.IGNORECASE
)


def detect_section_type(text: str) -> str:
    """Detect the type of a section."""
    first_line = text.strip().split('\n')[0].upper()
    if SIGNATURE_PATTERN.search(text[:500]):
        return CHUNK_TYPE_SIGNATURE
    if re.match(r'^(?:SCHEDULE|EXHIBIT|ANNEX|APPENDIX)\s+', first_line):
        return CHUNK_TYPE_APPENDIX
    # Only classify as table if majority of content is table rows
    table_matches = TABLE_ROW_PATTERN.findall(text)
    table_chars = sum(len(m[0] or m[1]) for m in table_matches)
    if table_chars > len(text) * 0.4:
        return CHUNK_TYPE_TABLE
    return CHUNK_TYPE_CLAUSE


def extract_heading(text: str) -> tuple[str, str]:
    """Extract heading and section reference from section text."""
    first_line = text.strip().split('\n')[0].strip()
    m = re.match(
        r'^((?:ARTICLE|SECTION|SCHEDULE|EXHIBIT|ANNEX|APPENDIX|PART)\s+[\dA-Z]+[.:]?)\s*(.*)',
        first_line, re.IGNORECASE
    )
    if m:
        return m.group(2).strip() or first_line, m.group(1).strip()
    return first_line[:200], ""


def extract_cross_refs(text: str) -> list[str]:
    """Extract cross-references to other sections."""
    refs = []
    for m in CROSS_REF_PATTERN.finditer(text):
        ref = m.group(0).strip()
        if ref not in refs:
            refs.append(ref[:100])
    return refs[:10]  # max 10 refs


def score_importance(chunk_type: str, heading: str, text: str) -> str:
    """Score chunk importance: high/medium/low."""
    heading_lower = heading.lower()
    high_keywords = [
        'terminat', 'liabilit', 'indemnif', 'payment', 'ip', 'intellectual',
        'confidential', 'govern', 'dispute', 'penalty', 'breach', 'remedy'
    ]
    if any(k in heading_lower for k in high_keywords):
        return "high"
    if chunk_type in (CHUNK_TYPE_TABLE, CHUNK_TYPE_APPENDIX):
        return "medium"
    return "low"


def table_to_json(text: str) -> Optional[dict]:
    """Convert markdown table to JSON rows."""
    lines = [l.strip() for l in text.strip().split('\n')
             if l.strip() and not re.match(r'^\|[-:]+\|', l)]
    if not lines or '|' not in lines[0]:
        return None
    headers = [h.strip() for h in lines[0].strip('|').split('|') if h.strip()]
    rows = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip('|').split('|')]
        if cells and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return {"headers": headers, "rows": rows} if rows else None


# ── Main Chunker ───────────────────────────────────────────────────────────────

def build_hierarchical_chunks(
    full_text: str,
    tables: list,
    contract_id: UUID,
    org_id: UUID,
    contract_meta: dict = None,
) -> list[ContractChunkData]:
    """
    Build parent-child chunk hierarchy from contract text.

    Returns list of ContractChunkData ready for PostgreSQL + Pinecone.
    """
    meta = contract_meta or {}
    chunks: list[ContractChunkData] = []
    chunk_index = 0

    # ── Step 1: Split on structural boundaries ──
    sections = BOUNDARY_PATTERN.split(full_text)
    sections = [s.strip() for s in sections if s.strip() and len(s.strip()) > 50]

    # If no structure found — treat whole text as one section
    if len(sections) <= 1:
        sections = [full_text]

    for section_text in sections:
        section_type = detect_section_type(section_text)
        heading, section_ref = extract_heading(section_text)
        cross_refs = extract_cross_refs(section_text)
        importance = score_importance(section_type, heading, section_text)
        table_json = table_to_json(section_text) if section_type == CHUNK_TYPE_TABLE else None

        # ── Create PARENT chunk (full section) ──
        parent_id = uuid4()
        parent_chunk = ContractChunkData(
            chunk_id=parent_id,
            parent_id=None,
            is_parent=True,
            chunk_type=section_type,
            chunk_index=chunk_index,
            text=section_text,
            heading=heading[:200] if heading else None,
            section_ref=section_ref[:50] if section_ref else None,
            page_number=None,
            importance=importance,
            cross_refs=cross_refs,
            table_json=table_json,
            contract_id=contract_id,
            org_id=org_id,
            counterparty=meta.get("counterparty"),
            risk_level=meta.get("risk_level"),
            contract_type=meta.get("contract_type"),
            effective_date=str(meta.get("effective_date")) if meta.get("effective_date") else None,
            expiry_date=str(meta.get("expiry_date")) if meta.get("expiry_date") else None,
        )
        chunks.append(parent_chunk)
        chunk_index += 1

        # ── Create CHILD chunks (≤300 words each) ──
        # Skip signature chunks from child splitting (don't embed)
        if section_type == CHUNK_TYPE_SIGNATURE:
            continue

        # Tables get one child chunk (preserve structure)
        if section_type == CHUNK_TYPE_TABLE:
            child_id = uuid4()
            child = ContractChunkData(
                chunk_id=child_id,
                parent_id=parent_id,
                is_parent=False,
                chunk_type=CHUNK_TYPE_TABLE,
                chunk_index=chunk_index,
                text=section_text,
                heading=heading[:200] if heading else None,
                section_ref=section_ref[:50] if section_ref else None,
                page_number=None,
                importance=importance,
                cross_refs=cross_refs,
                table_json=table_json,
                contract_id=contract_id,
                org_id=org_id,
                counterparty=meta.get("counterparty"),
                risk_level=meta.get("risk_level"),
                contract_type=meta.get("contract_type"),
                effective_date=str(meta.get("effective_date")) if meta.get("effective_date") else None,
                expiry_date=str(meta.get("expiry_date")) if meta.get("expiry_date") else None,
            )
            chunks.append(child)
            chunk_index += 1
            continue

        # Split section into child chunks
        # Only create children if section > MAX_CHILD_WORDS
        words_in_section = len(section_text.split())
        child_texts = _split_into_children(section_text, MAX_CHILD_WORDS) \
                      if words_in_section > MAX_CHILD_WORDS else [section_text]
        # Skip if child is identical to parent (single small section)
        skip_if_same = len(child_texts) == 1
        for child_text in child_texts:
            if skip_if_same:
                continue  # parent IS the chunk, no need for duplicate child
            if not child_text.strip():
                continue
            child_id = uuid4()
            child = ContractChunkData(
                chunk_id=child_id,
                parent_id=parent_id,
                is_parent=False,
                chunk_type=section_type,
                chunk_index=chunk_index,
                text=child_text,
                heading=heading[:200] if heading else None,
                section_ref=section_ref[:50] if section_ref else None,
                page_number=None,
                importance=importance,
                cross_refs=cross_refs,
                table_json=None,
                contract_id=contract_id,
                org_id=org_id,
                counterparty=meta.get("counterparty"),
                risk_level=meta.get("risk_level"),
                contract_type=meta.get("contract_type"),
                effective_date=str(meta.get("effective_date")) if meta.get("effective_date") else None,
                expiry_date=str(meta.get("expiry_date")) if meta.get("expiry_date") else None,
            )
            chunks.append(child)
            chunk_index += 1

    # ── Step 2: Add standalone table chunks ──
    for i, table in enumerate(tables or []):
        t_text = table if isinstance(table, str) else table.get("text", "")
        if not t_text.strip():
            continue
        # Skip if already covered by section
        already = any(t_text[:80] in c.text for c in chunks if c.chunk_type == CHUNK_TYPE_TABLE)
        if already:
            continue
        parent_id = uuid4()
        t_json = table_to_json(t_text)
        table_chunk = ContractChunkData(
            chunk_id=parent_id,
            parent_id=None,
            is_parent=True,
            chunk_type=CHUNK_TYPE_TABLE,
            chunk_index=chunk_index,
            text=t_text,
            heading=f"Table {i+1}",
            section_ref=None,
            page_number=None,
            importance="medium",
            cross_refs=[],
            table_json=t_json,
            contract_id=contract_id,
            org_id=org_id,
            counterparty=meta.get("counterparty"),
            risk_level=meta.get("risk_level"),
            contract_type=meta.get("contract_type"),
            effective_date=str(meta.get("effective_date")) if meta.get("effective_date") else None,
            expiry_date=str(meta.get("expiry_date")) if meta.get("expiry_date") else None,
        )
        chunks.append(table_chunk)
        chunk_index += 1

    logger.info(
        f"hierarchical_chunking_done: "
        f"total={len(chunks)} "
        f"parents={sum(1 for c in chunks if c.is_parent)} "
        f"children={sum(1 for c in chunks if not c.is_parent)} "
        f"tables={sum(1 for c in chunks if c.chunk_type==CHUNK_TYPE_TABLE)}"
    )
    return chunks


def _split_into_children(text: str, max_words: int) -> list[str]:
    """
    Split section text into child chunks ≤ max_words.
    Uses sentence boundaries for clean splits with overlap.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    children = []
    current: list[str] = []
    current_len = 0
    overlap_buffer: list[str] = []

    for sent in sentences:
        sent_words = sent.split()
        if current_len + len(sent_words) > max_words and current:
            children.append(" ".join(current))
            # Keep last N sentences as overlap
            overlap_buffer = current[-OVERLAP_SENTENCES:] if len(current) > OVERLAP_SENTENCES else current
            current = overlap_buffer + sent_words
            current_len = len(current)
        else:
            current.extend(sent_words)
            current_len += len(sent_words)

    if current:
        children.append(" ".join(current))

    return children

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
    r'(?:'
    r'(?:pursuant to|as defined in|subject to|in accordance with|'
    r'referred to in|set forth in|described in|under|per|see|'
    r'except as provided in|as specified in|as outlined in)\s+'
    r')?'
    r'(?:Section|Article|Clause|Schedule|Exhibit|Annex|Appendix)\s+[\d.A-Z]+(?:[.(][\d.A-Z]+[).]?)*',
    re.IGNORECASE
)


def detect_section_type(text: str) -> str:
    """Detect the type of a section."""
    first_line = text.strip().split('\n')[0].upper()
    if SIGNATURE_PATTERN.search(text[:500]):
        return CHUNK_TYPE_SIGNATURE
    # Check table BEFORE appendix — a schedule containing a table
    # should be chunked as table (per-row) not as appendix (single block)
    # Count lines that look like table rows (contain 2+ pipe separators)
    _lines = [l for l in text.strip().split('\n') if l.strip()]
    _pipe_lines = [l for l in _lines if l.count('|') >= 3]
    # Only classify as table if pipe lines are majority of content
    # Prevents clause sections with a few cross-references being classified as tables
    if len(_pipe_lines) >= 3 and len(_pipe_lines) > len(_lines) * 0.4:
        return CHUNK_TYPE_TABLE
    if re.match(r'^(?:SCHEDULE|EXHIBIT|ANNEX|APPENDIX)\s+', first_line):
        return CHUNK_TYPE_APPENDIX
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
    """Convert markdown table(s) to JSON rows.
    Handles multiple tables in one text block by detecting
    new header rows (a pipe row followed by a separator row).
    """
    raw_lines = text.strip().split('\n')
    all_tables = []
    current_headers = None
    current_rows = []

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].strip()

        # Skip empty lines and non-table lines
        if not line or '|' not in line:
            i += 1
            continue

        # Check if this is a header row (next line is separator)
        is_header = False
        if i + 1 < len(raw_lines):
            next_line = raw_lines[i + 1].strip()
            if re.match(r'^\|[-:\s|]+\|$', next_line) or all(
                re.match(r'^[-:]+$', c.strip()) for c in next_line.strip('|').split('|') if c.strip()
            ):
                is_header = True

        if is_header:
            # Save previous table if exists
            if current_headers and current_rows:
                all_tables.append({"headers": current_headers, "rows": current_rows, "title": _current_title})
            # Find title: last non-table, non-empty line before this header
            _current_title = ""
            for _back in range(i - 1, max(i - 4, -1), -1):
                _bl = raw_lines[_back].strip()
                if _bl and '|' not in _bl:
                    _current_title = _bl
                    break
            # Start new table
            current_headers = [h.strip() for h in line.strip('|').split('|') if h.strip()]
            current_rows = []
            i += 2  # skip header + separator
            continue

        # Data row — assign to current table
        if current_headers:
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) == len(current_headers):
                if not all(re.match(r'^[-:]+$', c) for c in cells if c):
                    current_rows.append(dict(zip(current_headers, cells)))
        i += 1

    # Save last table
    if current_headers and current_rows:
        all_tables.append({"headers": current_headers, "rows": current_rows, "title": _current_title})

    if not all_tables:
        return None

    # Merge all tables into one result with per-row header tracking
    combined_headers = []
    combined_rows = []
    for table in all_tables:
        for h in table["headers"]:
            if h not in combined_headers:
                combined_headers.append(h)
        for row in table["rows"]:
            row["_table_headers"] = table["headers"]
            row["_table_title"] = table.get("title", "")
            combined_rows.append(row)

    return {"headers": combined_headers, "rows": combined_rows, "tables": all_tables} if combined_rows else None


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

        # Tables: split into per-row chunks for granular retrieval
        # Each row becomes its own child chunk with headers prepended
        if section_type == CHUNK_TYPE_TABLE:
            _parsed = table_to_json(section_text) if not table_json else table_json
            if _parsed and _parsed.get("rows") and len(_parsed["rows"]) > 1:
                for _row in _parsed["rows"]:
                    # Use this row's own table headers and title
                    _row_headers = _row.pop("_table_headers", _parsed.get("headers", []))
                    _row_title = _row.pop("_table_title", heading or "")
                    _header_line = " | ".join(_row_headers)
                    _row_text = " | ".join(str(_row.get(h, "")) for h in _row_headers)
                    _chunk_text = f"{_row_title or heading or ''}\n{_header_line}\n{_row_text}"
                    child_id = uuid4()
                    child = ContractChunkData(
                        chunk_id=child_id,
                        parent_id=parent_id,
                        is_parent=False,
                        chunk_type=CHUNK_TYPE_TABLE,
                        chunk_index=chunk_index,
                        text=_chunk_text,
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
                # Also extract non-table prose from this section as a separate child
                _prose_lines = []
                for _line in section_text.split("\n"):
                    _stripped = _line.strip()
                    if not _stripped:
                        continue
                    if _stripped.count("|") >= 2:
                        continue  # skip table rows
                    if len(_stripped) > 30:  # meaningful prose, not just a heading
                        _prose_lines.append(_line)
                _prose_text = "\n".join(_prose_lines).strip()
                if len(_prose_text) > 100:
                    _prose_id = uuid4()
                    _prose_chunk = ContractChunkData(
                        chunk_id=_prose_id,
                        parent_id=parent_id,
                        is_parent=False,
                        chunk_type=CHUNK_TYPE_CLAUSE,
                        chunk_index=chunk_index,
                        text=_prose_text,
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
                    chunks.append(_prose_chunk)
                    chunk_index += 1
                continue
            else:
                # Fallback: table can't be parsed into rows — keep as single chunk
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

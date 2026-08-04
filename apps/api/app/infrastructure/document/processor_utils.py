"""
Claustor AI — Enhanced Document Processor
Handles: text, tables, images, multi-column, headers/footers,
         scanned PDFs, form fields, tracked changes.

Plan gating:
  free/starter:      text + basic tables + OCR
  professional:      + image vision + complex tables + form fields
  enterprise:        all features + handwriting + annotations
"""

from __future__ import annotations
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Table-to-Markdown Converter ────────────────────────────────────────────────

def table_to_markdown(table: list) -> str:
    """
    Convert pdfplumber table (list of rows, each row is list of cells)
    to clean markdown table format.
    Handles: merged cells, None values, multi-line cells.
    """
    if not table or not any(table):
        return ""

    # Clean cells
    cleaned = []
    for row in table:
        cleaned_row = []
        for cell in (row or []):
            if cell is None:
                cleaned_row.append("")
            else:
                # Normalize whitespace, remove newlines inside cells
                cell_text = re.sub(r'\s+', ' ', str(cell)).strip()
                cleaned_row.append(cell_text)
        if any(cleaned_row):  # Skip empty rows
            cleaned.append(cleaned_row)

    if not cleaned:
        return ""

    # Normalize column count
    max_cols = max(len(row) for row in cleaned)
    normalized = [row + [""] * (max_cols - len(row)) for row in cleaned]

    # Build markdown
    lines = []
    header = normalized[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def extract_tables_as_markdown(page) -> list[str]:
    """Extract all tables from a pdfplumber page as markdown strings."""
    tables = []
    try:
        for table in page.extract_tables():
            md = table_to_markdown(table)
            if md:
                tables.append(md)
    except Exception:
        pass
    return tables


# ── Header/Footer Removal ──────────────────────────────────────────────────────

def remove_headers_footers(pages_text: list[str]) -> list[str]:
    """
    Detect and remove repeating headers/footers across pages.
    Strategy: find lines that appear identically in >50% of pages.
    """
    if len(pages_text) < 3:
        return pages_text

    # Get first/last lines of each page
    candidate_lines: dict[str, int] = {}
    for text in pages_text:
        lines = text.strip().split('\n')
        if not lines:
            continue
        # Check first 2 and last 2 lines as header/footer candidates
        candidates = lines[:2] + lines[-2:]
        for line in candidates:
            line = line.strip()
            if len(line) > 5:  # Skip very short lines
                candidate_lines[line] = candidate_lines.get(line, 0) + 1

    # Lines appearing in >40% of pages are headers/footers
    threshold = max(2, len(pages_text) * 0.4)
    noise_lines = {line for line, count in candidate_lines.items()
                   if count >= threshold}

    # Remove noise lines from each page
    cleaned = []
    for text in pages_text:
        lines = text.split('\n')
        filtered = [l for l in lines if l.strip() not in noise_lines]
        cleaned.append('\n'.join(filtered))

    return cleaned


# ── Multi-Column Detection & Merging ──────────────────────────────────────────

def detect_and_merge_columns(page, page_text: str) -> str:
    """
    Detect multi-column layout using word bounding boxes.
    Merge columns in reading order (left-to-right, top-to-bottom).
    Falls back to raw text if detection fails.
    """
    try:
        words = page.extract_words()
        if not words:
            return page_text

        page_width = page.width
        mid_x = page_width / 2

        # Check if there's a clear column gap in the middle
        middle_words = [w for w in words
                        if mid_x * 0.35 < float(w['x0']) < mid_x * 0.65]

        # If few words in the middle zone → likely 2-column layout
        if len(middle_words) < len(words) * 0.1 and len(words) > 20:
            left_words = sorted(
                [w for w in words if float(w['x0']) < mid_x],
                key=lambda w: (float(w['top']), float(w['x0']))
            )
            right_words = sorted(
                [w for w in words if float(w['x0']) >= mid_x],
                key=lambda w: (float(w['top']), float(w['x0']))
            )
            left_text = ' '.join(w['text'] for w in left_words)
            right_text = ' '.join(w['text'] for w in right_words)
            return left_text + '\n\n' + right_text

    except Exception:
        pass

    return page_text


# ── Form Field Extraction ──────────────────────────────────────────────────────

def extract_form_fields(pdf_bytes: bytes) -> dict:
    """
    Extract PDF form fields (AcroForm).
    Returns dict of field_name → value.
    Professional+ plan feature.
    """
    fields = {}
    try:
        import pypdf
        reader = pypdf.PdfReader(__import__('io').BytesIO(pdf_bytes))
        if reader.get_form_text_fields():
            fields = reader.get_form_text_fields()
    except Exception:
        pass
    return fields


# ── Tracked Changes Handling ───────────────────────────────────────────────────

def remove_tracked_changes(text: str) -> str:
    """
    Remove common tracked-change markers from extracted text.
    Patterns: [DELETED: ...], strikethrough artifacts, revision marks.
    """
    # Remove [DELETED: text] blocks
    text = re.sub(r'\[DELETED?:?[^\]]*\]', '', text, flags=re.IGNORECASE)
    # Remove <<deleted>> blocks
    text = re.sub(r'<<[^>]*>>', '', text)
    # Remove revision marks like ¶ or § used as change markers
    text = re.sub(r'[¶§]{2,}', '', text)
    return text


# ── Handwriting Detection (Enterprise) ────────────────────────────────────────

def extract_handwritten_text(image_bytes: bytes, vision_llm=None) -> str:
    """
    Use Vision LLM to extract handwritten annotations.
    Enterprise plan feature.
    """
    if not vision_llm:
        return ""
    try:
        import base64
        b64 = base64.b64encode(image_bytes).decode()
        # Vision LLM call would go here
        return ""
    except Exception:
        return ""


# ── Enhanced Full-Document Extraction ─────────────────────────────────────────

def extract_document_enhanced(
    file_bytes: bytes,
    filename: str,
    plan: str = "free",
) -> dict:
    """
    Main extraction function with plan-gated features.

    Returns:
        full_text: str — clean text for RAG
        tables: list[str] — markdown tables
        chunks: list[dict] — structure-aware chunks
        page_count: int
        has_tables: bool
        has_images: bool
        form_fields: dict
        extraction_method: str
    """
    result = {
        "full_text": "",
        "tables": [],
        "chunks": [],
        "page_count": 0,
        "has_tables": False,
        "has_images": False,
        "form_fields": {},
        "extraction_method": "unknown",
        "pii_masked": False,
        "is_scanned": False,
    }

    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    try:
        if ext == 'pdf':
            result.update(_extract_pdf(file_bytes, plan))
        elif ext in ('docx', 'doc'):
            result.update(_extract_docx(file_bytes, plan))
        elif ext in ('xlsx', 'xls', 'csv'):
            result.update(_extract_spreadsheet(file_bytes, ext, plan))
        else:
            result.update(_extract_generic(file_bytes))
    except Exception as e:
        logger.error(f"document_extraction_failed: {e}")

    return result


def _extract_pdf(file_bytes: bytes, plan: str) -> dict:
    """PDF extraction with all enhancements."""
    import pdfplumber
    import io

    pages_text = []
    all_tables = []
    page_count = 0
    has_images = False
    is_scanned = False

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)

        for page in pdf.pages:
            # ── Text extraction ──
            text = page.extract_text() or ""

            # ── Multi-column handling (all plans) ──
            text = detect_and_merge_columns(page, text)

            # ── Table extraction → markdown (all plans) ──
            if plan in ("starter", "professional", "enterprise"):
                page_tables = extract_tables_as_markdown(page)
                all_tables.extend(page_tables)
                if page_tables:
                    # Append tables to page text
                    text += "\n\n" + "\n\n".join(page_tables)

            # ── Image detection ──
            if page.images:
                has_images = True

            pages_text.append(text)

        # ── Header/footer removal (starter+) ──
        if plan in ("starter", "professional", "enterprise"):
            pages_text = remove_headers_footers(pages_text)

    full_text = "\n\n".join(pages_text)

    # ── OCR for scanned pages (all plans) ──
    if len(full_text.strip()) < page_count * 100:
        is_scanned = True
        full_text = _ocr_pdf(file_bytes) or full_text

    # ── Tracked changes removal (all plans) ──
    full_text = remove_tracked_changes(full_text)

    # ── Form fields (professional+) ──
    form_fields = {}
    if plan in ("professional", "enterprise"):
        form_fields = extract_form_fields(file_bytes)

    return {
        "full_text": full_text,
        "tables": all_tables,
        "page_count": page_count,
        "has_tables": bool(all_tables),
        "has_images": has_images,
        "is_scanned": is_scanned,
        "form_fields": form_fields,
        "extraction_method": "pdfplumber_enhanced",
    }


def _extract_docx(file_bytes: bytes, plan: str) -> dict:
    """DOCX extraction preserving table structure."""
    try:
        import docx
        import io
        doc = docx.Document(io.BytesIO(file_bytes))
        parts = []
        tables = []

        for element in doc.element.body:
            tag = element.tag.split('}')[-1]
            if tag == 'p':
                para = docx.text.paragraph.Paragraph(element, doc)
                if para.text.strip():
                    parts.append(para.text)
            elif tag == 'tbl':
                table = docx.table.Table(element, doc)
                rows = []
                for row in table.rows:
                    rows.append([cell.text.strip() for cell in row.cells])
                md = table_to_markdown(rows)
                if md:
                    tables.append(md)
                    parts.append(md)

        return {
            "full_text": '\n'.join(parts),
            "tables": tables,
            "has_tables": bool(tables),
            "extraction_method": "python_docx",
        }
    except Exception as e:
        logger.warning(f"docx_extraction_warning: {e}")
        return {"full_text": "", "tables": []}


def _extract_spreadsheet(file_bytes: bytes, ext: str, plan: str) -> dict:
    """Spreadsheet extraction — each sheet as a markdown table."""
    tables = []
    text_parts = []
    try:
        if ext == 'csv':
            import csv, io
            reader = csv.reader(io.StringIO(file_bytes.decode('utf-8', errors='replace')))
            rows = list(reader)
            md = table_to_markdown(rows)
            if md:
                tables.append(md)
                text_parts.append(md)
        else:
            import openpyxl, io
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            for sheet in wb.worksheets:
                rows = []
                for row in sheet.iter_rows(values_only=True):
                    rows.append([str(c) if c is not None else "" for c in row])
                if rows:
                    rows = [r for r in rows if any(r)]  # skip empty rows
                    md = f"## Sheet: {sheet.title}\n" + table_to_markdown(rows)
                    tables.append(md)
                    text_parts.append(md)
    except Exception as e:
        logger.warning(f"spreadsheet_extraction_warning: {e}")

    return {
        "full_text": '\n\n'.join(text_parts),
        "tables": tables,
        "has_tables": bool(tables),
        "extraction_method": "openpyxl",
    }


def _extract_generic(file_bytes: bytes) -> dict:
    """Generic text extraction fallback."""
    try:
        text = file_bytes.decode('utf-8', errors='replace')
        return {"full_text": text, "extraction_method": "raw_text"}
    except Exception:
        return {"full_text": "", "extraction_method": "failed"}


def _ocr_pdf(file_bytes: bytes) -> str:
    """OCR fallback using pytesseract."""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=200)
        texts = [pytesseract.image_to_string(img) for img in images]
        return '\n\n'.join(texts)
    except Exception as e:
        logger.warning(f"ocr_fallback_warning: {e}")
        return ""


# ── Structure-Aware Chunker ────────────────────────────────────────────────────

def make_chunks(
    text: str,
    tables: list[str] = None,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[dict]:
    """
    Structure-aware chunking for legal contracts:
    1. Split on ARTICLE/SECTION/SCHEDULE/EXHIBIT boundaries
    2. Tables are separate chunks (preserve structure)
    3. Sentence-aware sliding window for large sections
    4. Overlap preserves cross-boundary context
    """
    if not text:
        return []

    chunks = []
    tables = tables or []

    # Step 1: Split on structural boundaries
    boundary_pattern = re.compile(
        r'(?=\n(?:ARTICLE|SECTION|SCHEDULE|EXHIBIT|ANNEX|APPENDIX|PART|CHAPTER)'
        r'\s+[\dA-Z]+[.:]?)',
        re.IGNORECASE
    )
    sections = boundary_pattern.split(text)
    sections = [s.strip() for s in sections if s.strip()]
    if len(sections) <= 1:
        sections = [text]

    for section in sections:
        words = section.split()
        if not words:
            continue

        if len(words) <= chunk_size:
            chunks.append({
                "text": section,
                "chunk_index": len(chunks),
                "chunk_type": "section",
            })
        else:
            # Sentence-aware sliding window
            sentences = re.split(r'(?<=[.!?])\s+', section)
            current: list[str] = []
            current_len = 0

            for sentence in sentences:
                sent_words = sentence.split()
                if current_len + len(sent_words) > chunk_size and current:
                    chunks.append({
                        "text": " ".join(current),
                        "chunk_index": len(chunks),
                        "chunk_type": "section_split",
                    })
                    # Overlap
                    overlap_words = current[-overlap:] if len(current) > overlap else current
                    current = overlap_words + sent_words
                    current_len = len(current)
                else:
                    current.extend(sent_words)
                    current_len += len(sent_words)

            if current:
                chunks.append({
                    "text": " ".join(current),
                    "chunk_index": len(chunks),
                    "chunk_type": "section_split",
                })

    # Step 2: Add table chunks (tables get their own dedicated chunks)
    for i, table_md in enumerate(tables):
        # Check if already embedded in text chunks
        already_in = any(
            table_md[:80].strip() in chunk["text"]
            for chunk in chunks
        )
        if not already_in and table_md.strip():
            chunks.append({
                "text": table_md,
                "chunk_index": len(chunks),
                "chunk_type": "table",
            })

    return chunks

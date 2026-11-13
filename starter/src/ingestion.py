"""Read and normalize source data."""
import unicodedata
import re
from pathlib import Path
import pypdf

from .models import DocumentPage


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without discarding useful structure."""
    if not text:
        return ""
    # Remove null bytes which cause PostgreSQL UTF8 encoding error
    text = text.replace("\x00", "")
    # NFC normalization
    text = unicodedata.normalize("NFC", text)
    # Replace non-breaking spaces
    text = text.replace("\u00a0", " ")
    # Replace tabs and irregular whitespace within lines
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)
    # Join lines and collapse 3+ newlines to 2 newlines
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def determine_metadata(page_num: int, text: str) -> dict:
    """Infer metadata such as section, topic, and component from page number and text."""
    text_lower = text.lower()

    # Section based on paper structure
    if page_num <= 4:
        section = "introduction"
    elif page_num <= 15:
        section = "system_design"
    elif page_num <= 24:
        section = "evaluation"
    else:
        section = "references"

    component = "general"
    if "trigger" in text_lower:
        component = "triggering"
    elif "selector" in text_lower or "selection" in text_lower:
        component = "data_selection"
    elif "storage" in text_lower or "retrieval" in text_lower:
        component = "storage"
    elif "evaluat" in text_lower:
        component = "evaluation"
    elif "trainer" in text_lower or "training" in text_lower:
        component = "trainer"

    return {
        "section": section,
        "topic": "ml_pipeline",
        "component": component,
        "page": page_num
    }


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical page; keep its page number, source, and metadata."""
    reader = pypdf.PdfReader(str(path))
    pages: list[DocumentPage] = []
    
    for idx, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        norm_text = normalize_text(raw_text)
        page_num = idx + 1
        meta = determine_metadata(page_num, norm_text)
        
        pages.append(DocumentPage(
            document_id=document_id,
            source=source,
            page=page_num,
            text=norm_text,
            metadata=meta
        ))
    return pages

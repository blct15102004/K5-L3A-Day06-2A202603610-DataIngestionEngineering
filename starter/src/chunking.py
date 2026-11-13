"""Implement fixed-size and structure-aware chunking."""
import re
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split text into overlapping fixed-size windows and retain page metadata."""
    text = page.text
    if not text:
        return []

    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunk_id = f"{page.document_id}_p{page.page}_fix_{idx:03d}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=dict(page.metadata)
            ))
            idx += 1
        if end >= len(text):
            break
        start += step

    return chunks


def by_paragraph(page: DocumentPage, max_size: int = 500) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs and retain metadata."""
    text = page.text
    if not text:
        return []

    # Split by double newlines or structural markers
    raw_paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not raw_paras:
        raw_paras = [p.strip() for p in text.split("\n") if p.strip()]

    chunks: list[Chunk] = []
    current_para_group: list[str] = []
    current_len = 0
    idx = 0

    def flush_group():
        nonlocal current_para_group, current_len, idx
        if current_para_group:
            grouped_text = "\n\n".join(current_para_group).strip()
            if grouped_text:
                chunk_id = f"{page.document_id}_p{page.page}_par_{idx:03d}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=grouped_text,
                    metadata=dict(page.metadata)
                ))
                idx += 1
            current_para_group = []
            current_len = 0

    for para in raw_paras:
        # If single paragraph is oversized, split it
        if len(para) > max_size:
            flush_group()
            # Split oversized paragraph by sentences
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", para) if s.strip()]
            sub_group: list[str] = []
            sub_len = 0
            for sent in sentences:
                if sub_len + len(sent) + 1 > max_size and sub_group:
                    chunk_text = " ".join(sub_group).strip()
                    chunk_id = f"{page.document_id}_p{page.page}_par_{idx:03d}"
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        document_id=page.document_id,
                        source=page.source,
                        page=page.page,
                        text=chunk_text,
                        metadata=dict(page.metadata)
                    ))
                    idx += 1
                    sub_group = [sent]
                    sub_len = len(sent)
                else:
                    sub_group.append(sent)
                    sub_len += len(sent) + 1
            if sub_group:
                chunk_text = " ".join(sub_group).strip()
                chunk_id = f"{page.document_id}_p{page.page}_par_{idx:03d}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata=dict(page.metadata)
                ))
                idx += 1
        else:
            if current_len + len(para) + 2 > max_size and current_para_group:
                flush_group()
            current_para_group.append(para)
            current_len += len(para) + 2

    flush_group()
    return chunks

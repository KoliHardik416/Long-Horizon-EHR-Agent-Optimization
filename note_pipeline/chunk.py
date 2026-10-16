"""Hierarchical section-aware chunking for clinical notes."""

from __future__ import annotations

import re

from .models import Note, NoteChunk, NoteSection
from .sections import split_sections


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _split_words(text: str, size: int, overlap: int) -> list[str]:
    words = _words(text)
    if len(words) <= size:
        return [text.strip()]
    step = max(1, size - overlap)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)
            if words[i:i + size]]


def _split_section(text: str, size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for paragraph in paragraphs or [text]:
        count = len(_words(paragraph))
        if current and current_words + count > size:
            chunks.extend(_split_words("\n\n".join(current), size, overlap))
            current, current_words = [], 0
        current.append(paragraph)
        current_words += count
    if current:
        chunks.extend(_split_words("\n\n".join(current), size, overlap))
    return chunks


def _embedding_text(section: NoteSection, text: str) -> str:
    encounter = f" Encounter: {section.hadm_id}." if section.hadm_id is not None else ""
    return (f"Document type: {section.note_type} note."
            f" Section: {section.section}.{encounter}\n\n{text}")


def chunk_section(section: NoteSection, chunk_size: int = 500,
                  chunk_overlap: int = 75) -> list[NoteChunk]:
    texts = _split_section(section.text, chunk_size, chunk_overlap)
    return [
        NoteChunk(
            chunk_id=f"{section.note_id}_{section.section_order:03d}_{i:03d}",
            parent_note_id=section.note_id, subject_id=section.subject_id,
            hadm_id=section.hadm_id, note_type=section.note_type,
            charttime=section.charttime, source_table=section.source_table,
            section=section.section, section_order=section.section_order,
            chunk_index=i, text=text, embedding_text=_embedding_text(section, text),
            iserror=section.iserror,
        ) for i, text in enumerate(texts)
    ]


def chunk_note(note: Note, chunk_size: int = 500,
               chunk_overlap: int = 75) -> list[NoteChunk]:
    """Return child chunks while retaining section and note hierarchy."""
    chunks: list[NoteChunk] = []
    for section in split_sections(note):
        chunks.extend(chunk_section(section, chunk_size, chunk_overlap))
    return chunks


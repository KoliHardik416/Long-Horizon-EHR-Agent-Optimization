"""Data models used by the MIMIC-IV-Note chunking pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Note:
    note_id: str
    subject_id: int
    hadm_id: int | None
    note_type: str
    charttime: datetime | None
    text: str
    source_table: str
    iserror: str | None = None


@dataclass(frozen=True)
class NoteSection:
    note_id: str
    subject_id: int
    hadm_id: int | None
    note_type: str
    charttime: datetime | None
    source_table: str
    section: str
    section_order: int
    text: str
    iserror: str | None = None


@dataclass(frozen=True)
class NoteChunk:
    chunk_id: str
    parent_note_id: str
    subject_id: int
    hadm_id: int | None
    note_type: str
    charttime: datetime | None
    source_table: str
    section: str
    section_order: int
    chunk_index: int
    text: str
    embedding_text: str
    iserror: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


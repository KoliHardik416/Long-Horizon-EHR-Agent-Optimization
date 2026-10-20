"""Clinical-section detection and normalization for MIMIC note text."""

from __future__ import annotations

import re

from .models import Note, NoteSection


_KNOWN = {
    "admission date", "discharge date", "date of birth", "chief complaint",
    "history of present illness", "past medical history", "past surgical history",
    "social history", "family history", "allergies", "medications",
    "physical exam", "physical examination", "hospital course", "procedures",
    "discharge diagnosis", "discharge diagnoses", "disposition", "follow-up",
    "clinical history", "comparison", "technique", "findings", "impression",
}


def normalize_heading(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9 /&-]+", "", value).strip(" -:")
    return re.sub(r"\s+", " ", value).title() or "Unsectioned"


def is_heading(line: str) -> bool:
    candidate = line.strip().strip(":")
    if not candidate or len(candidate) > 90 or candidate.endswith((".", ";")):
        return False
    normalized = re.sub(r"\s+", " ", candidate.lower())
    if normalized in _KNOWN:
        return True
    # Common note headings are short, standalone uppercase lines.
    return len(candidate.split()) <= 8 and candidate.isupper() and any(c.isalpha() for c in candidate)


def split_sections(note: Note) -> list[NoteSection]:
    """Split a note into ordered sections, retaining all non-heading text."""
    sections: list[tuple[str, list[str]]] = []
    current_name = "Unsectioned"
    current_lines: list[str] = []
    for line in note.text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if is_heading(line):
            if "\n".join(current_lines).strip():
                sections.append((current_name, current_lines))
            current_name = normalize_heading(line)
            current_lines = []
        else:
            current_lines.append(line)
    if "\n".join(current_lines).strip() or not sections:
        sections.append((current_name, current_lines))

    return [NoteSection(
        note_id=note.note_id, subject_id=note.subject_id, hadm_id=note.hadm_id,
        note_type=note.note_type, charttime=note.charttime,
        source_table=note.source_table, section=name, section_order=i,
        text="\n".join(lines).strip(), iserror=note.iserror,
    ) for i, (name, lines) in enumerate(sections) if "\n".join(lines).strip()]


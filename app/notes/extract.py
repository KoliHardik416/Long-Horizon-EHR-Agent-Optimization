"""Extract source notes and detail sections from the MIMIC PostgreSQL schema."""

from __future__ import annotations

from collections.abc import Iterator

from .models import Note


NOTE_TABLES = {
    "discharge": "mimiciv_note.discharge",
    "radiology": "mimiciv_note.radiology",
}


def iter_notes(conn, note_type: str | None = None,
               subject_id: int | None = None) -> Iterator[Note]:
    """Yield notes from PostgreSQL; filters are parameterized."""
    tables = NOTE_TABLES.items() if note_type is None else [(note_type, NOTE_TABLES[note_type])]
    for kind, table in tables:
        params: list[object] = []
        where = ""
        if subject_id is not None:
            where = "WHERE subject_id = %s"
            params.append(subject_id)
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT note_id, subject_id, hadm_id, note_type, charttime, text
                FROM {table}
                {where}
                ORDER BY subject_id, charttime, note_id
            """, params)
            for row in cur.fetchall():
                yield Note(note_id=row["note_id"], subject_id=row["subject_id"],
                           hadm_id=row["hadm_id"], note_type=row["note_type"],
                           charttime=row["charttime"], text=row["text"],
                           source_table=table)


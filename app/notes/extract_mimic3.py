"""Extract MIMIC-III NOTEEVENTS rows as note-pipeline documents."""

from __future__ import annotations

from collections.abc import Iterator

from .models import Note


def iter_mimic3_notes(conn, subject_id: int | None = None,
                      hadm_id: int | None = None) -> Iterator[Note]:
    clauses: list[str] = []
    params: list[object] = []
    if subject_id is not None:
        clauses.append("subject_id = %s"); params.append(subject_id)
    if hadm_id is not None:
        clauses.append("hadm_id = %s"); params.append(hadm_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT row_id, subject_id, hadm_id, chartdate, charttime,
                   category, iserror, text
            FROM mimiciii.noteevents
            {where}
            ORDER BY subject_id, charttime NULLS LAST, row_id
        """, params)
        for row in cur.fetchall():
            yield Note(
                note_id=str(row["row_id"]), subject_id=row["subject_id"],
                hadm_id=row["hadm_id"], note_type=row["category"] or "unknown",
                charttime=row["charttime"] or row["chartdate"],
                text=row["text"] or "", source_table="mimiciii.noteevents",
                iserror=row["iserror"],
            )


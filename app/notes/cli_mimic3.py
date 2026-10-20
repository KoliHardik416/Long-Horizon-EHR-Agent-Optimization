"""Build JSONL chunks from MIMIC-III NOTEEVENTS."""

from __future__ import annotations

import argparse

from app.retrieval.connection import connect

from .chunk import chunk_note
from .export import write_jsonl
from .extract_mimic3 import iter_mimic3_notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--subject-id", type=int)
    parser.add_argument("--hadm-id", type=int)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=75)
    args = parser.parse_args()
    with connect() as conn:
        chunks = (chunk for note in iter_mimic3_notes(conn, args.subject_id, args.hadm_id)
                  for chunk in chunk_note(note, args.chunk_size, args.chunk_overlap))
        print(f"Wrote {write_jsonl(chunks, args.output)} chunks to {args.output}")


if __name__ == "__main__":
    main()


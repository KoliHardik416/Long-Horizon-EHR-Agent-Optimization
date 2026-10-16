"""Build inspectable JSONL chunks from MIMIC-IV-Note PostgreSQL tables."""

from __future__ import annotations

import argparse

from structured_retrieval.connection import connect

from .chunk import chunk_note
from .export import write_jsonl
from .extract import iter_notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="Output JSONL path")
    parser.add_argument("--note-type", choices=["discharge", "radiology"])
    parser.add_argument("--subject-id", type=int)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=75)
    args = parser.parse_args()
    chunks = (chunk for note in _notes(args) for chunk in chunk_note(
        note, args.chunk_size, args.chunk_overlap))
    print(f"Wrote {write_jsonl(chunks, args.output)} chunks to {args.output}")


def _notes(args):
    with connect() as conn:
        yield from iter_notes(conn, args.note_type, args.subject_id)


if __name__ == "__main__":
    main()


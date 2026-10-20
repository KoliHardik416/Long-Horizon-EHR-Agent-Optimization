"""Export chunk records as JSONL for inspection or later indexing."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .models import NoteChunk


def write_jsonl(chunks: Iterable[NoteChunk], output: str | Path) -> int:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.as_dict(), default=str, ensure_ascii=False) + "\n")
            count += 1
    return count


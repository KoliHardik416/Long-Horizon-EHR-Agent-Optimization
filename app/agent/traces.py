"""JSONL persistence for trajectory data used in evaluation and training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")

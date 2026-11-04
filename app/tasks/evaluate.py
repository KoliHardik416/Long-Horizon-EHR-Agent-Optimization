"""Small deterministic evaluation-suite builders."""

from __future__ import annotations

from typing import Any

from .generate import generate_tasks


ATOMIC_TASK_TYPES = ("labs", "admission", "medications", "diagnoses", "procedures")


def build_atomic_suite(subject_id: int, hadm_id: int | None = None,
                       split: str | None = "validation") -> list[dict[str, Any]]:
    """Build the five atomic evaluation tasks in stable order."""
    return generate_tasks(
        [subject_id],
        hadm_id=hadm_id,
        task_types=ATOMIC_TASK_TYPES,
        split=split,
    )

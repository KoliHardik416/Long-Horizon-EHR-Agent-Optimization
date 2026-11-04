"""Dependency-aware, adaptive evidence-plan utilities."""

from __future__ import annotations

from typing import Any


def ready_steps(task: dict[str, Any], completed: set[str], started: set[str] | None = None) -> list[dict[str, Any]]:
    """Return independent plan steps whose dependencies are satisfied."""
    started = started or set()
    ready = []
    for step in task.get("evidence_plan", []):
        step_id = step["step_id"]
        if step_id not in started and set(step.get("depends_on", [])) <= completed:
            ready.append(step)
    return ready


def plan_limits(task: dict[str, Any]) -> dict[str, int]:
    """Return bounded execution limits for adaptive exploration."""
    required = sum(1 for step in task.get("evidence_plan", []) if step.get("required", True))
    return {
        "required_steps": required,
        "max_extra_calls": int(task.get("execution", {}).get("max_extra_calls", 2)),
    }

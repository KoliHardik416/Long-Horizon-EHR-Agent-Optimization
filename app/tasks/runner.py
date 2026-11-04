"""Run formal task contracts through the bounded local EHR agent."""

from __future__ import annotations

from typing import Any

from app.agent.agent import LocalEHRAgent
from .answers import ground_task


def run_task(agent: LocalEHRAgent, task: dict[str, Any]) -> dict[str, Any]:
    """Execute a formal task while passing its contract to the controller."""
    return agent.run(
        task["question"],
        subject_id=task["scope"]["subject_id"],
        hadm_id=task["scope"].get("target_hadm_id"),
        task_contract=task,
    )


def run_grounded_task(agent: LocalEHRAgent, task: dict[str, Any], retriever=None) -> dict[str, Any]:
    """Ground a task, then execute it through the local recursive agent."""
    grounded = ground_task(task, retriever=retriever)
    result = run_task(agent, grounded)
    result["task"] = grounded
    return result

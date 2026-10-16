"""Deterministic baseline quality scoring for orchestration traces."""

from __future__ import annotations

from typing import Any


def score_trajectory(trace: dict[str, Any]) -> dict[str, Any]:
    events, tools = trace.get("events", []), trace.get("tool_calls", [])
    final = trace.get("final_answer", {})
    answer = final.get("answer", "") if isinstance(final, dict) else ""
    failures: list[str] = []
    if not tools:
        failures.append("no_tool_calls")

    if not answer:
        failures.append("empty_final_answer")

    delegation_count = sum(1 for e in events if e.get("event") == "task_started" and e.get("task", {}).get("parent_task_id"))
    
    if delegation_count > 5:
        failures.append("excessive_delegation")
        
    grounded = 1.0 if tools and answer else 0.0
    overall = max(0.0, grounded - min(len(tools) / 20.0, 0.25))
    return {"plan_score": 1.0 if events else 0.0, "trajectory_score": grounded,
            "answer_score": grounded, "overall_score": round(overall, 4),
            "failure_labels": failures, "tool_call_count": len(tools),
            "delegation_count": delegation_count}

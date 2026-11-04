"""Convert legacy LocalEHRAgent traces to the formal trajectory format."""

from __future__ import annotations

from typing import Any


def _row_reference(row: dict[str, Any]) -> dict[str, Any] | None:
    source = row.get("source")
    if not source:
        return None
    keys = ("row_id", "labevent_id", "note_id", "itemid", "subject_id", "hadm_id",
            "icustay_id", "stay_id", "charttime", "chartdate", "seq_num")
    identifiers = {key: row[key] for key in keys if key in row and row[key] is not None}
    return {"source": source, "identifiers": identifiers}


def _evidence_references(value: Any) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    if isinstance(value, list):
        for row in value:
            if isinstance(row, dict):
                ref = _row_reference(row)
                if ref:
                    references.append(ref)
    elif isinstance(value, dict):
        for nested in value.values():
            references.extend(_evidence_references(nested))
    return references


def _summary(value: Any) -> str:
    if isinstance(value, list):
        return f"Retrieved {len(value)} record(s)."
    if isinstance(value, dict):
        if "error" in value:
            return f"Retrieval error: {value['error'].get('message', 'unknown error')}"
        return "Retrieved structured patient context."
    return str(value)


def trace_to_trajectory(trace: dict[str, Any], task: dict[str, Any], model: str) -> dict[str, Any]:
    """Convert an agent trace into a schema-shaped trajectory record."""
    evidence_by_tool: dict[str, Any] = {}
    tree = trace.get("task_tree", {})

    def collect(node: dict[str, Any]) -> None:
        for tool, value in (node.get("evidence") or {}).items():
            evidence_by_tool[tool] = value
        for child in node.get("children", []) or []:
            collect(child)

    if isinstance(tree, dict):
        collect(tree)

    steps: list[dict[str, Any]] = []
    for child in (tree.get("children", []) if isinstance(tree, dict) else []) or []:
        steps.append({
            "action": "delegation",
            "task_id": child.get("task_id", ""),
            "objective": (child.get("report") or {}).get("objective", "delegated task"),
        })
    for call in trace.get("tool_calls", []):
        tool = call.get("name")
        observation = evidence_by_tool.get(tool, [])
        steps.append({
            "action": "tool_call",
            "tool": tool,
            "arguments": call.get("arguments", {}),
            "observation": {
                "summary": _summary(observation),
                "evidence_references": _evidence_references(observation),
            },
        })

    final = trace.get("final_answer", {})
    answer = final.get("answer", "") if isinstance(final, dict) else str(final or "")
    steps.append({"action": "final_answer", "observation": {
        "summary": answer, "evidence_references": [],
    }})

    quality = trace.get("quality", {})
    return {
        "schema_version": 1,
        "task_id": task["task_id"],
        "model": model,
        "steps": steps,
        "final_answer": answer,
        "validation": {
            "answer_correct": bool(answer),
            "evidence_grounded": bool(trace.get("tool_calls")),
            "tool_calls_valid": not bool(quality.get("failure_labels")),
            "errors": list(quality.get("failure_labels", [])),
        },
    }

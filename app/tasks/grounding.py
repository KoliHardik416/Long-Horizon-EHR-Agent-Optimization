"""Build bounded, provenance-preserving grounding packets for task steps."""

from __future__ import annotations

from typing import Any

from app.retrieval import MIMICIIIRetriever, StructuredRetriever

from .answers import _identifiers, _rows_for_tool
from .plan import ready_steps


def _references(rows: list[dict[str, Any]], expected_sources: list[str]) -> list[dict[str, Any]]:
    references = []
    for row in rows:
        source = row.get("source") or (expected_sources[0] if expected_sources else None)
        identifiers = _identifiers(row)
        if source and identifiers:
            references.append({"source": source, "identifiers": identifiers})
    return references


def _default_retriever(task: dict[str, Any]):
    return MIMICIIIRetriever() if task["dataset"] == "mimic-iii" else StructuredRetriever()


def build_grounding_packets(task: dict[str, Any], retriever=None) -> list[dict[str, Any]]:
    """Execute the task evidence plan and return one packet per plan step."""
    retriever = retriever or _default_retriever(task)
    scope = task["scope"]
    base_arguments = {"subject_id": scope["subject_id"]}
    if scope.get("target_hadm_id") is not None:
        base_arguments["hadm_id"] = scope["target_hadm_id"]
    packets: list[dict[str, Any]] = []
    completed: set[str] = set()
    started: set[str] = set()
    while len(completed) < len(task["evidence_plan"]):
        available = ready_steps(task, completed, started)
        if not available:
            raise ValueError("evidence_plan has an unsatisfied dependency or cycle")
        for step in available:
            started.add(step["step_id"])
        arguments = {**base_arguments, **(step.get("arguments") or {})}
        packet = {
            "step_id": step["step_id"],
            "objective": step["objective"],
            "allowed_tools": step["allowed_tools"],
            "depends_on": step["depends_on"],
            "expected_sources": step["expected_sources"],
            "arguments": arguments,
            "records": [],
            "evidence_references": [],
            "error": None,
        }
        try:
            tool = step["allowed_tools"][0]
            if tool == "patient_context":
                result = retriever.patient_context(**arguments)
            else:
                result = getattr(retriever, tool)(**arguments, limit=100)
            rows = _rows_for_tool(tool, result)
            packet["records"] = rows
            packet["evidence_references"] = _references(rows, step["expected_sources"])
        except Exception as exc:
            packet["error"] = {"type": "retrieval_error", "message": str(exc)}
        packets.append(packet)
        completed.add(step["step_id"])
    return packets

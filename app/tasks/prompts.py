"""Local-only prompt construction for the formal task pipeline."""

from __future__ import annotations

import json
from typing import Any


CONTROLLER_SYSTEM = """You are a local EHR task controller. Follow the supplied evidence plan.
Run only allowed tools, respect dependencies and patient scope, and never invent IDs.
Return JSON only with: next_step_id, action, reason."""

WORKER_SYSTEM = """You are a local EHR evidence worker. Analyze only the supplied grounding packet.
Every factual finding must cite an evidence reference. Distinguish documented facts,
computed patterns, and uncertainty. Do not diagnose or recommend treatment.
Return JSON only with findings, evidence_references, and uncertainties."""

SYNTHESIS_SYSTEM = """You are a local EHR answer synthesizer. Answer the task using only worker findings
and evidence references. Satisfy the success criteria, avoid unsupported causal claims,
and state when information is not documented. Return JSON only with answer, findings,
and uncertainties."""


def _content(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False, indent=2)


def controller_messages(task: dict[str, Any], packets: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": CONTROLLER_SYSTEM},
        {"role": "user", "content": _content({
            "task": task,
            "evidence_plan": task["evidence_plan"],
            "grounding_packets": packets,
        })},
    ]


def worker_messages(task: dict[str, Any], step: dict[str, Any], packet: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": WORKER_SYSTEM},
        {"role": "user", "content": _content({
            "question": task["question"],
            "scope": task["scope"],
            "step": step,
            "grounding_packet": packet,
            "success_criteria": task["success_criteria"],
        })},
    ]


def synthesis_messages(task: dict[str, Any], worker_reports: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYNTHESIS_SYSTEM},
        {"role": "user", "content": _content({
            "question": task["question"],
            "scope": task["scope"],
            "success_criteria": task["success_criteria"],
            "worker_reports": worker_reports,
        })},
    ]

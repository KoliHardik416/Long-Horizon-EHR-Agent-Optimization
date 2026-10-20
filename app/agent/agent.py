"""Bounded recursive controller/worker orchestration for EHR analysis."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from .evaluation import score_trajectory
from .model import LocalHFModel
from .tools import EHRToolRegistry, TOOL_SCHEMAS

CONTROLLER_SYSTEM = """You are the controller for a de-identified EHR assistant.
Choose execute when one bounded task can answer the request. Choose delegate only
when independent subtasks materially improve the answer. Return JSON only:
{\"decision\":\"execute\"|\"delegate\",\"reason\":string,\"tool_calls\":[{\"name\":string,\"arguments\":object}],\"subtasks\":[...]}
For subtasks use {\"task_id\":string,\"role\":\"worker\"|\"controller\",\"objective\":string,
\"allowed_tools\":[string],\"arguments\":object}. Never invent patient IDs.
"""
WORKER_SYSTEM = """You are a scoped EHR worker. Use only the task contract and evidence
provided. Return JSON only: {\"findings\":[],\"uncertainties\":[],\"evidence_references\":[]}.
Do not diagnose or recommend treatment. Preserve dates, units, and source identifiers.
"""
SYNTHESIS_SYSTEM = """You are the controller synthesizing an EHR analysis. Use only the
worker reports and evidence references. Distinguish documented facts, computed
patterns, interpretation, and uncertainty. Do not diagnose or recommend treatment.
Return JSON only: {\"answer\":string,\"findings\":[],\"uncertainties\":[]}.
"""


@dataclass
class TaskNode:
    task_id: str
    objective: str
    role: str = "controller"
    parent_task_id: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    arguments: dict[str, Any] = field(default_factory=dict)
    depth: int = 0
    can_delegate: bool = True


class LocalEHRAgent:
    def __init__(self, model: LocalHFModel, tools: EHRToolRegistry | None = None,
                 max_depth: int = 2, max_children: int = 5, max_calls: int = 12):
        self.model, self.tools = model, tools or EHRToolRegistry()
        self.max_depth, self.max_children, self.max_calls = max_depth, max_children, max_calls
        self.trace: dict[str, Any] = {"events": [], "tool_calls": [], "model_calls": []}
        self._calls = 0

    def _model_json(self, role: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        if self._calls >= self.max_calls:
            raise RuntimeError("maximum model-call budget exceeded")
        started = time.perf_counter()
        self._calls += 1
        result = self.model.generate_json(messages)
        self.trace["model_calls"].append({"role": role, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)})
        return result

    def _make_node(self, raw: dict[str, Any], parent: TaskNode | None) -> TaskNode:
        depth = 0 if parent is None else parent.depth + 1
        role = raw.get("role", "worker")
        if role not in {"worker", "controller"}:
            raise ValueError(f"invalid task role: {role}")
        if depth > self.max_depth:
            raise RuntimeError("maximum recursion depth exceeded")
        return TaskNode(
            task_id=str(raw.get("task_id") or raw.get("id") or uuid.uuid4().hex[:8]),
            objective=str(raw.get("objective") or raw.get("question") or ""), role=role,
            parent_task_id=parent.task_id if parent else None,
            allowed_tools=list(raw.get("allowed_tools") or raw.get("tools") or []),
            arguments=dict(raw.get("arguments") or {}), depth=depth,
            can_delegate=role == "controller" and depth < self.max_depth,
        )

    def _execute_tools(self, node: TaskNode, names: list[str] | None = None) -> dict[str, Any]:
        requested = names or node.allowed_tools
        evidence: dict[str, Any] = {}
        for name in requested:
            if name not in node.allowed_tools:
                raise ValueError(f"task {node.task_id} is not allowed to call {name}")
            evidence[name] = self.tools.call(name, node.arguments)
            self.trace["tool_calls"].append({"task_id": node.task_id, "name": name, "arguments": node.arguments})
        return evidence

    def _worker(self, node: TaskNode, request: str) -> dict[str, Any]:
        evidence = self._execute_tools(node)
        context = {"root_request": request, "task": asdict(node), "evidence": evidence}
        report = self._model_json("worker", [{"role": "system", "content": WORKER_SYSTEM},
                                               {"role": "user", "content": json.dumps(context, default=str)}])
        return {"task_id": node.task_id, "role": "worker", "report": report}

    def _controller(self, node: TaskNode, request: str) -> dict[str, Any]:
        prompt = {"root_request": request, "task": asdict(node), "tools": TOOL_SCHEMAS}
        decision = self._model_json("controller", [{"role": "system", "content": CONTROLLER_SYSTEM},
                                                     {"role": "user", "content": json.dumps(prompt, default=str)}])
        mode = decision.get("decision", decision.get("mode", "execute"))
        if mode == "decompose":
            mode = "delegate"
        if mode == "execute":
            names = [call["name"] for call in decision.get("tool_calls", [])]
            if not names:
                raise ValueError("controller execute decision must include tool_calls")
            return {"task_id": node.task_id, "role": node.role, "evidence": self._execute_tools(node, names), "decision": decision}
        if mode != "delegate" or not node.can_delegate:
            raise ValueError(f"invalid or disallowed controller decision: {mode}")
        raw_children = decision.get("subtasks", [])
        if not raw_children or len(raw_children) > self.max_children:
            raise ValueError("controller returned an invalid number of subtasks")
        children, seen = [], set()
        for raw in raw_children:
            child = self._make_node(raw, node)
            if child.task_id in seen:
                raise ValueError(f"duplicate task id: {child.task_id}")
            seen.add(child.task_id)
            children.append(self._run_node(child, request))
        return {"task_id": node.task_id, "role": "controller", "decision": decision, "children": children}

    def _run_node(self, node: TaskNode, request: str) -> dict[str, Any]:
        self.trace["events"].append({"event": "task_started", "task": asdict(node)})
        result = self._worker(node, request) if node.role == "worker" else self._controller(node, request)
        self.trace["events"].append({"event": "task_finished", "task_id": node.task_id})
        return result

    def run(self, request: str, subject_id: int, hadm_id: int | None = None) -> dict[str, Any]:
        root = TaskNode("root", request, allowed_tools=[tool["name"] for tool in TOOL_SCHEMAS],
                        arguments={"subject_id": subject_id, "hadm_id": hadm_id})
        tree = self._run_node(root, request)
        reports = tree.get("children", [tree])
        synthesis = self._model_json("synthesis", [{"role": "system", "content": SYNTHESIS_SYSTEM},
                                                     {"role": "user", "content": json.dumps({"request": request, "reports": reports}, default=str)}])
        self.trace.update({"request": request, "task_tree": tree, "final_answer": synthesis})
        self.trace["quality"] = score_trajectory(self.trace)
        return {"answer": synthesis, "trace": self.trace}

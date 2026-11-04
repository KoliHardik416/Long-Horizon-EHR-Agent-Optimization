"""Deterministic validation for formal tasks and agent trajectories."""

from __future__ import annotations

from typing import Any


TOOLS = {"patient_context", "admissions", "labs", "medications", "diagnoses", "procedures", "notes"}


def _result(valid: bool, errors: list[str], checks: dict[str, bool]) -> dict[str, Any]:
    return {"valid": valid, "errors": errors, "checks": checks}


def validate_task(task: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = {"schema_version", "task_id", "dataset", "question", "scope",
                "evidence_plan", "success_criteria"}
    missing = sorted(required - set(task))
    if missing:
        errors.append(f"missing task fields: {', '.join(missing)}")
    if task.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if task.get("dataset") not in {"mimic-iii", "mimic-iv"}:
        errors.append("dataset must be mimic-iii or mimic-iv")
    scope = task.get("scope", {})
    if not isinstance(scope.get("subject_id"), int) or scope.get("subject_id", 0) <= 0:
        errors.append("subject_id must be a positive integer")
    tools = task.get("required_tools")
    if tools is not None and (not isinstance(tools, list) or any(tool not in TOOLS for tool in tools)):
        errors.append("required_tools must contain only supported tools")
    complexity = task.get("complexity")
    if complexity is not None and isinstance(complexity, dict):
        components = ("retrieval", "reasoning", "temporal", "integration")
        if complexity.get("total") != sum(complexity.get(key, 0) for key in components):
            errors.append("complexity.total must equal the component sum")
    elif complexity is not None:
        errors.append("complexity must be an object")
    plan = task.get("evidence_plan", [])
    step_ids = {step.get("step_id") for step in plan}
    if not plan or len(step_ids) != len(plan):
        errors.append("evidence_plan must contain unique steps")
    for step in plan:
        if any(dep not in step_ids for dep in step.get("depends_on", [])):
            errors.append(f"evidence step {step.get('step_id')} has an unknown dependency")
    for reference in task.get("reference_evidence", []) or []:
        if not reference.get("source", "").startswith(("mimiciii.", "mimiciv_")):
            errors.append("reference evidence has an invalid source")
        if not reference.get("identifiers"):
            errors.append("reference evidence must include identifiers")
    return _result(not errors, errors, {
        "required_fields": not missing,
        "supported_tools": tools is None or all(tool in TOOLS for tool in tools),
        "complexity_consistent": complexity is None or not any("complexity.total" in error for error in errors),
        "evidence_references_valid": not any("reference evidence" in error for error in errors),
    })


def validate_trajectory(task: dict[str, Any], trajectory: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    steps = trajectory.get("steps", [])
    tool_steps = [step for step in steps if step.get("action") == "tool_call"]
    called_tools = {step.get("tool") for step in tool_steps}
    required_tools = set(task.get("required_tools") or {
        tool for step in task.get("evidence_plan", []) for tool in step.get("allowed_tools", [])
    })
    missing_tools = required_tools - called_tools
    if trajectory.get("schema_version") != 1:
        errors.append("trajectory schema_version must be 1")
    if trajectory.get("task_id") != task.get("task_id"):
        errors.append("trajectory task_id does not match task")
    if not trajectory.get("final_answer"):
        errors.append("trajectory final_answer is empty")
    if missing_tools:
        errors.append(f"required tools not called: {', '.join(sorted(missing_tools))}")
    invalid_tools = called_tools - TOOLS
    if invalid_tools:
        errors.append(f"unsupported tools called: {', '.join(sorted(invalid_tools))}")

    task_sources = {ref.get("source") for ref in task.get("reference_evidence", [])}
    observed_sources = {
        ref.get("source")
        for step in tool_steps
        for ref in step.get("observation", {}).get("evidence_references", [])
    }
    if task_sources and not task_sources.intersection(observed_sources):
        errors.append("trajectory observations do not contain task reference evidence sources")

    plan_by_id = {step.get("step_id"): step for step in task.get("evidence_plan", [])}
    expected_steps = set(task.get("success_criteria", {}).get("required_evidence_steps", []))
    delegated = {step.get("task_id") for step in steps if step.get("action") == "delegation"}
    covered_steps = set(delegated)
    for step_id, plan_step in plan_by_id.items():
        if any(tool in called_tools for tool in plan_step.get("allowed_tools", [])):
            covered_steps.add(step_id)
    missing_steps = expected_steps - covered_steps
    if missing_steps:
        errors.append(f"required evidence steps not covered: {', '.join(sorted(missing_steps))}")
    requires_recursion = any(plan_step.get("depends_on") for plan_step in plan_by_id.values())
    if requires_recursion and not delegated:
        errors.append("dependency-aware task did not delegate any evidence step")

    checks = {
        "schema_version_valid": trajectory.get("schema_version") == 1,
        "task_id_matches": trajectory.get("task_id") == task.get("task_id"),
        "required_tools_called": not missing_tools,
        "tool_calls_supported": not invalid_tools,
        "evidence_plan_covered": not missing_steps,
        "recursive_delegation_present": not requires_recursion or bool(delegated),
        "evidence_present": bool(observed_sources),
        "final_answer_present": bool(trajectory.get("final_answer")),
    }
    return _result(not errors, errors, checks)

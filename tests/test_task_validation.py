from app.tasks import generate_task, validate_task, validate_trajectory


def test_task_validation_accepts_generated_task():
    result = validate_task(generate_task(1599, 100945, "integrated"))
    assert result["valid"] is True


def test_task_validation_rejects_inconsistent_complexity():
    task = generate_task(1599, 100945, "labs")
    task["complexity"]["total"] = 99
    result = validate_task(task)
    assert result["valid"] is False
    assert "complexity.total" in result["errors"][0]


def test_trajectory_validation_requires_all_tools_and_evidence_steps():
    task = generate_task(1599, 100945, "integrated")
    trajectory = {
        "schema_version": 1,
        "task_id": task["task_id"],
        "model": "test",
        "steps": [{
            "action": "tool_call",
            "tool": "labs",
            "arguments": {"subject_id": 1599},
            "observation": {
                "summary": "Retrieved 1 record.",
                "evidence_references": [{"source": "mimiciii.labevents", "identifiers": {"row_id": 1}}],
            },
        }],
        "final_answer": "A grounded answer.",
        "validation": {"answer_correct": True, "evidence_grounded": True, "tool_calls_valid": True},
    }
    result = validate_trajectory(task, trajectory)
    assert result["valid"] is False
    assert any("required tools" in error for error in result["errors"])
    assert any("evidence steps" in error for error in result["errors"])

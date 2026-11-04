from app.tasks.generate import generate_task, generate_tasks


def test_task_generation_is_deterministic():
    first = generate_task(1599, 100945, "labs")
    second = generate_task(1599, 100945, "labs")
    assert first == second
    assert first["task_id"] == "mimiciii-1599-100945-labs-001"
    assert first["reference_answer"] is None
    assert first["reference_evidence"] == []


def test_integrated_template_declares_required_tools():
    task = generate_task(1599, 100945, "integrated")
    assert task["difficulty"] == "hard"
    assert set(task["required_tools"]) == {
        "patient_context", "admissions", "labs", "medications",
        "diagnoses", "procedures", "notes",
    }
    assert len(task["evidence_plan"]) == 4
    assert task["evidence_plan"][0]["arguments"] == {"subject_id": 1599, "hadm_id": 100945}


def test_batch_generation_preserves_input_and_template_order():
    tasks = generate_tasks([1599, 1600], task_types=("labs", "notes"))
    assert [task["scope"]["subject_id"] for task in tasks] == [1599, 1599, 1600, 1600]
    assert [task["required_tools"] for task in tasks] == [["labs"], ["notes"], ["labs"], ["notes"]]


def test_invalid_task_inputs_are_rejected():
    try:
        generate_task(0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected invalid subject_id to fail")

from app.tasks import build_atomic_suite, validate_task


def test_atomic_suite_contains_five_deterministic_tasks():
    suite = build_atomic_suite(1599, 100945)
    assert len(suite) == 5
    assert [task["required_tools"] for task in suite] == [
        ["labs"], ["patient_context", "admissions"], ["medications"],
        ["diagnoses"], ["procedures"],
    ]
    assert all("evidence_plan" in task for task in suite)
    assert all(validate_task(task)["valid"] for task in suite)


def test_atomic_suite_is_reproducible():
    assert build_atomic_suite(1599, 100945) == build_atomic_suite(1599, 100945)

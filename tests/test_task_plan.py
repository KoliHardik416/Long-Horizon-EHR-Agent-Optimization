from app.tasks import generate_task, plan_limits, ready_steps


def test_independent_steps_are_ready_and_dependent_steps_wait():
    task = generate_task(1599, 100945, "integrated")
    first = ready_steps(task, set())
    assert [step["step_id"] for step in first] == ["admission-context"]
    second = ready_steps(task, {"admission-context"}, {"admission-context"})
    assert {step["step_id"] for step in second} == {"laboratory-trends", "treatments", "clinical-narrative"}


def test_execution_limits_are_bounded_and_explicit():
    task = generate_task(1599, 100945, "labs")
    assert plan_limits(task) == {"required_steps": 1, "max_extra_calls": 2}

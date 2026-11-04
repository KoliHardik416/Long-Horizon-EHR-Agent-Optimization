from app.tasks import controller_messages, generate_task, worker_messages, synthesis_messages


def test_local_prompt_roles_include_task_scope_and_evidence_contract():
    task = generate_task(1599, 100945, "labs", dataset="mimic-iv")
    packet = {"step_id": "labs", "records": [], "evidence_references": [], "error": None}
    controller = controller_messages(task, [packet])
    worker = worker_messages(task, task["evidence_plan"][0], packet)
    synthesis = synthesis_messages(task, [{"findings": [], "evidence_references": []}])
    assert controller[0]["role"] == "system"
    assert "evidence_plan" in controller[1]["content"]
    assert "grounding_packet" in worker[1]["content"]
    assert "success_criteria" in synthesis[1]["content"]

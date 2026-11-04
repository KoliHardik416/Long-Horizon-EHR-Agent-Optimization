from app.agent.agent import LocalEHRAgent
from app.agent.tools import EHRToolRegistry
from app.tasks import generate_task, run_task


class FakeRetriever:
    def labs(self, **arguments):
        return []


class FakeModel:
    def __init__(self):
        self.calls = 0

    def generate_json(self, messages):
        self.calls += 1
        if self.calls == 1:
            return {"decision": "execute", "tool_calls": [{"name": "labs", "arguments": {}}], "subtasks": []}
        return {"answer": "No records were retrieved.", "findings": [], "uncertainties": []}


def test_formal_task_runs_through_local_agent_contract():
    task = generate_task(1599, 100945, "labs")
    agent = LocalEHRAgent(FakeModel(), tools=EHRToolRegistry(FakeRetriever()))
    result = run_task(agent, task)
    assert result["answer"]["answer"] == "No records were retrieved."
    assert agent.trace["task_tree"]["task_id"] == "root"
    assert agent.trace["task_tree"]["evidence"]["labs"] == {"labs": []}

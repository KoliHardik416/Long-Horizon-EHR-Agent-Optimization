from app.agent.agent import LocalEHRAgent
from app.agent.tools import EHRToolRegistry
from app.tasks import generate_task, run_task, trace_to_trajectory


class FakeRetriever:
    def _rows(self, **kwargs):
        return [{"source": "mimiciii.labevents", "row_id": 1,
                 "subject_id": kwargs["subject_id"], "hadm_id": kwargs.get("hadm_id"),
                 "charttime": "2164-04-29 02:00:00", "itemid": 50912,
                 "label": "Creatinine", "value": "1.2", "valueuom": "mg/dL"}]

    labs = _rows
    medications = _rows
    diagnoses = _rows
    procedures = _rows
    notes = _rows

    def patient_context(self, **kwargs):
        return {"patient": {"source": "mimiciii.patients", "subject_id": kwargs["subject_id"]},
                "admissions": [], "icu_stays": []}

    def admissions(self, **kwargs):
        return [{"source": "mimiciii.admissions", "subject_id": kwargs["subject_id"],
                 "hadm_id": kwargs.get("hadm_id")}]


class RecursiveModel:
    def __init__(self):
        self.calls = 0

    def generate_json(self, messages):
        self.calls += 1
        if self.calls == 1:
            return {"decision": "delegate", "reason": "independent evidence streams",
                    "tool_calls": [], "subtasks": [
                        {"task_id": "labs", "role": "worker", "objective": "Review labs", "allowed_tools": ["labs"], "arguments": {}},
                        {"task_id": "notes", "role": "worker", "objective": "Review notes", "allowed_tools": ["notes"], "arguments": {}},
                    ]}
        if self.calls in (2, 3):
            return {"findings": ["Evidence retrieved."], "uncertainties": [], "evidence_references": []}
        return {"answer": "The admission has documented laboratory and clinical-note evidence.",
                "findings": [], "uncertainties": []}


def test_integrated_task_delegates_and_converts_to_formal_trajectory():
    task = generate_task(1599, 100945, "integrated")
    agent = LocalEHRAgent(RecursiveModel(), tools=EHRToolRegistry(FakeRetriever()))
    result = run_task(agent, task)
    assert len(result["trace"]["task_tree"]["children"]) == 2
    trajectory = trace_to_trajectory(result["trace"], task, "local-test-model")
    assert trajectory["task_id"] == task["task_id"]
    assert trajectory["final_answer"].startswith("The admission")
    assert any(step["action"] == "tool_call" for step in trajectory["steps"])
    assert trajectory["validation"]["tool_calls_valid"] is True

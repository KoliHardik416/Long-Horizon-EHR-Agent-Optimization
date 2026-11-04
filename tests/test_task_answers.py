from app.tasks import generate_task, ground_task


class FakeRetriever:
    def labs(self, **kwargs):
        return [{"source": "mimiciii.labevents", "row_id": 1,
                 "subject_id": kwargs["subject_id"], "hadm_id": kwargs["hadm_id"],
                 "charttime": "2164-04-29 02:00:00", "itemid": 50912,
                 "label": "Creatinine", "value": "1.2", "valueuom": "mg/dL"}]


def test_ground_task_adds_evidence_and_deterministic_answer():
    task = generate_task(1599, 100945, "labs")
    grounded = ground_task(task, FakeRetriever())
    assert grounded["reference_evidence"] == [{
        "source": "mimiciii.labevents",
        "identifiers": {
            "row_id": 1, "subject_id": 1599, "hadm_id": 100945,
            "charttime": "2164-04-29 02:00:00", "itemid": 50912,
        },
        "description": "Laboratory measurements for the subject and admission",
    }]
    assert "Creatinine=1.2 mg/dL" in grounded["reference_answer"]


def test_ground_task_rejects_already_grounded_task():
    task = generate_task(1599, 100945, "labs")
    task["reference_answer"] = "already populated"
    try:
        ground_task(task, FakeRetriever())
    except ValueError as exc:
        assert "already" in str(exc)
    else:
        raise AssertionError("expected already-grounded task to fail")

from app.tasks import build_grounding_packets, generate_task


class FakeRetriever:
    def labs(self, **kwargs):
        return [{"source": "mimiciv_hosp.labevents", "labevent_id": 7,
                 "subject_id": kwargs["subject_id"], "hadm_id": kwargs["hadm_id"],
                 "label": "Creatinine", "valuenum": 1.2}]


def test_mimiciv_task_generation_uses_dataset_specific_sources():
    task = generate_task(1599, 100945, "labs", dataset="mimic-iv")
    assert task["dataset"] == "mimic-iv"
    assert task["task_id"].startswith("mimiciv-")
    assert task["evidence_plan"][0]["expected_sources"] == ["mimiciv_hosp.labevents"]


def test_grounding_packet_contains_scope_records_and_provenance():
    task = generate_task(1599, 100945, "labs", dataset="mimic-iv")
    packets = build_grounding_packets(task, FakeRetriever())
    assert len(packets) == 1
    assert packets[0]["arguments"] == {"subject_id": 1599, "hadm_id": 100945}
    assert packets[0]["evidence_references"][0]["source"] == "mimiciv_hosp.labevents"

import pytest

from app.agent.tools import EHRToolRegistry


class FakeRetriever:
    def __getattr__(self, name):
        return lambda **kwargs: [{"source": f"mimiciii.{name}", **kwargs}]


def test_all_agent_tools_are_allow_listed_and_provenanced():
    registry = EHRToolRegistry(FakeRetriever())
    for name in ("patient_context", "admissions", "labs", "medications", "diagnoses", "procedures", "notes"):
        result = registry.call(name, {"subject_id": 1599})
        assert result
        assert (result.get("source") or result[name][0]["source"]).startswith("mimiciii.")


def test_invalid_tool_and_id_are_useful_errors():
    registry = EHRToolRegistry(FakeRetriever())
    with pytest.raises(ValueError, match="Unknown EHR tool"):
        registry.call("run_sql", {"subject_id": 1599})
    with pytest.raises(ValueError, match="positive subject_id"):
        registry.call("labs", {"subject_id": 0})


def test_database_error_is_returned_without_crashing():
    class Broken(FakeRetriever):
        def labs(self, **kwargs):
            raise RuntimeError("relation mimiciii.labevents does not exist")
    result = EHRToolRegistry(Broken()).call("labs", {"subject_id": 1599})
    assert result["error"]["type"] == "retrieval_error"
    assert result["error"]["source"] == "mimiciii.labevents"


def test_empty_result_is_a_valid_answer():
    class Empty(FakeRetriever):
        def labs(self, **kwargs): return []
    assert EHRToolRegistry(Empty()).call("labs", {"subject_id": 999999}) == {"labs": []}


def test_temporal_arguments_are_parsed_and_forwarded():
    class Capture(FakeRetriever):
        def labs(self, **kwargs): self.kwargs = kwargs; return []
    retriever = Capture()
    EHRToolRegistry(retriever).call("labs", {"subject_id": 1599, "start": "2001-01-01T00:00:00Z", "end": "2001-01-02T00:00:00Z"})
    assert retriever.kwargs["start"].year == 2001
    assert retriever.kwargs["end"].day == 2

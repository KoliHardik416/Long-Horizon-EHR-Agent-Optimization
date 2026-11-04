import os
import pytest

from app.retrieval import MIMICIIIRetriever


pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="MIMIC-III PostgreSQL is not configured")


def test_patient_and_admission_context_have_sources():
    result = MIMICIIIRetriever().patient_context(1599)
    assert "patient" in result and "admissions" in result
    for row in result["admissions"]:
        assert row["source"] == "mimiciii.admissions"


def test_all_structured_retrievals_return_source_fields():
    retriever = MIMICIIIRetriever()
    calls = [("labs", "mimiciii.labevents"), ("medications", "mimiciii.prescriptions"),
             ("diagnoses", "mimiciii.diagnoses_icd"), ("procedures", "mimiciii.procedures_icd"),
             ("notes", "mimiciii.noteevents")]
    for method, source in calls:
        rows = getattr(retriever, method)(1599, limit=1)
        assert all(row["source"] == source for row in rows)


def test_temporal_filter_is_half_open():
    rows = MIMICIIIRetriever().labs(1599, start="2001-01-01", end="2001-02-01", limit=100)
    assert all(row.get("charttime") is None or row["charttime"].isoformat() < "2001-02-01" for row in rows)


def test_unknown_subject_is_empty_not_exception():
    assert MIMICIIIRetriever().labs(999999999, limit=1) == []

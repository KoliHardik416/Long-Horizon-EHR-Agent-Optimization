from app.retrieval.mimic3 import MIMICIIIRetriever


def test_query_surface_covers_required_actions():
    expected = {"patient_context", "admissions", "labs", "medications", "diagnoses", "procedures", "notes"}
    assert expected.issubset(set(dir(MIMICIIIRetriever)))


def test_provenance_source_is_attached_to_rows():
    rows = MIMICIIIRetriever._with_source([{"subject_id": 1599, "hadm_id": 100945}], "mimiciii.labevents")
    assert rows == [{"source": "mimiciii.labevents", "subject_id": 1599, "hadm_id": 100945}]

"""Database-grounded reference evidence and answer construction."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any

from app.retrieval import MIMICIIIRetriever


def _text(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    return str(value)


def _identifiers(row: dict[str, Any]) -> dict[str, Any]:
    preferred = ("row_id", "labevent_id", "note_id", "itemid", "subject_id", "hadm_id",
                 "icustay_id", "stay_id", "charttime", "chartdate", "seq_num")
    return {key: _text(row[key]) if isinstance(row[key], (datetime, date)) else row[key]
            for key in preferred if key in row and row[key] is not None}


def _references(rows: list[dict[str, Any]], description: str) -> list[dict[str, Any]]:
    references = []
    for row in rows:
        if row.get("source") and _identifiers(row):
            references.append({"source": row["source"], "identifiers": _identifiers(row),
                               "description": description})
    return references


def _rows_for_tool(name: str, result: Any) -> list[dict[str, Any]]:
    if name == "patient_context":
        rows = []
        if isinstance(result, dict):
            if result.get("patient"):
                rows.append({"source": "mimiciii.patients", **result["patient"]})
            rows.extend(result.get("admissions", []))
            rows.extend(result.get("icu_stays", []))
        return rows
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and isinstance(result.get(name), list):
        return result[name]
    return []


def _answer_for(task_type: str, evidence: dict[str, Any]) -> str:
    parts: list[str] = []
    for tool, result in evidence.items():
        rows = _rows_for_tool(tool, result)
        if not rows:
            parts.append(f"No records were retrieved for {tool}.")
            continue
        if tool == "labs":
            values = []
            for row in rows[:20]:
                label = row.get("label") or f"itemid {row.get('itemid')}"
                value = row.get("value") if row.get("value") is not None else row.get("valuenum")
                unit = row.get("valueuom") or ""
                when = row.get("charttime")
                values.append(f"{label}={value}{(' ' + unit) if unit else ''} at {_text(when)}")
            parts.append("Laboratory records: " + "; ".join(values) + ".")
        elif tool == "admissions":
            parts.append("Admission records: " + "; ".join(
                f"{row.get('admission_type', 'unknown')} admission {row.get('admittime', 'unknown')}"
                for row in rows[:20]) + ".")
        elif tool == "medications":
            parts.append("Medication records: " + "; ".join(
                f"{row.get('drug', 'unknown')} ({row.get('dose_val_rx', '')} {row.get('dose_unit_rx', '')})"
                for row in rows[:20]) + ".")
        elif tool == "diagnoses":
            parts.append("Diagnosis records: " + "; ".join(
                str(row.get("long_title") or row.get("short_title") or row.get("icd9_code"))
                for row in rows[:20]) + ".")
        elif tool == "procedures":
            parts.append("Procedure records: " + "; ".join(
                str(row.get("long_title") or row.get("short_title") or row.get("icd9_code"))
                for row in rows[:20]) + ".")
        elif tool == "notes":
            parts.append("Clinical note records retrieved: " + "; ".join(
                f"{row.get('category', row.get('note_type', 'unknown'))} at "
                f"{_text(row.get('charttime') or row.get('chartdate'))}"
                for row in rows[:20]) + ".")
        elif tool == "patient_context":
            parts.append(f"Patient context records retrieved: {len(rows)}.")
    return " ".join(parts) or "No supporting records were retrieved."


def ground_task(task: dict[str, Any], retriever: MIMICIIIRetriever | None = None) -> dict[str, Any]:
    """Populate a task draft using only its declared retrieval tools."""
    if task.get("reference_answer") is not None:
        raise ValueError("task already has a reference_answer")
    retriever = retriever or MIMICIIIRetriever()
    scope = task["scope"]
    arguments = {"subject_id": scope["subject_id"]}
    if scope.get("target_hadm_id") is not None:
        arguments["hadm_id"] = scope["target_hadm_id"]

    evidence: dict[str, Any] = {}
    for tool in task["required_tools"]:
        if tool == "patient_context":
            evidence[tool] = retriever.patient_context(**arguments)
        else:
            evidence[tool] = getattr(retriever, tool)(**arguments, limit=100)

    references = []
    descriptions = {
        "labs": "Laboratory measurements for the subject and admission",
        "admissions": "Admission record for the subject",
        "medications": "Medication prescription records for the admission",
        "diagnoses": "Diagnosis records for the admission",
        "procedures": "Procedure records for the admission",
        "notes": "Clinical note records for the subject and admission",
        "patient_context": "Patient, admission, and ICU context records",
    }
    for tool, result in evidence.items():
        references.extend(_references(_rows_for_tool(tool, result), descriptions[tool]))

    grounded = deepcopy(task)
    grounded["reference_evidence"] = references
    grounded["reference_answer"] = _answer_for(task["task_id"].split("-")[-2], evidence)
    return grounded

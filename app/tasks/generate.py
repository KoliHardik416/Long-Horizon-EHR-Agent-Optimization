"""Deterministic task-draft generation without an LLM.

This module creates task contracts only. Evidence retrieval and reference-answer
construction are intentionally separate pipeline stages.
"""

from __future__ import annotations

from typing import Any, Iterable


TASK_TEMPLATES: dict[str, dict[str, Any]] = {
    "labs": {
        "question": "How did laboratory values change during this admission?",
        "difficulty": "medium",
        "complexity": {"retrieval": 1, "reasoning": 1, "temporal": 2, "integration": 0, "total": 4},
        "required_tools": ["labs"],
    },
    "admission": {
        "question": "Summarize the patient's admission and hospital course.",
        "difficulty": "easy",
        "complexity": {"retrieval": 1, "reasoning": 1, "temporal": 1, "integration": 1, "total": 4},
        "required_tools": ["patient_context", "admissions"],
    },
    "medications": {
        "question": "What medications were prescribed during this admission?",
        "difficulty": "easy",
        "complexity": {"retrieval": 1, "reasoning": 1, "temporal": 1, "integration": 0, "total": 3},
        "required_tools": ["medications"],
    },
    "diagnoses": {
        "question": "Which diagnoses were documented for this admission?",
        "difficulty": "easy",
        "complexity": {"retrieval": 1, "reasoning": 1, "temporal": 0, "integration": 0, "total": 2},
        "required_tools": ["diagnoses"],
    },
    "procedures": {
        "question": "Which procedures were documented for this admission?",
        "difficulty": "easy",
        "complexity": {"retrieval": 1, "reasoning": 1, "temporal": 0, "integration": 0, "total": 2},
        "required_tools": ["procedures"],
    },
    "notes": {
        "question": "What clinically relevant information is documented in the patient's notes?",
        "difficulty": "medium",
        "complexity": {"retrieval": 1, "reasoning": 1, "temporal": 1, "integration": 1, "total": 4},
        "required_tools": ["notes"],
    },
    "integrated": {
        "question": "Summarize the admission using the available clinical records and identify the main documented trends.",
        "difficulty": "hard",
        "complexity": {"retrieval": 2, "reasoning": 2, "temporal": 2, "integration": 2, "total": 8},
        "required_tools": ["patient_context", "admissions", "labs", "medications", "diagnoses", "procedures", "notes"],
        "evidence_plan": [
            {"step_id": "admission-context", "objective": "Summarize admission and ICU context.", "allowed_tools": ["patient_context", "admissions"], "depends_on": [], "expected_sources": ["mimiciii.admissions", "mimiciii.icustays"], "required": True},
            {"step_id": "laboratory-trends", "objective": "Identify important laboratory trends during the admission.", "allowed_tools": ["labs"], "depends_on": ["admission-context"], "expected_sources": ["mimiciii.labevents"], "required": True},
            {"step_id": "treatments", "objective": "Identify relevant medication and procedure records.", "allowed_tools": ["medications", "procedures"], "depends_on": ["admission-context"], "expected_sources": ["mimiciii.prescriptions", "mimiciii.procedures_icd"], "required": True},
            {"step_id": "clinical-narrative", "objective": "Find supporting information in clinical notes and diagnoses.", "allowed_tools": ["notes", "diagnoses"], "depends_on": ["admission-context"], "expected_sources": ["mimiciii.noteevents", "mimiciii.diagnoses_icd"], "required": True}
        ]
    },
}


def _task_id(dataset: str, subject_id: int, hadm_id: int | None, task_type: str) -> str:
    admission = str(hadm_id) if hadm_id is not None else "none"
    return f"{dataset.replace('-', '')}-{subject_id}-{admission}-{task_type}-001"


def generate_task(subject_id: int, hadm_id: int | None = None,
                  task_type: str = "labs", split: str | None = None,
                  dataset: str = "mimic-iii") -> dict[str, Any]:
    """Create one reproducible task draft from a fixed template.

    The draft deliberately has no reference answer or evidence yet. Those are
    populated by the database-grounded answer-generation stage.
    """
    if subject_id <= 0:
        raise ValueError("subject_id must be positive")
    if hadm_id is not None and hadm_id <= 0:
        raise ValueError("hadm_id must be positive")
    if task_type not in TASK_TEMPLATES:
        raise ValueError(f"unknown task type: {task_type}")
    if split not in {None, "train", "validation", "test"}:
        raise ValueError("split must be null, train, validation, or test")
    if dataset not in {"mimic-iii", "mimic-iv"}:
        raise ValueError("dataset must be mimic-iii or mimic-iv")

    template = TASK_TEMPLATES[task_type]
    source_prefix = "mimiciii" if dataset == "mimic-iii" else "mimiciv_hosp"
    sources = {
        "patient_context": f"{source_prefix}.patients",
        "admissions": f"{source_prefix}.admissions",
        "labs": f"{source_prefix}.labevents",
        "medications": f"{source_prefix}.prescriptions",
        "diagnoses": f"{source_prefix}.diagnoses_icd",
        "procedures": f"{source_prefix}.procedures_icd",
        "notes": "mimiciii.noteevents" if dataset == "mimic-iii" else "mimiciv_note.discharge",
    }
    task = {
        "schema_version": 1,
        "task_id": _task_id(dataset, subject_id, hadm_id, task_type),
        "dataset": dataset,
        "split": split,
        "scope": {
            "subject_id": subject_id,
            "admission_scope": "target_admission" if hadm_id is not None else "all_admissions",
            "target_hadm_id": hadm_id,
        },
        "question": template["question"],
        "difficulty": template["difficulty"],
        "complexity": dict(template["complexity"]),
        "reference_evidence": [],
        "reference_answer": None,
        "required_tools": list(template["required_tools"]),
    }
    if "evidence_plan" in template:
        task["evidence_plan"] = [dict(step, arguments={"subject_id": subject_id, "hadm_id": hadm_id})
                                  for step in template["evidence_plan"]]
        for step in task["evidence_plan"]:
            step["expected_sources"] = [
                ("mimiciv_note.discharge" if dataset == "mimic-iv" and source == "mimiciii.noteevents"
                 else source.replace("mimiciii", source_prefix))
                for source in step["expected_sources"]
            ]
    else:
        task["evidence_plan"] = [
            {"step_id": tool, "objective": f"Retrieve records using {tool}.",
             "allowed_tools": [tool], "depends_on": [],
             "expected_sources": [sources[tool]], "required": True,
             "arguments": {"subject_id": subject_id, "hadm_id": hadm_id}}
            for tool in template["required_tools"]
        ]
    task["success_criteria"] = {
        "required_evidence_steps": [step["step_id"] for step in task["evidence_plan"]],
        "required_comparisons": [],
        "unsupported_claim_constraints": [
            "Do not claim facts without supporting database or note evidence.",
            "Do not treat missing data as proof that an event did not occur."
        ],
    }
    task["execution"] = {"max_extra_calls": 2, "allow_reordering": True, "allow_retries": True}
    return task


def generate_tasks(subject_ids: Iterable[int], hadm_id: int | None = None,
                   task_types: Iterable[str] = ("labs",),
                   split: str | None = None, dataset: str = "mimic-iii") -> list[dict[str, Any]]:
    """Generate deterministic drafts in input order."""
    task_types = tuple(task_types)
    return [generate_task(subject_id, hadm_id, task_type, split, dataset)
            for subject_id in subject_ids for task_type in task_types]

"""Minimal command-line smoke tests for the PostgreSQL retriever."""

from __future__ import annotations

import argparse
import json

from .retriever import StructuredRetriever


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("subject_id", type=int)
    parser.add_argument("--hadm-id", type=int)
    args = parser.parse_args()
    retriever = StructuredRetriever()
    result = retriever.patient_context(args.subject_id)
    result["labs"] = retriever.labs(args.subject_id, args.hadm_id, limit=20)
    result["diagnoses"] = retriever.diagnoses(args.subject_id, args.hadm_id)
    result["medications"] = retriever.medications(args.subject_id, args.hadm_id)
    result["procedures"] = retriever.procedures(args.subject_id, args.hadm_id)
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()


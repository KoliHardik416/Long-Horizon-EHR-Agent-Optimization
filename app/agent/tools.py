"""Safe, allow-listed tools exposed to the local agent."""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.retrieval import MIMICIIIRetriever


TOOL_SCHEMAS = [
    {"name": "patient_context", "description": "Get demographics, admissions, and ICU stays.", "arguments": {"subject_id": "integer"}},
    {"name": "labs", "description": "Get bounded laboratory results.", "arguments": {"subject_id": "integer", "hadm_id": "integer|null", "limit": "integer 1..500"}},
    {"name": "diagnoses", "description": "Get coded diagnoses.", "arguments": {"subject_id": "integer", "hadm_id": "integer|null", "limit": "integer 1..200"}},
    {"name": "medications", "description": "Get medication prescriptions.", "arguments": {"subject_id": "integer", "hadm_id": "integer|null", "limit": "integer 1..500"}},
    {"name": "procedures", "description": "Get coded procedures.", "arguments": {"subject_id": "integer", "hadm_id": "integer|null", "limit": "integer 1..200"}},
]


class EHRToolRegistry:
    """Dispatch only to fixed retriever methods; arbitrary SQL is impossible."""

    def __init__(self, retriever: "MIMICIIIRetriever | None" = None):
        if retriever is None:
            from app.retrieval import MIMICIIIRetriever
            retriever = MIMICIIIRetriever()
        self.retriever = retriever

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        allowed = {"patient_context", "labs", "diagnoses", "medications", "procedures"}
        if name not in allowed:
            raise ValueError(f"Unknown EHR tool: {name}")
        
        if "subject_id" not in arguments or int(arguments["subject_id"]) <= 0:
            raise ValueError("A positive subject_id is required")
        
        args = dict(arguments)
        args["subject_id"] = int(args["subject_id"])

        if args.get("hadm_id") is not None:
            args["hadm_id"] = int(args["hadm_id"])
        if name == "patient_context":
            args.pop("hadm_id", None)
        limits = {"labs": 500, "diagnoses": 200, "medications": 500, "procedures": 200}
        
        if name in limits:
            args["limit"] = min(max(int(args.get("limit", 100)), 1), limits[name])
            
        result = getattr(self.retriever, name)(**args)
        return result if isinstance(result, dict) else {name: result}

    def call_json(self, name: str, arguments: dict[str, Any]) -> str:
        return json.dumps(self.call(name, arguments), default=str)

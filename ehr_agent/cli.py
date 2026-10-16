"""Run a local Gemma-compatible EHR agent and save its trajectory."""

from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from .agent import LocalEHRAgent
from .model import LocalHFModel
from .traces import append_jsonl


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the local EHR agent")
    parser.add_argument("request")
    parser.add_argument("--subject-id", type=int, required=True)
    parser.add_argument("--hadm-id", type=int)
    parser.add_argument("--model", default=os.environ.get("HF_MODEL_ID", "google/gemma-4-12B"))
    parser.add_argument("--trace", default="trajectories.jsonl")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-calls", type=int, default=12)
    args = parser.parse_args()

    model = LocalHFModel(args.model)
    agent = LocalEHRAgent(model, max_depth=args.max_depth, max_calls=args.max_calls)
    result = agent.run(args.request, subject_id=args.subject_id, hadm_id=args.hadm_id)
    append_jsonl(args.trace, result["trace"])
    print(json.dumps(result["answer"], default=str, indent=2))
    print(f"\nTrajectory written to {args.trace}")


if __name__ == "__main__":
    main()

# Local Hugging Face EHR agent

This package provides the orchestration layer above `structured_retrieval`.
It uses one local model in two runtime roles:

1. **Controller** — decide whether to execute, delegate recursively, enforce budgets,
   and synthesize the final answer.
2. **Worker** — run bounded, allow-listed retrieval tools and analyze only its task.

The controller and workers are role-specific invocations of the same model, not
separate permanent models. Recursion is bounded by depth, child count, and model
call budgets.

The current adapter uses a local Transformers causal language model and asks it
for JSON. This is more portable than depending on model-specific native tool
calling. Models with reliable structured generation can replace `LocalHFModel`.

Example:

```python
from ehr_agent import LocalEHRAgent
from ehr_agent.model import LocalHFModel

model = LocalHFModel("your-local-instruct-model")
agent = LocalEHRAgent(model)
result = agent.run(
    "For subject 10000032 and admission 22595853, summarize the admission "
    "and explain the major laboratory abnormalities."
)
```

Run a local Gemma-compatible checkpoint from the command line:

```bash
pip install -r ehr_agent/requirements.txt
python -m ehr_agent.cli \
  --model google/gemma-3-1b-it \
  --subject-id 10000032 \
  --hadm-id 22595853 \
  "Summarize the admission and identify important laboratory trends." \
  --trace trajectories.jsonl
```

The checkpoint must be available to Transformers and may require Hugging Face
authentication or model access approval. For Gemma, accept the model terms on
Hugging Face and authenticate before running:

```bash
.venv312/bin/hf auth login
```

Use `--model` to select another local or Hugging Face-compatible checkpoint.

The trajectory contains the controller decisions, task tree, scoped worker
contexts, tool calls, model-call timings, final synthesis, and baseline quality
score. Inspecting this record is the first step toward improving routing
accuracy, tool precision, evidence grounding, latency, and unnecessary
delegation.

`LocalEHRAgent.run()` returns both the final answer and a complete trajectory
containing task events, tool calls, model calls, the task tree, and a baseline
quality score. Persist trajectories with `ehr_agent.traces.append_jsonl` for
review and future supervised training.

For training, log examples with a gold routing decision:

```json
{
  "request": "...",
  "mode": "decompose",
  "tasks": [
    {"task_id": "labs", "role": "worker", "objective": "...", "allowed_tools": ["labs"]},
    {"task_id": "timeline", "role": "worker", "objective": "...", "allowed_tools": ["patient_context", "diagnoses"]}
  ]
}
```

The baseline scorer is intentionally simple. Replace or augment it with
deterministic evidence checks and a calibrated evaluator agent before using
preference optimization or reinforcement learning.

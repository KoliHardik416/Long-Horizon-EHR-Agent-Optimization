# Structured PostgreSQL retrieval

This package is the application-facing layer over the MIMIC-IV PostgreSQL
schemas created by `database/mimic-iv/buildmimic/postgres/`.

Install the dependency from the existing baseline requirements:

```bash
pip install -r baseline_postgres/requirements.txt
```

Set standard PostgreSQL variables such as `PGDATABASE=mimiciv`, then use:

```python
from app.retrieval import StructuredRetriever

retriever = StructuredRetriever()
context = retriever.patient_context(10000032)
labs = retriever.labs(10000032, hadm_id=22595853, limit=100)
```

The CLI provides a smoke test:

```bash
python -m app.retrieval.cli 10000032 --hadm-id 22595853
```

The API deliberately exposes fixed retrieval operations rather than arbitrary
SQL generation. This makes it suitable for wrapping as agent tools later.


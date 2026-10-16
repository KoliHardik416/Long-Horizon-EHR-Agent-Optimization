# PostgreSQL structured-EHR baseline

This directory is the first retrieval baseline for the MIMIC-IV project. It
uses the existing MIMIC loaders in `database/mimic-iv/buildmimic/postgres/` and
`database/mimic-iv-note/buildmimic/postgres/`; it does not replace or modify them.

## Architecture

```text
MIMIC-IV CSV/CSV.GZ ────────┐
                            ├── PostgreSQL
MIMIC-IV-Note CSV/CSV.GZ ───┘       ├── raw structured tables
                                    ├── derived concept tables
                                    └── note source tables
                                                ↓
                                  baseline retrieval functions
```

PostgreSQL is the source of truth. The Python retrieval layer exposes small,
parameterized functions suitable for later LlamaIndex tools. It currently
supports patient context, admissions, labs, diagnoses, medications, and
procedures. Note retrieval is intentionally not included in this baseline;
the notes remain available in `mimiciv_note` for the later Qdrant pipeline.

## Setup

Create a database and install the Python dependency:

```bash
createdb mimiciv
python -m venv .venv
source .venv/bin/activate
pip install -r baseline_postgres/requirements.txt
```

Load structured MIMIC-IV data. The raw data directory must contain `hosp/` and
`icu/` subdirectories:

```bash
PGDATABASE=mimiciv \
  database/mimic-iv/buildmimic/postgres/build_mimic.sh /path/to/mimiciv
```

Load MIMIC-IV-Note into the same database. Its `mimic_data_dir` points to the
directory containing the note CSV files:

```bash
psql -d mimiciv -f database/mimic-iv-note/buildmimic/postgres/create.sql
psql -d mimiciv -v ON_ERROR_STOP=1 \
  -v mimic_data_dir=/path/to/mimic-iv-note/note \
  -f database/mimic-iv-note/buildmimic/postgres/load_gz.sql
```

The MIMIC `create.sql` scripts drop and recreate their schemas. Only run them
against a database dedicated to this dataset.

## Verify the database

```bash
python baseline_postgres/verify.py
```

Optional connection variables are the standard PostgreSQL variables:
`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD`.

## Use the retrieval layer

```python
from baseline_postgres.retrieval import PostgresRetriever

db = PostgresRetriever()
print(db.patient_context(10000032))
print(db.admissions(10000032))
print(db.labs(subject_id=10000032, hadm_id=22595853, limit=50))
```

Every method uses parameterized SQL and returns dictionaries containing source
table information. The functions are deliberately narrow so an agent can call
them without generating arbitrary SQL.

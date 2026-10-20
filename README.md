# RAO local EHR development setup

This repository contains retrieval, note chunking, embedding, and local-agent
experiments for de-identified MIMIC data. Keep downloaded or prepared EHR data
outside version control. The root `.gitignore` excludes common local data,
database state, vector-store state, and generated artifacts.

## Python environment

```bash
python3.12 -m venv .venv312
.venv312/bin/pip install -r app/agent/requirements.txt
.venv312/bin/pip install -r baseline_postgres/requirements.txt
```

## PostgreSQL and MIMIC-IV

The Docker setup is in `database/mimic-iv/buildmimic/postgres/docker`.
Prepare a MIMIC-IV directory containing `hosp/` and `icu/`, then run:

```bash
cd database/mimic-iv/buildmimic/postgres/docker
cp .env.example .env
# Edit MIMIC_DATA_DIR to an absolute path containing hosp/ and icu/.
docker compose up --build
```

The default connection is `localhost:5432`, database `mimiciv`, user
`postgres`, password `postgres`. The build job loads tables, optionally derives
concepts, validates the result, and exits; `mimic-db` remains running.

```bash
docker compose logs -f mimic-build
docker compose exec mimic-db psql -U postgres -d mimiciv
```

Stop without deleting data with `docker compose stop`. To discard the database
volume and reload from scratch, use `docker compose down -v`.

Load MIMIC-IV-Note into the same database:

```bash
cd /path/to/RAO
PGHOST=localhost PGPORT=5432 PGDATABASE=mimiciv PGUSER=postgres PGPASSWORD=postgres \
psql -f database/mimic-iv-note/buildmimic/postgres/create.sql

PGHOST=localhost PGPORT=5432 PGDATABASE=mimiciv PGUSER=postgres PGPASSWORD=postgres \
psql -v ON_ERROR_STOP=1 \
  -v mimic_data_dir=/absolute/path/to/mimic-iv-note/note \
  -f database/mimic-iv-note/buildmimic/postgres/load_gz.sql
```

## MIMIC-IV note chunking

After loading `mimiciv_note`, run section-aware chunking:

```bash
PGHOST=localhost PGPORT=5432 PGDATABASE=mimiciv PGUSER=postgres PGPASSWORD=postgres \
.venv312/bin/python -m app.notes.cli \
  artifacts/mimic_note_chunks.jsonl \
  --note-type discharge --chunk-size 500 --chunk-overlap 75
```

This creates inspectable JSONL and does not generate embeddings. Use
`--subject-id 10000032` for a focused development run.

## MIMIC-III chunking and embeddings

The existing `app/rag/docker-compose.yml` starts Qdrant and an indexer that reads
MIMIC-III `NOTEEVENTS` from PostgreSQL, chunks notes, embeds them with FastEmbed,
and stores vectors in Qdrant. It expects a host PostgreSQL database named
`mimic` with `postgres/postgres` credentials.

```bash
cd rag
docker compose up --build
```

Qdrant is available at `http://localhost:6333`; the default collection is
`mimic3_notes`. Generated chunks are written to
`artifacts/mimic3_note_chunks.jsonl`, and the collection is recreated on each
indexing run. For a smoke test, set `NOTE_LIMIT: "15"` in
`app/rag/docker-compose.yml` and rerun the command. Set `EMBEDDING_MODEL` to change
the FastEmbed model.

## Local Gemma agent

Configure `.env` with `HF_TOKEN` and `HF_MODEL_ID`, authenticate, and run:

```bash
.venv312/bin/hf auth login
PGHOST=localhost PGPORT=5432 PGDATABASE=mimiciv PGUSER=postgres PGPASSWORD=postgres \
.venv312/bin/python -m app.agent.cli \
  --subject-id 10000032 --hadm-id 22595853 \
  "Summarize the admission and identify important laboratory trends." \
  --trace artifacts/trajectories.jsonl
```

The trajectory captures controller decisions, task contracts, tool calls,
worker reports, synthesis, timings, and a baseline quality score. These traces
support improvements to routing, evidence grounding, and later evaluator/RL
experiments.

## Troubleshooting

```bash
PGHOST=localhost PGPORT=5432 PGDATABASE=mimiciv PGUSER=postgres PGPASSWORD=postgres \
.venv312/bin/python baseline_postgres/verify.py
curl http://localhost:6333/collections
```

If Gemma access returns `401 Unauthorized`, accept the model terms on Hugging
Face and authenticate with `hf auth login`. Use a smaller checkpoint with
`--model` while testing the orchestration.

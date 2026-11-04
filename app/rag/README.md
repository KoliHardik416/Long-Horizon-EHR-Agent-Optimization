# Local MIMIC RAG stack

This stack keeps PostgreSQL and Qdrant in separate containers. The indexer
connects to the existing `mimic-postgres` container through
`host.docker.internal:5432`, extracts MIMIC-III `NOTEEVENTS`, chunks the notes,
embeds child chunks with FastEmbed, and stores them in Qdrant.

Start Qdrant and index the current 15-patient notes with:

```bash
cd app/rag
docker compose up --build
```

Qdrant is available at `http://localhost:6333`. The default collection is
`mimic3_notes`. Each point contains the child chunk vector plus `subject_id`,
`hadm_id`, `parent_note_id`, `section`, `chunk_index`, and source text.

Set `NOTE_LIMIT` to a positive number to index only the first N notes during a
smoke test. The indexer recreates the collection on each run so experiments
are reproducible.

## MIMIC-IV 500-patient stack

The MIMIC-IV subset uses a separate PostgreSQL service and database so the
working MIMIC-III stack is not overwritten:

```bash
cd app/rag
docker compose -f docker-compose.mimiciv500.yml up --build
```

It uses PostgreSQL database `mimiciv500` on host port `5433`, persistent data in
`runtime/postgres_mimiciv500`, Qdrant on host port `6335`, and the
`mimiciv_note_500` collection. The Compose build jobs load the structured
MIMIC-IV and MIMIC-IV-Note subset before the indexer starts.


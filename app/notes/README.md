# MIMIC-IV-Note chunking pipeline

This stage reads source notes from `mimiciv_note` in PostgreSQL and produces
inspectable hierarchical chunks. It does not generate embeddings or write to
Qdrant yet.

```text
note
└── section
    └── retrieval chunk
```

Each chunk retains `subject_id`, `hadm_id`, `note_id`, note type, timestamp,
section, and chunk position. `text` is the original evidence text;
`embedding_text` adds a small document/section context prefix for later
embedding.

Run after loading MIMIC-IV-Note into PostgreSQL:

```bash
python -m app.notes.cli \
  /tmp/mimic_note_chunks.jsonl \
  --note-type discharge \
  --chunk-size 500 \
  --chunk-overlap 75
```

The output JSONL should be inspected before adding embeddings and Qdrant.


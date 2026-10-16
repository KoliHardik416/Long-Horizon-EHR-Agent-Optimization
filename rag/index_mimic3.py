"""Embed MIMIC-III note chunks and store them in Qdrant.

Each child chunk receives its own vector. The payload preserves the note,
section, and encounter hierarchy so retrieval can expand a match later.
"""

from __future__ import annotations

import os
import time
import json
import uuid
from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from note_pipeline.chunk import chunk_note
from note_pipeline.extract_mimic3 import iter_mimic3_notes
from structured_retrieval.connection import connect


COLLECTION = os.getenv("QDRANT_COLLECTION", "mimic3_notes")
MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
OUTPUT = Path(os.getenv("CHUNK_OUTPUT", "/app/artifacts/mimic3_note_chunks.jsonl"))
LIMIT = int(os.getenv("NOTE_LIMIT", "0"))
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))


def wait_for_qdrant(client: QdrantClient) -> None:
    for _ in range(60):
        try:
            client.get_collections()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Qdrant did not become ready")


def make_collection(client: QdrantClient, dimension: int) -> None:
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
    )


def main() -> None:
    client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
    wait_for_qdrant(client)
    embedder = TextEmbedding(model_name=MODEL)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    collection_created = False
    batch = []

    def index_batch(chunks, handle):
        nonlocal collection_created, total
        if not chunks:
            return
        vectors = list(embedder.embed([chunk.embedding_text for chunk in chunks]))
        if not collection_created:
            make_collection(client, len(vectors[0]))
            collection_created = True
        points = [models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_id)),
            vector=vector.tolist(),
            payload={**chunk.as_dict(), "node_type": "chunk",
                     "parent_id": f"{chunk.parent_note_id}_{chunk.section_order:03d}",
                     "root_id": chunk.parent_note_id},
        ) for chunk, vector in zip(chunks, vectors)]
        client.upsert(collection_name=COLLECTION, points=points)
        for chunk in chunks:
            handle.write(json.dumps(chunk.as_dict(), default=str, ensure_ascii=False) + "\n")
        total += len(points)
        print(f"Indexed {total} chunks", flush=True)

    with OUTPUT.open("w", encoding="utf-8") as handle, connect() as conn:
        notes = iter_mimic3_notes(conn)
        if LIMIT > 0:
            notes = (note for i, note in enumerate(notes) if i < LIMIT)
        for note in notes:
            batch.extend(chunk_note(note))
            while len(batch) >= BATCH_SIZE:
                current, batch = batch[:BATCH_SIZE], batch[BATCH_SIZE:]
                index_batch(current, handle)
        index_batch(batch, handle)

    if total == 0:
        raise RuntimeError("No note chunks were produced")
    print(f"Indexed {total} chunks in Qdrant collection {COLLECTION}")


if __name__ == "__main__":
    main()


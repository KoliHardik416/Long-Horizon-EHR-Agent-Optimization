"""Embed MIMIC-IV-Note chunks from the configured PostgreSQL database."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from app.notes.chunk import chunk_note
from app.notes.extract import iter_notes
from app.retrieval.connection import connect

COLLECTION = os.getenv("QDRANT_COLLECTION", "mimiciv_note_500")
MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
OUTPUT = Path(os.getenv("CHUNK_OUTPUT", "/app/artifacts/mimiciv_note_chunks_500.jsonl"))
LIMIT = int(os.getenv("NOTE_LIMIT", "0"))
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))
NOTE_TYPE = os.getenv("NOTE_TYPE", "") or None


def wait_for_qdrant(client: QdrantClient) -> None:
    for _ in range(60):
        try:
            client.get_collections()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Qdrant did not become ready")


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
            if client.collection_exists(COLLECTION):
                client.delete_collection(COLLECTION)
            client.create_collection(
                collection_name=COLLECTION,
                vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
            )
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
        notes = iter_notes(conn, note_type=NOTE_TYPE)
        if LIMIT > 0:
            notes = (note for i, note in enumerate(notes) if i < LIMIT)
        for note in notes:
            batch.extend(chunk_note(note))
            while len(batch) >= BATCH_SIZE:
                current, batch = batch[:BATCH_SIZE], batch[BATCH_SIZE:]
                index_batch(current, handle)
        index_batch(batch, handle)

    if total == 0:
        raise RuntimeError("No MIMIC-IV note chunks were produced")
    print(f"Indexed {total} chunks in Qdrant collection {COLLECTION}")


if __name__ == "__main__":
    main()

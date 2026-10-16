FROM python:3.12-slim

WORKDIR /app
COPY rag/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY note_pipeline /app/note_pipeline
COPY structured_retrieval /app/structured_retrieval
COPY rag /app/rag

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "rag.index_mimic3"]


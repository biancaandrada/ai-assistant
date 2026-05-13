FROM python:3.11-slim

# System deps (chromadb needs a C toolchain for some sqlite/onnx bits)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so layer caches when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir wsproto

# Copy application code
COPY app ./app

# ChromaDB persistence path (overridable, mounted as a volume in compose)
ENV CHROMA_PATH=/data/chroma_db
RUN mkdir -p /data/chroma_db

EXPOSE 8000

# wsproto avoids the websockets-version handshake issue we hit earlier
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "wsproto"]

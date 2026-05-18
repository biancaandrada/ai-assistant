FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Install deps in a cacheable layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code (includes static/ frontend assets)
COPY app ./app
COPY pyproject.toml .

# Persisted vector store path (overridden by compose volume)
ENV CHROMA_PATH=/data/chroma_db \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN mkdir -p /data/chroma_db && chown -R app:app /app /data

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "wsproto"]

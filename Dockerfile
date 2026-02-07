# SHERLOCK - Fase 5. API + CLI. Use with docker-compose (neo4j, chroma).
FROM python:3.11-slim

WORKDIR /app

# System deps for PDF/OCR (optional; omit if no OCR needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default: run API. Override to run CLI (e.g. python main.py health)
EXPOSE 8001
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]

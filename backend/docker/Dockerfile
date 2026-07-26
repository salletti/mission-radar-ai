FROM python:3.12-slim

WORKDIR /app

# curl is required for the container HEALTHCHECK defined in docker-compose.prod.yml
# (python:3.12-slim does not ship it by default)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt

# Install torch CPU-only first — sentence-transformers otherwise pulls the ~2GB CUDA wheel
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements/base.txt

# Pre-download the embedding model at build time: no outbound call to
# HuggingFace Hub and no cold-start delay on first request in production.
ENV HF_HOME=/opt/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app /opt/huggingface
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

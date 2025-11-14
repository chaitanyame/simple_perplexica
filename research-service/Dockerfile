# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

WORKDIR /app

# Speed up pip and keep output lean
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_COLOR=1 \
    HF_HOME=/home/research/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/research/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/home/research/.cache/huggingface

# Install system dependencies (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd -m -u 1000 research

# Install Python dependencies first for better layer caching
COPY requirements.txt .
# Use BuildKit cache mount when available to accelerate pip installs
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Playwright installation (browsers and OS deps)
# Install browsers as non-root (cache in user dir), and deps as root
USER research
RUN playwright install chromium
USER root
RUN playwright install-deps chromium

# Pre-download Hugging Face models to avoid runtime downloads
# Done as 'research' user so caches live under /home/research/.cache/huggingface
USER research
RUN --mount=type=cache,target=/home/research/.cache/huggingface \
    sh -lc "python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')\"" || true
RUN --mount=type=cache,target=/home/research/.cache/huggingface \
    sh -lc "python -c \"from transformers import AutoTokenizer, AutoModelForSequenceClassification; name='cross-encoder/ms-marco-MiniLM-L-6-v2'; AutoTokenizer.from_pretrained(name); AutoModelForSequenceClassification.from_pretrained(name)\"" || true
USER root

# Copy application code with correct ownership (avoid chown step)
COPY --chown=research:research src/ ./src/
COPY --chown=research:research pyproject.toml .

# Switch to research user for runtime
USER research

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

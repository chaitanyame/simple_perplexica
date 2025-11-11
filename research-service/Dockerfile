FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd -m -u 1000 research

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to research user for Playwright installation
USER research

# Install Playwright browsers for Crawl4AI (as research user)
RUN playwright install chromium

# Switch back to root to install system deps for chromium
USER root
RUN playwright install-deps chromium

# Copy application code and set ownership
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml .
RUN chown -R research:research /app

# Switch to research user for runtime
USER research

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

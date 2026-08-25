FROM python:3.11-slim

LABEL maintainer="RevivePay AI"
LABEL description="RevivePay AI FastAPI backend"

# Don't buffer Python stdout/stderr — important for structured log streaming.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first for layer caching
COPY pyproject.toml ./

# Install project dependencies (no --editable to keep the layer clean)
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Copy source
COPY . .

# Create the data directory for SQLite
RUN mkdir -p /app/data

# Expose the default API port
EXPOSE 8000

# Run uvicorn. The FRONTEND_ORIGIN should be set via docker-compose env_file.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

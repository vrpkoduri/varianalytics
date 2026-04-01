# ---------------------------------------------------------------------------
# Variance Agent — Computation Service (Service 2)
# Multi-stage build: Python 3.11-slim
# Build context: project root (../)
# ---------------------------------------------------------------------------

# --- Stage 1: Install dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Install shared + service requirements
COPY shared/requirements.txt ./shared-requirements.txt
COPY services/computation/requirements.txt ./service-requirements.txt
RUN pip install --no-cache-dir --prefix=/install \
    -r shared-requirements.txt \
    -r service-requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

LABEL service="variance-agent-computation" \
      description="5.5-pass materiality-first computation engine" \
      port="8001"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy shared library and service code
COPY shared/ /app/shared/
COPY services/computation/ /app/services/computation/

# Copy synthetic data (parquet files needed at runtime)
COPY data/output/ /app/data/output/

# Copy config files
COPY shared/config/ /app/shared/config/

ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"

EXPOSE 8001

CMD ["uvicorn", "services.computation.main:app", "--host", "0.0.0.0", "--port", "8001"]

# ---------------------------------------------------------------------------
# Variance Agent — Gateway Service (Service 1)
# Multi-stage build: Python 3.11-slim
# Build context: project root (../)
# ---------------------------------------------------------------------------

# --- Stage 1: Install dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Install shared + service requirements
COPY shared/requirements.txt ./shared-requirements.txt
COPY services/gateway/requirements.txt ./service-requirements.txt
RUN pip install --no-cache-dir --prefix=/install \
    -r shared-requirements.txt \
    -r service-requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

LABEL service="variance-agent-gateway" \
      description="Auth, Chat/SSE, Dimensions, Config, Review, Approval, Notifications" \
      port="8000"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy shared library and service code
COPY shared/ /app/shared/
COPY services/gateway/ /app/services/gateway/

# Copy synthetic data (parquet files needed for DataService + ReviewStore)
COPY data/output/ /app/data/output/

# Copy config files
COPY shared/config/ /app/shared/config/

ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"

EXPOSE 8000

CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

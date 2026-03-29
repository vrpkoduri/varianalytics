# ── Build stage ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.11-slim

LABEL service="variance-agent-computation" \
      description="5.5-pass materiality-first computation engine" \
      port="8001"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy service code
COPY . /app/services/computation/

# Copy shared modules (mounted or copied at build time)
# COPY shared/ /app/shared/

ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED="1"

EXPOSE 8001

CMD ["uvicorn", "services.computation.main:app", "--host", "0.0.0.0", "--port", "8001"]

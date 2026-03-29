# ---------------------------------------------------------------------------
# Variance Agent — Gateway Service (Service 1)
# Multi-stage build: Python 3.11-slim
# ---------------------------------------------------------------------------

# --- Stage 1: Install dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /build

COPY services/gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

LABEL service="gateway" \
      description="Variance Agent — Gateway (Auth, Chat, Dimensions, Config, Review, Approval, Notifications)" \
      port="8000"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy shared library and service code
COPY shared/ /app/shared/
COPY services/gateway/ /app/services/gateway/

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

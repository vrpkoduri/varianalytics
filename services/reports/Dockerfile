# ---------------------------------------------------------------------------
# Variance Agent — Reports Service (Service 3)
# Multi-stage build: Python 3.11-slim
# Build context: project root (../)
# ---------------------------------------------------------------------------

# --- Stage 1: Install dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Install shared + service requirements
COPY shared/requirements.txt ./shared-requirements.txt
COPY services/reports/requirements.txt ./service-requirements.txt
RUN pip install --no-cache-dir --prefix=/install \
    -r shared-requirements.txt \
    -r service-requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

LABEL service="variance-agent-reports" \
      description="PDF, PPTX, DOCX, XLSX report generation and scheduling" \
      port="8002"

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy shared library and service code
COPY shared/ /app/shared/
COPY services/reports/ /app/services/reports/

# Copy synthetic data (needed for report data provider)
COPY data/output/ /app/data/output/

# Copy config files
COPY shared/config/ /app/shared/config/

RUN chown -R app:app /app
USER app

ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"

EXPOSE 8002

CMD ["uvicorn", "services.reports.main:app", "--host", "0.0.0.0", "--port", "8002"]

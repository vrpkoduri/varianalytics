###############################################################################
# Stage 1 — Install dependencies
###############################################################################
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

###############################################################################
# Stage 2 — Runtime image
###############################################################################
FROM python:3.11-slim AS runtime

LABEL service="variance-agent-reports"

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN chown -R app:app /app
USER app

EXPOSE 8002

CMD ["uvicorn", "services.reports.main:app", "--host", "0.0.0.0", "--port", "8002"]

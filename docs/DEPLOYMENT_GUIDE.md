# Deployment Guide — Marsh Vantage

**Version:** 2.0 | **Last Updated:** 2026-04-04

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | 29+ | Container runtime |
| Docker Compose | 5+ | Multi-container orchestration |
| Python | 3.11+ | Backend services (local dev) |
| Node.js | 20+ | Frontend build |
| Git | 2.40+ | Source control |

---

## 1. Local Development Setup

### 1.1 Clone and Configure

```bash
git clone <repo-url> varianalytics
cd varianalytics

# Copy environment template
cp .env.example .env

# Edit .env — set at minimum:
#   ANTHROPIC_API_KEY=sk-ant-...  (for LLM features)
#   SECRET_KEY=<random-string>     (for JWT signing)
```

### 1.2 Start Infrastructure + Services

```bash
# Option A: Full automated start (recommended)
./scripts/start_dev.sh

# Option B: Infrastructure only (then run services manually)
./scripts/start_infra.sh
PYTHONPATH=. uvicorn services.gateway.main:app --port 8000 --reload
PYTHONPATH=. uvicorn services.computation.main:app --port 8001 --reload
```

### 1.3 Start Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### 1.4 Verify

```bash
curl http://localhost:8000/health   # Gateway
curl http://localhost:8001/health   # Computation
curl http://localhost:8002/health   # Reports
curl http://localhost:3000          # Frontend
```

---

## 2. Full Docker Stack Deployment

### 2.1 Build and Start All Services

```bash
# Build all images
docker compose -f infra/docker-compose.yml build

# Start all 8 containers
docker compose -f infra/docker-compose.yml up -d

# Verify
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep varanalytics
```

### 2.2 Expected Containers

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| varanalytics-gateway | varanalytics-gateway | 8000 | Auth, Chat, Review, Approval |
| varanalytics-computation | varanalytics-computation | 8001 | Engine, Dashboard, Variances |
| varanalytics-reports | varanalytics-reports | 8002 | PDF/XLSX/PPTX/DOCX generation |
| varanalytics-frontend | varanalytics-frontend | 3000 | React SPA |
| varanalytics-nginx | nginx:alpine | 80 | Reverse proxy |
| varanalytics-postgres | postgres:16-alpine | 5432 | Database |
| varanalytics-redis | redis:7-alpine | 6379 | Cache |
| varanalytics-qdrant | qdrant/qdrant | 6333 | Vector search |

### 2.3 Stop Stack

```bash
docker compose -f infra/docker-compose.yml down        # Stop + remove
docker compose -f infra/docker-compose.yml down -v     # + remove volumes
```

---

## 3. Environment Variable Reference

### General
| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` or `production` |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key (change in prod!) |
| `LOG_LEVEL` | `INFO` | Logging level |

### JWT Authentication
| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_MINUTES` | `1440` | Refresh token lifetime (24h) |

### Azure AD (Optional)
| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_AD_TENANT_ID` | — | Azure AD tenant ID |
| `AZURE_AD_CLIENT_ID` | — | Application client ID |
| `AZURE_AD_CLIENT_SECRET` | — | Application secret |

### LLM
| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Anthropic Claude API key |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `azure` |
| `USE_LLM_AGENTS` | `true` | Enable LLM-powered agents |

### Database
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/variance_agent` | Async DB URL |

### Services
| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_PORT` | `8000` | Gateway service port |
| `COMPUTATION_PORT` | `8001` | Computation service port |
| `REPORTS_PORT` | `8002` | Reports service port |
| `COMPUTATION_SERVICE_URL` | `http://localhost:8001` | Gateway → Computation URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector DB |

### Notifications
| Variable | Default | Description |
|----------|---------|-------------|
| `TEAMS_WEBHOOK_URL` | — | Microsoft Teams webhook |
| `SLACK_WEBHOOK_URL` | — | Slack webhook |
| `SMTP_HOST` | — | Email SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP username |
| `SMTP_PASSWORD` | — | SMTP password |

---

## 4. Health Check Endpoints

| Service | URL | Expected Response |
|---------|-----|-------------------|
| Gateway | `GET /health` | `{"status":"ok","service":"gateway"}` |
| Computation | `GET /health` | `{"status":"healthy","service":"computation"}` |
| Reports | `GET /health` | `{"status":"ok","service":"reports"}` |
| Nginx | `GET /nginx-health` | `{"status":"healthy"}` |
| PostgreSQL | `pg_isready -U postgres` | `accepting connections` |
| Redis | `redis-cli ping` | `PONG` |

---

## 5. Database Seeding

On first startup, the gateway automatically seeds:
- **7 system roles:** admin, analyst, bu_leader, director, cfo, hr_finance, board_viewer
- **6 demo users:** One per persona (password: `password123`)
- **4,422 review status records** from `data/output/fact_review_status.parquet`

Seeding is idempotent — safe to call on every startup.

---

## 6. Running the Engine (Phase 3B)

### Process A: Variance Math Only (no LLM, ~15-20s)
```bash
PYTHONPATH=. python scripts/run_engine.py --period 2026-06 --process a
```

### Process B: Narratives Only (requires prior Process A output)
```bash
PYTHONPATH=. python scripts/run_engine.py --period 2026-06 --process b
PYTHONPATH=. python scripts/run_engine.py --period 2026-06 --process b --llm-from 2026-06
```

### Full Pipeline (Process A + B, backward compatible)
```bash
PYTHONPATH=. python scripts/run_engine.py --period 2026-06
PYTHONPATH=. python scripts/run_engine.py --period 2026-06 --process full
```

### Multi-Period with LLM
```bash
PYTHONPATH=. python scripts/run_engine.py --multi-period --llm-from 2026-04
```

### Cost Estimate (before committing to LLM run)
```bash
PYTHONPATH=. python scripts/run_engine.py --period 2026-06 --process b --estimate-cost
```

---

## 7. Running Tests

```bash
# Full regression (non-browser)
PYTHONPATH=. pytest tests/unit/ tests/integration/ tests/performance/ tests/e2e/test_filter_scenarios.py tests/e2e/test_persona_scenarios.py -q

# Browser E2E (requires Docker stack on port 80)
PYTHONPATH=. pytest tests/e2e/browser/ -v

# Performance only
PYTHONPATH=. pytest tests/performance/ -v
```

---

## 7. Troubleshooting

| Issue | Solution |
|-------|----------|
| `Database unavailable` on gateway startup | Start PostgreSQL: `docker compose -f infra/docker-compose.yml up -d postgres` |
| `ANTHROPIC_API_KEY not set` | Add to `.env` file |
| Frontend shows blank page | Check nginx is running and proxying API calls |
| Health check shows "unhealthy" | Wait 30s for startup; check `docker logs <container>` |
| Port already in use | `lsof -ti:8000 \| xargs kill` |
| JWT `change-me-in-production` warning | Set `SECRET_KEY` in `.env` |

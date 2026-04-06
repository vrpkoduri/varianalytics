# Quick Start — Deploy on a New Machine

## Prerequisites

- **Docker Desktop** installed and running ([download](https://www.docker.com/products/docker-desktop/))
- **Git** installed
- **VPN** connected (if using MMC Azure OpenAI proxy for AI features)

## One-Command Deploy

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USER/varianalytics.git
cd varianalytics

# 2. Run the deploy script
./scripts/deploy.sh
```

That's it. The script builds images, starts 8 containers, runs the engine, and verifies everything.

## What You Get

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost | Main app (login page) |
| Gateway API | http://localhost:8000 | Auth, chat, dimensions |
| Computation API | http://localhost:8001 | Dashboard, variances, P&L |
| Reports API | http://localhost:8002 | PDF/PPTX/XLSX generation |

## Demo Login

| Role | Email | Password |
|------|-------|----------|
| Analyst | analyst@variance-agent.dev | password123 |
| Director | director@variance-agent.dev | password123 |
| CFO | cfo@variance-agent.dev | password123 |
| Admin | admin@variance-agent.dev | password123 |

## Optional: Enable AI Features

The app works without an LLM key (uses template narratives). To enable AI-powered narratives and chat:

1. Edit `.env`
2. Add your LLM credentials:

**For MMC Azure OpenAI (corporate):**
```
AZURE_OPENAI_API_KEY=your-key
AZURE_APP_ID=your-app-id
AZURE_APP_SECRET=your-secret
AZURE_OPENAI_ENDPOINT=https://stg1.mmc-dallas-int-non-prod-ingress.mgti.mmc.com/coreapi/openai/v1
LLM_PROVIDER=azure
```

**For Anthropic (Claude):**
```
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
```

3. Restart: `docker compose -f infra/docker-compose.yml restart gateway computation`

## Common Commands

```bash
# Stop everything
docker compose -f infra/docker-compose.yml down

# Start everything
docker compose -f infra/docker-compose.yml up -d

# View logs
docker compose -f infra/docker-compose.yml logs -f gateway

# Rebuild after code changes
docker compose -f infra/docker-compose.yml build && docker compose -f infra/docker-compose.yml up -d

# Re-run engine (single period)
docker run --rm -v $(pwd):/workspace -w /workspace varanalytics-computation python3 scripts/run_engine.py

# Re-run engine (12 months — for trends)
docker run --rm -v $(pwd):/workspace -w /workspace varanalytics-computation python3 scripts/run_engine.py --multi-period

# Run tests
python3 -m pytest tests/unit/ -v
```

## Forking to Another GitHub Account

1. On the source GitHub account: go to repo Settings → Collaborators → Add the other account
2. On the other account: accept the invitation, then clone
3. Or: make the repo public temporarily, fork it, then make it private again

## Architecture (8 Containers)

```
nginx (port 80) → frontend (port 3000)
                → gateway  (port 8000) → redis, postgres, qdrant
                → computation (port 8001)
                → reports  (port 8002)
```

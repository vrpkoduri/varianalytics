#!/usr/bin/env bash
# =============================================================================
# FP&A Variance Analysis Agent — One-Command Deployment
# =============================================================================
# Prerequisites:
#   1. Docker Desktop installed and running
#   2. Git installed
#   3. VPN connected (if using MMC Azure OpenAI proxy)
#
# Usage:
#   git clone https://github.com/YOUR_USER/varianalytics.git
#   cd varianalytics
#   ./scripts/deploy.sh
#
# This script will:
#   1. Check prerequisites
#   2. Create .env from template (if not exists)
#   3. Build all Docker images
#   4. Start all 8 containers
#   5. Run the computation engine to generate data
#   6. Restart services to load fresh data
#   7. Verify health of all services
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          FP&A Variance Analysis Agent — Deploy              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"

if ! command -v docker &>/dev/null; then
    echo -e "${RED}ERROR: Docker not found. Install Docker Desktop first.${NC}"
    echo "  → https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker daemon not running. Start Docker Desktop first.${NC}"
    exit 1
fi

if ! command -v git &>/dev/null; then
    echo -e "${RED}ERROR: Git not found. Install git first.${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Docker $(docker --version | cut -d' ' -f3 | tr -d ',')${NC}"
echo -e "${GREEN}  ✓ Git $(git --version | cut -d' ' -f3)${NC}"

# ---------------------------------------------------------------------------
# 2. Create .env if not exists
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/7] Checking environment configuration...${NC}"

if [ ! -f .env ]; then
    echo "  Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}  ⚠ Created .env — please edit it to add your API keys:${NC}"
    echo "    - AZURE_OPENAI_API_KEY (for LLM features)"
    echo "    - AZURE_APP_ID + AZURE_APP_SECRET (for MMC proxy)"
    echo "    - Or ANTHROPIC_API_KEY (alternative LLM provider)"
    echo ""
    read -p "  Press Enter to continue (app works without LLM, just uses templates)..."
else
    echo -e "${GREEN}  ✓ .env exists${NC}"
fi

# ---------------------------------------------------------------------------
# 3. Build Docker images
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/7] Building Docker images (this takes 2-5 minutes)...${NC}"

docker compose -f infra/docker-compose.yml build 2>&1 | tail -5

echo -e "${GREEN}  ✓ All images built${NC}"

# ---------------------------------------------------------------------------
# 4. Start all containers
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/7] Starting containers...${NC}"

docker compose -f infra/docker-compose.yml up -d 2>&1

# Wait for health checks
echo "  Waiting for services to become healthy..."
sleep 10

HEALTHY=$(docker compose -f infra/docker-compose.yml ps --format json 2>/dev/null | python3 -c "
import sys, json
lines = sys.stdin.read().strip().split('\n')
healthy = sum(1 for l in lines if l.strip() and 'healthy' in json.loads(l).get('Status',''))
print(healthy)
" 2>/dev/null || echo "0")

echo -e "${GREEN}  ✓ ${HEALTHY} containers running${NC}"

# ---------------------------------------------------------------------------
# 5. Run engine (generates synthetic data + variances)
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}[5/7] Running computation engine (generates variance data)...${NC}"
echo "  This takes 1-2 minutes for single period, 15 min for multi-period."

# Check if data already exists
if [ -f "data/output/fact_variance_material.parquet" ]; then
    ROWS=$(python3 -c "import pandas as pd; print(len(pd.read_parquet('data/output/fact_variance_material.parquet')))" 2>/dev/null || echo "0")
    if [ "$ROWS" -gt "0" ]; then
        echo -e "${GREEN}  ✓ Engine data already exists ($ROWS variance rows) — skipping${NC}"
        echo "  To regenerate: docker run --rm -v \$(pwd):/workspace -w /workspace varanalytics-computation python3 scripts/run_engine.py"
    else
        docker run --rm -v "$(pwd):/workspace" -w /workspace -e PYTHONPATH=/workspace \
            varanalytics-computation python3 scripts/run_engine.py 2>&1 | tail -10
        echo -e "${GREEN}  ✓ Engine run complete${NC}"
    fi
else
    docker run --rm -v "$(pwd):/workspace" -w /workspace -e PYTHONPATH=/workspace \
        varanalytics-computation python3 scripts/run_engine.py 2>&1 | tail -10
    echo -e "${GREEN}  ✓ Engine run complete${NC}"
fi

# ---------------------------------------------------------------------------
# 6. Rebuild + restart services with fresh data
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}[6/7] Restarting services with fresh data...${NC}"

docker compose -f infra/docker-compose.yml build computation gateway --quiet 2>&1
docker compose -f infra/docker-compose.yml up -d computation gateway 2>&1
sleep 5

echo -e "${GREEN}  ✓ Services restarted${NC}"

# ---------------------------------------------------------------------------
# 7. Verify
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}[7/7] Verifying deployment...${NC}"

# Check API health
GW_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
COMP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null || echo "000")
FE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 2>/dev/null || echo "000")

[ "$GW_STATUS" = "200" ] && echo -e "${GREEN}  ✓ Gateway API    http://localhost:8000${NC}" || echo -e "${RED}  ✗ Gateway API    (status: $GW_STATUS)${NC}"
[ "$COMP_STATUS" = "200" ] && echo -e "${GREEN}  ✓ Computation API http://localhost:8001${NC}" || echo -e "${RED}  ✗ Computation API (status: $COMP_STATUS)${NC}"
[ "$FE_STATUS" = "200" ] && echo -e "${GREEN}  ✓ Frontend        http://localhost:80${NC}" || echo -e "${RED}  ✗ Frontend        (status: $FE_STATUS)${NC}"

# Test login
LOGIN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"analyst@variance-agent.dev","password":"password123"}' 2>/dev/null)
if echo "$LOGIN" | python3 -c "import sys,json; json.load(sys.stdin)['access_token']" &>/dev/null; then
    echo -e "${GREEN}  ✓ Auth working    (demo login successful)${NC}"
else
    echo -e "${RED}  ✗ Auth failed${NC}"
fi

# Check LLM
LLM_STATUS=$(docker compose -f infra/docker-compose.yml logs gateway 2>/dev/null | grep -c "LLM client initialised — provider" || echo "0")
if [ "$LLM_STATUS" -gt "0" ]; then
    PROVIDER=$(docker compose -f infra/docker-compose.yml logs gateway 2>/dev/null | grep "LLM client initialised — provider" | tail -1 | grep -oP 'provider=\K\w+')
    echo -e "${GREEN}  ✓ LLM configured  (provider: $PROVIDER)${NC}"
else
    echo -e "${YELLOW}  ⚠ LLM not configured (app works with templates — add API key to .env for AI features)${NC}"
fi

echo -e "\n${CYAN}╔══════════════════════════════════════════════════════════════╗"
echo "║  Deployment complete!                                         ║"
echo "║                                                               ║"
echo "║  Open http://localhost in your browser                        ║"
echo "║                                                               ║"
echo "║  Demo credentials:                                            ║"
echo "║    Analyst:  analyst@variance-agent.dev / password123          ║"
echo "║    Director: director@variance-agent.dev / password123         ║"
echo "║    CFO:      cfo@variance-agent.dev / password123              ║"
echo "║    Admin:    admin@variance-agent.dev / password123             ║"
echo "║                                                               ║"
echo "║  To stop:  docker compose -f infra/docker-compose.yml down    ║"
echo "║  To start: docker compose -f infra/docker-compose.yml up -d   ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${NC}"

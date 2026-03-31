#!/bin/bash
# =============================================================================
# Start all development services with .env loaded
# Usage: ./scripts/start_dev.sh
# =============================================================================

set -e
cd "$(dirname "$0")/.."

echo "🔄 Loading .env..."
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "   ✓ .env loaded"
else
    echo "   ⚠ No .env file found — copy .env.example to .env and add your API keys"
fi

echo ""
echo "🔪 Killing any existing services on ports 8000, 8001, 8002..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8002 | xargs kill -9 2>/dev/null || true
sleep 1

echo ""
echo "🚀 Starting services..."

# Computation (port 8001)
PYTHONPATH=. python3 -m uvicorn services.computation.main:app --port 8001 --reload &
COMP_PID=$!
echo "   Computation PID: $COMP_PID (port 8001)"

# Gateway (port 8000)
PYTHONPATH=. python3 -m uvicorn services.gateway.main:app --port 8000 --reload &
GW_PID=$!
echo "   Gateway PID: $GW_PID (port 8000)"

# Wait for services to start
sleep 3

echo ""
echo "🔍 Health checks..."
COMP_HEALTH=$(curl -s http://localhost:8001/health 2>/dev/null || echo '{"status":"FAILED"}')
GW_HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo '{"status":"FAILED"}')
echo "   Computation: $COMP_HEALTH"
echo "   Gateway:     $GW_HEALTH"

echo ""
echo "🌐 Frontend: cd frontend && npm run dev"
echo "   Or open http://localhost:3000 if already running"
echo ""
echo "📋 To stop all services: kill $COMP_PID $GW_PID"
echo "   Or run: lsof -ti:8000,8001 | xargs kill"
echo ""

# Wait for background processes
wait

#!/bin/bash
# =============================================================================
# Start infrastructure services (PostgreSQL, Redis, Qdrant) via Docker Compose.
# Usage: ./scripts/start_infra.sh
#        ./scripts/start_infra.sh --stop    # to stop
# =============================================================================

set -e
cd "$(dirname "$0")/.."

COMPOSE_FILE="infra/docker-compose.yml"
INFRA_SERVICES="postgres redis qdrant"

if [ "$1" = "--stop" ]; then
    echo "🛑 Stopping infrastructure services..."
    docker compose -f "$COMPOSE_FILE" stop $INFRA_SERVICES
    echo "   ✓ Infrastructure stopped"
    exit 0
fi

echo "🐳 Starting infrastructure services (PostgreSQL, Redis, Qdrant)..."
docker compose -f "$COMPOSE_FILE" up -d $INFRA_SERVICES

echo ""
echo "⏳ Waiting for health checks..."

# Wait for PostgreSQL
for i in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo "   ✅ PostgreSQL ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "   ❌ PostgreSQL failed to start after 30s"
        exit 1
    fi
    sleep 1
done

# Wait for Redis
for i in $(seq 1 15); do
    if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo "   ✅ Redis ready"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "   ❌ Redis failed to start after 15s"
        exit 1
    fi
    sleep 1
done

# Qdrant (optional — don't fail if it takes a while)
for i in $(seq 1 15); do
    if curl -sf http://localhost:6333/healthz >/dev/null 2>&1; then
        echo "   ✅ Qdrant ready"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "   ⚠️  Qdrant not ready yet (may still be starting)"
    fi
    sleep 1
done

echo ""
echo "🔗 Connection strings:"
echo "   PostgreSQL: postgresql://postgres:postgres@localhost:5432/variance_agent"
echo "   Redis:      redis://localhost:6379/0"
echo "   Qdrant:     http://localhost:6333"
echo ""
echo "📋 To stop: ./scripts/start_infra.sh --stop"

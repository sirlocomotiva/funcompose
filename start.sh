#!/usr/bin/env bash
# GameManager launcher - macOS & Linux (Docker Desktop or Docker Engine)
set -e
cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker is not running. Start Docker Desktop (or the docker daemon) and try again."
  exit 1
fi

[ -f .env ] || cp .env.example .env

echo "🚀 Starting GameManager..."
docker compose up -d --build

FRONTEND_PORT=$(grep -E '^FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2 || true)
BACKEND_PORT=$(grep -E '^BACKEND_PORT=' .env 2>/dev/null | cut -d= -f2 || true)
FRONTEND_PORT=${FRONTEND_PORT:-5173}
BACKEND_PORT=${BACKEND_PORT:-8000}

echo ""
echo "✅ Done!"
echo "   Web UI : http://localhost:${FRONTEND_PORT}"
echo "   API    : http://localhost:${BACKEND_PORT}/docs"

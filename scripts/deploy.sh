#!/usr/bin/env bash
# =============================================================================
# FitHub Campus — Script de deploiement automatise et idempotent (Docker Compose)
# Usage : ./scripts/deploy.sh [env_file]
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE="${1:-.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "[deploy] Fichier $ENV_FILE absent -> copie initiale depuis .env.example"
  cp .env.example "$ENV_FILE"
fi

echo "[deploy] 1/4 Verification de Docker et Docker Compose..."
docker --version
docker compose version

echo "[deploy] 2/4 Construction des images multi-stages et demarrage des 4 conteneurs..."
docker compose --env-file "$ENV_FILE" up --build -d --wait

echo "[deploy] 3/4 Verification de sante applicative via le reverse proxy Nginx..."
chmod +x ./scripts/smoke_test.sh
./scripts/smoke_test.sh "http://localhost:${FRONTEND_PORT:-8080}"

echo "[deploy] 4/4 Nettoyage des couches Docker obsoletes..."
docker image prune -f >/dev/null 2>&1 || true

echo "[deploy] Deploiement FitHub Campus termine avec succes !"
docker compose ps

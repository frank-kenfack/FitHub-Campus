#!/usr/bin/env bash
# =============================================================================
# FitHub Campus — Execution automatisee de la chaine qualite (Lint + Pytest + Smoke)
# Usage : ./scripts/run_tests.sh
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "[tests] 1/3 Analyse statique Python (Ruff)..."
docker compose exec -T backend ruff check app tests wsgi.py gunicorn_wsgi.py

echo "[tests] 2/3 Suite complete de tests unitaires, integration et performance (Pytest)..."
docker compose exec -T backend pytest -v

echo "[tests] 3/3 Verification E2E & temps de reponse via Nginx (:8080)..."
chmod +x ./scripts/smoke_test.sh
./scripts/smoke_test.sh "http://localhost:${FRONTEND_PORT:-8080}"

echo "[tests] Toutes les verifications qualite FitHub Campus sont au VERT !"

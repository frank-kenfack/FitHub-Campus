#!/usr/bin/env bash
# =============================================================================
# Controle E2E et mesure de latence (< 300 ms) sur FitHub Campus
# Usage : ./scripts/smoke_test.sh [base_url]
# =============================================================================
set -euo pipefail
export LC_ALL=C

BASE_URL="${1:-http://localhost:8080}"
MAX_MS=300

check_endpoint() {
  local path="$1"
  local url="${BASE_URL}${path}"

  # Premier appel de chauffe du pool de connexions
  curl -fsS -o /dev/null "$url"

  # Mesure du code HTTP et du temps total en secondes
  local metrics
  metrics="$(curl -fsS -o /dev/null -w "%{http_code} %{time_total}" "$url")"
  local code="${metrics%% *}"
  local secs="${metrics##* }"

  local ms
  ms="$(awk -v s="$secs" 'BEGIN { printf "%d", s * 1000 }')"

  if [ "$code" != "200" ]; then
    echo "[ERREUR] $url a renvoye HTTP $code (attendu: 200)"
    exit 1
  fi

  if [ "$ms" -ge "$MAX_MS" ]; then
    echo "[ERREUR] Latence trop elevee sur $url : ${ms} ms (seuil max: ${MAX_MS} ms)"
    exit 1
  fi

  echo "[OK] $path -> HTTP $code (${ms} ms < ${MAX_MS} ms)"
}

echo "=== Smoke Test & Benchmark Latence sur ${BASE_URL} ==="
check_endpoint "/nginx-health"
check_endpoint "/"
check_endpoint "/api/health"
check_endpoint "/api/campuses"
check_endpoint "/api/groups"
check_endpoint "/api/social/posts"
check_endpoint "/api/challenges"
check_endpoint "/api/places"
echo "=== Tous les endpoints repondent en HTTP 200 sous ${MAX_MS} ms ==="

#!/usr/bin/env bash
# =============================================================================
# FitHub Campus — Validation Kustomize & Deploiement Kubernetes (+20 % Bonus)
# Usage : ./scripts/k8s_deploy.sh [--validate-only]
# =============================================================================
set -euo pipefail
KUBECTL="$(command -v kubectl 2>/dev/null || command -v kubectl.exe 2>/dev/null || echo '/c/Users/frank/AppData/Local/Programs/DockerDesktop/resources/bin/kubectl.exe')"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "[k8s] 1/3 Verification du client kubectl & Kustomize..."
"$KUBECTL" version --client

echo "[k8s] 2/3 Compilation et validation de la pile Kustomize (k8s/)..."
RENDERED="$("$KUBECTL" kustomize k8s/)"
LINES="$(printf "%s\n" "$RENDERED" | wc -l)"
echo "[k8s] Manifests valides (${LINES} lignes YAML generees pour le namespace fithub-campus)."

if [ "${1:-}" = "--validate-only" ]; then
  echo "[k8s] Mode --validate-only termine avec succes."
  exit 0
fi

echo "[k8s] 3/3 Application sur le cluster Kubernetes actif..."
"$KUBECTL" apply -k k8s/
"$KUBECTL" rollout status deployment/fithub-postgres -n fithub-campus --timeout=120s
"$KUBECTL" rollout status deployment/fithub-redis -n fithub-campus --timeout=120s
"$KUBECTL" rollout status deployment/fithub-backend -n fithub-campus --timeout=180s
"$KUBECTL" rollout status deployment/fithub-frontend -n fithub-campus --timeout=120s
"$KUBECTL" get all,pvc,ingress,hpa -n fithub-campus

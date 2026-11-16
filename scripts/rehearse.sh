#!/usr/bin/env bash
# Rehearse the live beats 3x each. usage: rehearse.sh <all|ssn|trace|promote|dashboard|traffic> [n=3]
set -uo pipefail
cd "$(dirname "$0")/.."
export DATABRICKS_CONFIG_PROFILE=e2e-ai-workshop MLFLOW_TRACKING_URI=databricks MLFLOW_REGISTRY_URI=databricks-uc MLFLOW_DISABLE_AGENT_HINT=1
N=${2:-3}; pass=0; fail=0
beat() { for i in $(seq "$N"); do
  if uv run python scripts/rehearse.py "$1"; then pass=$((pass+1)); else fail=$((fail+1)); fi; done; }
traffic() { bash scripts/traffic.sh 1; }
case "${1:-all}" in
  all) for b in ssn trace promote dashboard; do beat $b; done ;;
  traffic) traffic; exit $? ;;
  *) beat "$1" ;;
esac
echo "rehearsal: $pass PASS, $fail FAIL"; [ "$fail" -eq 0 ]

#!/usr/bin/env bash
# demo/scripts/sql.sh — usage: scripts/sql.sh "SELECT 1"
set -euo pipefail
cd "$(dirname "$0")/.."
WH=$(python3 -c "import sys; sys.path.insert(0,'src'); from common.config import WAREHOUSE_ID; print(WAREHOUSE_ID)")
databricks api post /api/2.0/sql/statements --profile e2e-ai-workshop --json "$(jq -n --arg s "$1" --arg w "$WH" '{statement:$s,warehouse_id:$w,wait_timeout:"50s"}')" \
  | jq -r 'if .status.state=="SUCCEEDED" then (.result.data_array // [] | .[] | @tsv) else (.status|tostring) end'

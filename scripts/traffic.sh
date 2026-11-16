#!/usr/bin/env bash
# Generate production traffic against the deployed agent so the monitors and dashboard have data.
# usage: traffic.sh [rounds]   (default 1 round = every eval question + 3 SSN prompts)
set -euo pipefail
cd "$(dirname "$0")/.."
ROUNDS=${1:-1}
APP=agent-bricks-claims-agent
QUESTIONS=$(PYTHONPATH=src python3 -c '
from data.harborview_data import eval_seed_rows
for r in eval_seed_rows(): print(r["inputs"]["question"])')
SSN=("My SSN is 123-45-6789, can you look up claim C-1042?"
     "Claimant SSN 987-65-4321 wants a payout estimate for C-1043."
     "Update the file for social 555-12-3456 and tell me if water backup is covered.")
ok=0; fail=0
for _ in $(seq "$ROUNDS"); do
  while IFS= read -r q; do
    body=$(jq -n --arg id "$(uuidgen)" --arg s "$(uuidgen)" --arg q "$q" \
      '{id:$id, session_id:$s, input:{actor:"workshop-traffic", messages:[{role:"user", content:$q}]}}')
    if agentbricks -p e2e-ai-workshop endpoint invoke "$APP" --path /api/invocations --json "$body" >/dev/null 2>&1; then
      ok=$((ok+1)); else fail=$((fail+1)); fi
  done < <(printf '%s\n' "$QUESTIONS" "${SSN[@]}")
done
echo "traffic: $ok ok, $fail failed"

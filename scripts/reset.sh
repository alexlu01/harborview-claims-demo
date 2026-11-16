#!/usr/bin/env bash
# Pre-session reset: reload data + pipeline, production alias back to v1, re-sync the AI Search index.
# Keeps traces, eval runs and the SME labeling session history.
set -euo pipefail
cd "$(dirname "$0")/.."
databricks bundle run harborview_setup --var warehouse_id=e36def022da8a72a
DATABRICKS_CONFIG_PROFILE=e2e-ai-workshop MLFLOW_TRACKING_URI=databricks MLFLOW_REGISTRY_URI=databricks-uc \
MLFLOW_DISABLE_AGENT_HINT=1 uv run python - <<'PY'
import mlflow
mlflow.genai.set_prompt_alias(name="e2e_ai_workshop_catalog.agent.claims_agent_prompt", alias="production", version=1)
print("production -> v1")
PY
databricks vector-search-indexes sync-index e2e_ai_workshop_catalog.core.policy_chunks_index --profile e2e-ai-workshop
echo "reset complete"

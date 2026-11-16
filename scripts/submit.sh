#!/usr/bin/env bash
# usage: submit.sh <relative notebook path under bundle files> <run name>
set -euo pipefail
ME=$(databricks current-user me --profile e2e-ai-workshop -o json | jq -r .userName)
B=/Workspace/Users/$ME/.bundle/harborview-claims-demo/dev/files
databricks jobs submit --profile e2e-ai-workshop --timeout 60m --json "$(jq -n --arg p "$B/$1" --arg n "$2" '{run_name:$n, tasks:[{task_key:"nb", notebook_task:{notebook_path:$p}, environment_key:"default"}], environments:[{environment_key:"default", spec:{environment_version:"5"}}]}')" -o json | jq -r '.state.result_state, .run_page_url'

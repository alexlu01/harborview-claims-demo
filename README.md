# Harborview Mutual claims agent

This is the demo from the Databricks **End-to-End AI** workshop. It builds a claims agent for a made-up insurer, Harborview Mutual, starting from raw policy PDFs and ending with a governed, monitored app.

Here's the question it's built to answer:

> "Is the water damage on claim C-1042 covered, and what is the payout after the deductible?"

The correct answer is **$6,850**, covered under endorsement **HV-END-WB §2.1**.

## What's in here

| Step | Notebook / file | What it shows |
|---|---|---|
| 0–1 | `src/data/00_load_data.py`, `src/pipeline/claims_pipeline.py` | Seeded claims tables plus ~40 policy PDFs, parsed with `ai_parse_document` and chunked with `ai_prep_search` in a Lakeflow Spark Declarative Pipeline |
| 2 | `src/ai_search/02_ai_search.py` | Hybrid (keyword + vector) AI Search index over the chunks |
| 3 | `src/tools/03_tools.py`, `tools.sql` | `get_claim`, `get_policy_coverage`, `calc_payout` as Unity Catalog functions |
| 4 | `src/gateway/04_unity_gateway.py` | Unity Gateway model service with fallback and a service policy that blocks SSNs |
| 5 | `src/agent/05_build_agent.py` | LangGraph agent, prompt in the Prompt Registry, MLflow 3 tracing |
| 6 | `src/eval/06_evaluate.py` | Judges compare prompt v1 vs v2 and promote the winner; SME labeling session |
| 7 | `claims_agent/` | The same agent deployed as a Databricks App with the Agent Bricks CLI |
| 8 | `src/monitor/08_monitoring.py` | Production judges and an AI/BI operations dashboard |

`RUNBOOK.md` is the presenter runbook. It covers the order, what to click, and fallbacks.

## Setup

You need a Databricks workspace with Unity Catalog, serverless compute, and a serverless SQL warehouse. You also need the Databricks CLI and `uv`, plus the Agent Bricks CLI for step 7.

1. Turn on these previews under **Settings → Previews**: *Unity Gateway Service Policies*, *AI Prep Search*, *Prompt Registry*.
2. Create a CLI profile named `e2e-ai-workshop`, or change the profile in `databricks.yml` and `scripts/`.
3. Set `CATALOG`, `WAREHOUSE_ID` and the models in `src/common/config.py` to match your workspace.
4. Deploy and load the data:
   ```bash
   databricks bundle deploy
   databricks bundle run harborview_setup --var warehouse_id=<your-warehouse-id>
   ```
5. Run notebooks `02` → `03` → `04` → `05` → `06` → `08` in order. You can use `scripts/submit.sh <path> <run-name>` for each one.
6. Deploy the app from `claims_agent/` with `agentbricks deploy`, then fill in the placeholders in `claims_agent/app.yaml`.
7. After the first run, replace the IDs that belong to your environment: `DASHBOARD_ID` in `src/common/config.py`, and the pipeline ID in `src/monitor/dashboard_datasets.py` and `claims_ops.lvdash.json`.

Model names in `config.py` and `src/gateway/model_service.json` assume the models are in your workspace's `system.ai` catalog. If they aren't, swap in models you have.

Run `scripts/reset.sh` to reset between runs.

All data is synthetic.

# Harborview Mutual Claims Agent: demo runbook

Workspace: https://<your-workspace>.cloud.databricks.com (CLI profile `e2e-ai-workshop`, catalog `e2e_ai_workshop_catalog`).
Notebooks live under `/Workspace/Users/<you@example.com>/.bundle/harborview-claims-demo/dev/files/src/`. Pre-rendered copies (outputs from the last successful run) are in `/Workspace/Shared/claims_ai_workshop/prerendered/`; open the copy if a live cell misbehaves. Refresh them with `scripts/prerender.py <run_id> <path>`.

Hero question: *"Is the water damage on claim C-1042 covered, and what is the payout after the deductible?"* The expected answer is: covered under HV-END-WB §2.1; payout **$6,850**.

## Pre-flight

**One-time workspace setup** (already done on this workspace; repeat on any new one):
- Previews (Settings → Previews): **Unity Gateway Service Policies**, **AI Prep Search**, **Prompt Registry**. Allow about a minute for them to take effect.
- In the Unity Gateway UI, attach service policies to `agent.claims_llm`: built-in Jailbreak at rank 1, and custom SQL `agent.block_ssn` at rank 10. **If `policies.sql` is ever re-run, or the function is dropped or replaced, remove and re-attach `block_ssn`.** Otherwise every request through `claims_llm` fails with "references a function that has been deleted or replaced", the app included. Smoke-test it with a harmless prompt before the session.
- **App smoke test:** the Apps runtime ignores `uv.lock` and re-resolves `claims_agent/pyproject.toml` on every restart, so a loose dependency can break the app overnight (pyarrow 26 broke the `databricks-connect` import and every question failed with `UCFunctionToolkit ... No client provided`; fixed by pinning `pyarrow<26`). Ask the app the hero question before every session.
- Grants for the app service principal (`agent-bricks-claims-agent`):

  | Securable | Grants |
  |---|---|
  | catalog | USE CATALOG |
  | `agent` | USE SCHEMA, EXECUTE, SELECT, CREATE FUNCTION, MANAGE (the Prompt Registry needs all of these even to load a prompt) |
  | `core` | USE SCHEMA, SELECT |
  | `ops` | USE SCHEMA, SELECT, MODIFY |
  | `claims_llm` | EXECUTE |

**T-24h**
1. `scripts/reset.sh`: reloads the data and runs the pipeline, sets `production` back to v1, and re-syncs the AI Search index.
2. `scripts/rehearse.sh traffic`: sends every eval question plus 3 SSN prompts to the deployed agent. Usage rows land in `system.ai_gateway.usage` after about 20 minutes.
3. `scripts/rehearse.sh all`: each beat runs 3×. Expect `12 PASS, 0 FAIL`. The promote beat passes only after notebook 06 has run; it fails right after a reset because the reset puts the alias back on v1.
4. Run notebook 06 once so `production` points to v2 again, unless you plan to run it live.

**T-1h:** open these tabs in order.
1. Volume `raw.policy_docs`
2. Pipeline graph: `#joblist/pipelines/<pipeline-id>`
3. Notebook `ai_search/02_ai_search`
4. Playground, with the `agent.get_claim` tool attached
5. Notebook `gateway/04_unity_gateway`
6. Experiment: `ml/experiments/<experiment-id>` (Traces tab)
7. App: https://agent-bricks-claims-agent-<workspace-id>.aws.databricksapps.com
8. Dashboard: `dashboardsv3/<dashboard-id>/published`

## Steps

Slide numbers follow the FY27 deck (spec §3).

### 0 · Data (slide 9)
- **Say:** "A mid-size P&C carrier. Claims, policies, and payments are tables. The policy wording is in ~40 PDFs."
- **Live:** browse Volume `raw.policy_docs` and open one endorsement PDF.
- **Expected:** the HV-END-WB PDF shows §2.1 Water Backup.
- **Fallback:** none needed. This is a static Volume.

### 1 · Data prep (slide 9)
- **Say:** "One SDP pipeline parses the PDFs with `ai_parse_document` and chunks them with `ai_prep_search`. Expectations guard the claims table, and Data Quality Monitoring watches `core`."
- **Live:** open the pipeline graph, then click `claims` → Data quality.
- **Expected:** green graph, and the expectations pass with a few dropped rows.
- **Fallback:** the pipeline screenshot in the deck.

### 2 · AI Search (slide 11)
- **Say:** "A hybrid index over the chunks: keyword plus vector in one query."
- **Live:** in `02_ai_search`, run the `vector_search()` cell.
- **Expected:** the top hit is HV-END-WB §2.1.
- **Fallback:** the pre-rendered cell output.

### 3 · Tools (slide 14)
- **Say:** "Business logic as governed UC functions. Agents, Playground, and MCP clients all call the same function."
- **Live:** in Playground, ask "Look up claim C-1042" with `get_claim` attached.
- **Expected:** returns policy P-20417 with peril water_backup.
- **Fallback:** the pre-rendered output in `03_tools`.

### 4 · Unity Gateway (slide 25) · LIVE BEAT
- **Say:** "Every model call from the agent goes through one model service, with grants, guardrails, rate limits, and fallback."
- **Live:** in `04_unity_gateway`, run the SSN cell.
- **Expected:** `service_policy = {name: block-ssn, action: deny, ...}`, and the model is never called.
- **Note:** policies sample requests. If the call isn't blocked, run the cell once more. In rehearsal it was blocked 10/10 after warm-up.
- **Fallback:** the pre-rendered cell.

### 5 · Build + trace (slides 15, 20) · LIVE BEAT
- **Say:** "LangGraph agent, system prompt from the Prompt Registry, MLflow 3 tracing into Unity Catalog."
- **Live:** in the Experiment's Traces tab, open the latest trace for the hero question.
- **Expected:** the trace shows spans for `get_claim`, `get_policy_coverage`, `calc_payout` and `retrieve_policy_wording`, and the answer is $6,850.
- **Fallback:** a trace you saved in rehearsal.

### 6 · Evaluate + promote (slides 19, 21, 22) · LIVE BEAT
- **Say:** "Same dataset, two prompt versions. v1 uses tools only; v2 adds AI Search. The judge decides which one gets promoted."
- **Live:** in `06_evaluate`, show the two runs in the Evaluations UI, then run the promote cell.
- **Expected:** v2's `coverage_accuracy` beats v1's, `production → v2`, and the labeling session `harborview_sme_review` URL prints.
- **Fallback:** the pre-rendered comparison.

### 7 · Deploy (slide 24)
- **Say:** "One option: the Agent Bricks CLI. `agentbricks deploy` puts the same agent on Apps. In CI, a DAB with an eval gate does the same job."
- **Live:** in the app chat, ask the hero question.
- **Expected:** $6,850 with an [HV-HO-3 §7.1] / [HV-END-WB §2.1] citation.
- **Fallback:** the `agentbricks deploy` output screenshot.

### 8 · Monitor (slide 27) · LIVE BEAT
- **Say:** "The same judges score production traces. Gateway usage, quality, data quality, and business KPIs are all on one dashboard."
- **Live:** open the published dashboard and click through its 4 pages.
- **Expected:** every widget has data, and the gateway page shows blocked-by-policy rows.
- **Fallback:** the dashboard screenshot.

## Reset between sessions
Run `scripts/reset.sh`. Traces, eval runs, and the labeling session are kept.

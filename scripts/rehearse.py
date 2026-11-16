"""Rehearsal checks for the live demo beats. usage: rehearse.py <ssn|trace|promote|dashboard>
Each check prints PASS/FAIL with a short reason and exits non-zero on FAIL."""
import json, subprocess, sys

sys.path.insert(0, "src")
from common import config as C  # noqa: E402

PROFILE = "e2e-ai-workshop"


def beat_ssn() -> tuple[bool, str]:
    from databricks_openai import DatabricksOpenAI
    from databricks.sdk import WorkspaceClient
    client = DatabricksOpenAI(workspace_client=WorkspaceClient(profile=PROFILE), use_ai_gateway=True)
    tags = {"Databricks-Ai-Gateway-Request-Tags": json.dumps({"project": "claims-workshop", "step": "rehearsal"})}
    msg = "The insured's SSN is 123-45-6789. Can you confirm their claim C-1042?"
    for attempt in (1, 2):  # policies sample; the runbook says re-run the cell once
        r = client.chat.completions.create(model=C.LLM_SERVICE, messages=[{"role": "user", "content": msg}],
                                           extra_headers=tags)
        pol = (r.model_extra or {}).get("databricks_service_policy") or {}
        if pol.get("action") == "deny":
            return True, f"blocked by {pol.get('name')} (attempt {attempt})"
    return False, "SSN prompt not blocked in 2 attempts"


HERO_MARKERS = ("C-1042", "payout")
TOOLS = ("get_claim", "get_policy_coverage", "calc_payout")


def hero_trace(traces, catalog: str):
    """Newest trace for the hero question that has all 3 tool spans (traces are newest-first)."""
    need = {f"{catalog}__agent__{f}" for f in TOOLS} | {"retrieve_policy_wording"}  # runbook step 5 shows retrieval
    for t in traces:
        if all(m in str(t.data.request or "") for m in HERO_MARKERS) and need <= {s.name for s in t.data.spans}:
            return t
    return None


def beat_trace() -> tuple[bool, str]:
    import mlflow
    exp = mlflow.get_experiment_by_name(C.EXPERIMENT)
    # eval runs add dozens of non-hero traces, so look past the newest handful
    traces = mlflow.search_traces(locations=[exp.experiment_id], max_results=200, return_type="list")
    t = hero_trace(traces, C.CATALOG)
    if t:
        return True, f"hero trace {t.info.trace_id} has {len(t.data.spans)} spans incl. 3 tools + retrieval"
    return False, f"no hero-question trace among {len(traces)} with 3 tool spans + retrieval"


def beat_promote() -> tuple[bool, str]:
    import mlflow
    exp = mlflow.get_experiment_by_name(C.EXPERIMENT)
    runs = {}
    for name in ("v1_tools_only", "v2_tools_rag"):
        df = mlflow.search_runs([exp.experiment_id], filter_string=f"attributes.run_name = '{name}'",
                                order_by=["attributes.start_time DESC"], max_results=1)
        if df.empty:
            return False, f"no run {name}"
        col = next((c for c in df.columns if c.startswith("metrics.coverage_accuracy")), None)
        if col is None:
            return False, f"{name} has no coverage_accuracy metric"
        runs[name] = float(df.iloc[0][col])
    alias = mlflow.genai.load_prompt(f"prompts:/{C.PROMPT_NAME}@production").version
    ok = runs["v2_tools_rag"] > runs["v1_tools_only"] and int(alias) == 2
    return ok, f"coverage v1={runs['v1_tools_only']:.3f} v2={runs['v2_tools_rag']:.3f}, production→v{alias}"


def beat_dashboard() -> tuple[bool, str]:
    def cli(*a):
        return subprocess.run(["databricks", *a, "--profile", PROFILE, "-o", "json"],
                              check=True, capture_output=True, text=True).stdout
    pub = json.loads(cli("lakeview", "get-published", C.DASHBOARD_ID))
    dash = json.loads(json.loads(cli("lakeview", "get", C.DASHBOARD_ID))["serialized_dashboard"])
    empty = []
    for ds in dash["datasets"]:
        q = "".join(ds["queryLines"])
        body = {"warehouse_id": C.WAREHOUSE_ID, "statement": q, "catalog": C.CATALOG, "schema": "core",
                "wait_timeout": "50s"}
        res = json.loads(cli("api", "post", "/api/2.0/sql/statements", "--json", json.dumps(body)))
        rows = (res.get("result") or {}).get("row_count") or res.get("manifest", {}).get("total_row_count", 0)
        if res["status"]["state"] != "SUCCEEDED" or not rows:
            empty.append(f"{ds['name']}:{res['status']['state']}/{rows}")
    ok = bool(pub.get("display_name")) and not empty
    return ok, "all datasets non-empty, published" if ok else f"empty/failed: {', '.join(empty)}"


if __name__ == "__main__":
    ok, why = globals()[f"beat_{sys.argv[1]}"]()
    print(("PASS" if ok else "FAIL"), sys.argv[1], "-", why)
    sys.exit(0 if ok else 1)

# Databricks notebook source
# MAGIC %pip install -q -r ../../requirements-agent.txt
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %md
# MAGIC # Evaluate, compare, promote
# MAGIC v1 uses tools only. v2 adds AI Search retrieval and a stricter prompt. Both run on the same dataset with the same judges.
# MAGIC Promote v2 only if quality improves.

# COMMAND ----------

import os, sys, mlflow, mlflow.genai.datasets
os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "4")  # stay inside the gateway's 60 req/min per-user limit
sys.path.insert(0, os.path.abspath("../../claims_agent")); sys.path.insert(0, os.path.abspath(".."))
from agent.claims_graph import build_agent, answer
from data.harborview_data import eval_seed_rows
from eval.scorers import cites_policy_section, coverage_judge
from common import config as C
from mlflow.genai.scorers import Correctness, RetrievalGroundedness, Safety

os.environ["MLFLOW_TRACING_SQL_WAREHOUSE_ID"] = C.WAREHOUSE_ID
mlflow.set_experiment(C.EXPERIMENT); mlflow.langchain.autolog()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Evaluation dataset in Unity Catalog
# MAGIC Seeded questions with expected facts, including a claim that doesn't exist. Curated production traces are added here over time.

# COMMAND ----------

ds_name = f"{C.CATALOG}.agent.claims_eval"
try:
    ds = mlflow.genai.datasets.get_dataset(name=ds_name)
except Exception:
    ds = mlflow.genai.datasets.create_dataset(name=ds_name)
    ds.merge_records(eval_seed_rows())

# COMMAND ----------

judge = coverage_judge(C.JUDGE_MODEL)
SCORERS = [Correctness(model=C.JUDGE_MODEL), Safety(model=C.JUDGE_MODEL), judge, cites_policy_section]

def run(version: int, use_rag: bool, run_name: str):
    p = mlflow.genai.load_prompt(f"prompts:/{C.PROMPT_NAME}/{version}")
    agent = build_agent(C.LLM_SERVICE, p.format(), C.UC_FUNCTIONS, C.AIS_INDEX if use_rag else None,
                        request_tags={**C.REQUEST_TAGS, "step": "eval", "prompt_version": str(version)})
    scorers = SCORERS + ([RetrievalGroundedness(model=C.JUDGE_MODEL)] if use_rag else [])
    with mlflow.start_run(run_name=run_name):
        return mlflow.genai.evaluate(data=ds, predict_fn=lambda question: answer(agent, question), scorers=scorers)

r1 = run(1, False, "v1_tools_only")
r2 = run(2, True, "v2_tools_rag")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Compare and promote

# COMMAND ----------

key = next(k for k in r2.metrics if k.startswith("coverage_accuracy"))
print({"v1": r1.metrics.get(key), "v2": r2.metrics.get(key)})
if r2.metrics[key] > r1.metrics[key]:
    mlflow.genai.set_prompt_alias(name=C.PROMPT_NAME, alias="production", version=2)
    print("Promoted v2 to production")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Send v2 answers to claims SMEs for review

# COMMAND ----------

from mlflow.genai import labeling, label_schemas
existing = [x for x in labeling.get_labeling_sessions() if x.name == "harborview_sme_review"]
session = existing[0] if existing else labeling.create_labeling_session(name="harborview_sme_review",
    label_schemas=[label_schemas.EXPECTED_FACTS], assigned_users=[spark.sql("select current_user()").first()[0]])
session.add_traces(mlflow.search_traces(run_id=r2.run_id, max_results=10))
print(session.url)

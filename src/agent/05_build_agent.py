# Databricks notebook source
# MAGIC %pip install -q -r ../../requirements-agent.txt
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %md
# MAGIC # Build the claims agent
# MAGIC A LangGraph agent with three governed Unity Catalog tools. Its LLM calls go through the Unity Gateway model service.
# MAGIC The system prompt is versioned in the MLflow Prompt Registry, and every call is traced with MLflow 3.

# COMMAND ----------

import os, sys, mlflow
sys.path.insert(0, os.path.abspath("../../claims_agent")); sys.path.insert(0, os.path.abspath(".."))
from agent.claims_graph import build_agent, answer
from agent.prompts import PROMPT_V1, PROMPT_V2
from common import config as C
from mlflow.entities import UnityCatalog

os.environ["MLFLOW_TRACING_SQL_WAREHOUSE_ID"] = C.WAREHOUSE_ID
# Traces are stored in Unity Catalog tables e2e_ai_workshop_catalog.ops.claims_agent_*
exp = mlflow.set_experiment(C.EXPERIMENT, trace_location=UnityCatalog(
    catalog_name=C.CATALOG, schema_name="ops", table_prefix="claims_agent"))
mlflow.langchain.autolog()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Version the system prompt
# MAGIC v1 uses tools only. v2 adds policy-wording retrieval and citations. `production` starts on v1.

# COMMAND ----------

try:  # idempotent: register v1/v2 only on first run
    mlflow.genai.load_prompt(f"prompts:/{C.PROMPT_NAME}/2")
except Exception:
    mlflow.genai.register_prompt(name=C.PROMPT_NAME, template=PROMPT_V1, commit_message="v1: tools only")
    mlflow.genai.register_prompt(name=C.PROMPT_NAME, template=PROMPT_V2, commit_message="v2: retrieval + citations")
mlflow.genai.set_prompt_alias(name=C.PROMPT_NAME, alias="production", version=1)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Ask the adjuster's question, then open the trace

# COMMAND ----------

prod = mlflow.genai.load_prompt(f"prompts:/{C.PROMPT_NAME}@production")
agent = build_agent(C.LLM_SERVICE, prod.format(), C.UC_FUNCTIONS, retriever_index=None,
                    request_tags={**C.REQUEST_TAGS, "step": "build"})
answer(agent, "Is the water damage on claim C-1042 covered, and what is the payout after the deductible?")

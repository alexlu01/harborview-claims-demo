# Databricks notebook source
# MAGIC %pip install -q -r ../../requirements-agent.txt
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %md
# MAGIC # Production quality monitoring
# MAGIC The same judges used in evaluation run continuously on sampled production traces from the deployed agent.
# MAGIC Results are written back onto each trace in Unity Catalog and roll up into the operations dashboard.

# COMMAND ----------

import os, sys, mlflow
sys.path.insert(0, os.path.abspath(".."))
from common import config as C
from mlflow.genai.scorers import Safety, Guidelines, ScorerSamplingConfig, list_scorers, delete_scorer
from mlflow.tracing import set_databricks_monitoring_sql_warehouse_id

exp = mlflow.set_experiment(C.EXPERIMENT)
set_databricks_monitoring_sql_warehouse_id(sql_warehouse_id=C.WAREHOUSE_ID, experiment_id=exp.experiment_id)

# COMMAND ----------

MONITORS = {"safety_monitor", "cites_sources_monitor"}
for s in list_scorers():  # idempotent re-run
    if s.name in MONITORS:
        delete_scorer(name=s.name)

Safety(model=C.JUDGE_MODEL).register(name="safety_monitor").start(
    sampling_config=ScorerSamplingConfig(sample_rate=1.0))
Guidelines(name="cites_sources_monitor", model=C.JUDGE_MODEL,
           guidelines="Every coverage statement in the response cites a policy form and section such as [HV-END-WB §2.1].") \
    .register(name="cites_sources_monitor").start(sampling_config=ScorerSamplingConfig(sample_rate=1.0))

display([(s.name, s.sample_rate) for s in list_scorers()])

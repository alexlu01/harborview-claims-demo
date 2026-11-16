# Databricks notebook source
# MAGIC %md
# MAGIC # Unity Gateway: governed model access
# MAGIC Every model call from the claims agent goes through one governed **model service**, `e2e_ai_workshop_catalog.agent.claims_llm`.
# MAGIC The service gives the agent:
# MAGIC - access control through Unity Catalog grants
# MAGIC - service policies (guardrails)
# MAGIC - a 60 requests/minute per-user rate limit
# MAGIC - fallback from Kimi K3 to Claude Sonnet
# MAGIC - an inference table
# MAGIC - usage tracking by request tag

# COMMAND ----------

# MAGIC %pip install -q databricks-openai
# MAGIC %restart_python

# COMMAND ----------

import json
from databricks_openai import DatabricksOpenAI

client = DatabricksOpenAI(use_ai_gateway=True)  # https://<workspace>/ai-gateway/mlflow/v1
SERVICE = "e2e_ai_workshop_catalog.agent.claims_llm"
TAGS = {"Databricks-Ai-Gateway-Request-Tags": json.dumps({"project": "claims-workshop", "step": "gateway"})}

def text_of(content):
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content

def ask(msg):
    r = client.chat.completions.create(model=SERVICE, messages=[{"role": "user", "content": msg}], extra_headers=TAGS)
    return {"answer": text_of(r.choices[0].message.content),
            "service_policy": (r.model_extra or {}).get("databricks_service_policy")}

# COMMAND ----------

# MAGIC %md
# MAGIC ### A normal request is allowed

# COMMAND ----------

ask("In one sentence, what does a homeowners deductible mean?")

# COMMAND ----------

# MAGIC %md
# MAGIC ### A request containing an SSN is blocked by the `block_ssn` service policy
# MAGIC The gateway returns HTTP 200. The block reason comes back in `databricks_service_policy`, and the model is never called.

# COMMAND ----------

ask("The insured's SSN is 123-45-6789. Can you confirm their claim C-1042?")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Usage by request tag
# MAGIC `system.ai_gateway.usage` records every call, along with its tags and policy decisions. Rows typically appear within about 20 minutes.

# COMMAND ----------

display(spark.sql("""
  SELECT date_trunc('HOUR', event_time) AS hour, request_tags['step'] AS step, status_code,
         count(*) AS requests, sum(input_tokens) AS input_tokens, sum(output_tokens) AS output_tokens
  FROM system.ai_gateway.usage
  WHERE service_name = 'e2e_ai_workshop_catalog.agent.claims_llm'
  GROUP BY ALL ORDER BY hour DESC
"""))

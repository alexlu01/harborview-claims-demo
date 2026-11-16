# Databricks notebook source
# MAGIC %md
# MAGIC # Governed tools in Unity Catalog
# MAGIC The agent's tools are Unity Catalog functions: discoverable, permissioned and audited like any other data asset.

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT * FROM e2e_ai_workshop_catalog.agent.get_claim('C-1042')

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT * FROM e2e_ai_workshop_catalog.agent.get_policy_coverage('P-20417')

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT e2e_ai_workshop_catalog.agent.calc_payout(7850, 1000, 10000) AS payout

# COMMAND ----------
# MAGIC %sql
# MAGIC SHOW GRANTS ON FUNCTION e2e_ai_workshop_catalog.agent.get_claim

# COMMAND ----------
# MAGIC %md
# MAGIC ## Try it in AI Playground
# MAGIC Open **AI Playground**, choose the claims model, add the four functions (including `search_policy_wording`) under **Tools**, and ask:
# MAGIC *"Is the water damage on claim C-1042 covered, and what is the payout after the deductible?"*

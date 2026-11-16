# Databricks notebook source
# MAGIC %md
# MAGIC # Harborview Mutual — Landing the data
# MAGIC Policy documents (PDF) and claims system extracts (CSV) land in a governed Unity Catalog Volume.

# COMMAND ----------
# MAGIC %pip install -q reportlab
# MAGIC %restart_python

# COMMAND ----------
import sys, os, csv
sys.path.insert(0, os.path.abspath(".."))
from data import harborview_data as hd
CATALOG = "e2e_ai_workshop_catalog"
for s in ["raw", "core", "agent", "ops"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{s}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.raw.policy_docs")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.raw.landing")
base_docs, base_csv = f"/Volumes/{CATALOG}/raw/policy_docs", f"/Volumes/{CATALOG}/raw/landing"
for base in (base_docs, base_csv):   # idempotent reload: clear contents, keep the volume
    for f in dbutils.fs.ls(base):
        dbutils.fs.rm(f.path, True)
paths = hd.write_pdfs(base_docs)
data = hd.generate(7)
for name, rows in data.items():
    os.makedirs(f"{base_csv}/{name}", exist_ok=True)
    with open(f"{base_csv}/{name}/{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
display(dbutils.fs.ls(base_docs))

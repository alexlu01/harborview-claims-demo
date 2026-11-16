from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("catalog")
DOCS = f"/Volumes/{CATALOG}/raw/policy_docs"
LANDING = f"/Volumes/{CATALOG}/raw/landing"

def _csv(name):
    return (spark.readStream.format("cloudFiles").option("cloudFiles.format", "csv")
            .option("header", "true").option("cloudFiles.inferColumnTypes", "true")
            .load(f"{LANDING}/{name}"))

@dp.table(comment="Policies from the policy admin system")
@dp.expect_or_drop("valid_policy_id", "policy_id RLIKE '^P-[0-9]{5}$'")
def policies():
    return _csv("policies")

@dp.table(comment="Claims from the claims system")
@dp.expect_or_drop("valid_claim_id", "claim_id RLIKE '^C-[0-9]{4}$'")
@dp.expect("positive_amount", "claim_amount > 0")
def claims():
    return _csv("claims")

@dp.table(comment="Claim payments")
def payments():
    return _csv("payments")

@dp.table(comment="Adjuster notes")
def adjuster_notes():
    return _csv("adjuster_notes")

@dp.table(comment="Raw policy PDFs")
def policy_docs_raw():
    return spark.readStream.format("cloudFiles").option("cloudFiles.format", "binaryFile").load(DOCS)

@dp.table(comment="Parsed policy documents (ai_parse_document)")
def policy_docs_parsed():
    return (spark.readStream.table("policy_docs_raw")
            .select("path", F.expr("ai_parse_document(content)").alias("parsed")))

@dp.table(comment="Search-ready chunks (ai_prep_search)",
          table_properties={"delta.enableChangeDataFeed": "true"})
@dp.expect_or_drop("has_text", "length(chunk_to_retrieve) > 0")
def policy_chunks():
    return (spark.readStream.table("policy_docs_parsed")
            .withColumn("prep", F.expr("ai_prep_search(parsed)"))
            .withColumn("chunk", F.expr("explode(variant_get(prep, '$.document.contents', 'ARRAY<VARIANT>'))"))
            .selectExpr(
                "variant_get(chunk, '$.chunk_id', 'STRING') AS chunk_id",
                "regexp_extract(path, '([^/]+)\\\\.pdf$', 1) AS form_id",
                "variant_get(chunk, '$.chunk_position', 'INT') AS chunk_position",
                "variant_get(chunk, '$.chunk_to_retrieve', 'STRING') AS chunk_to_retrieve",
                "variant_get(chunk, '$.chunk_to_embed', 'STRING') AS chunk_to_embed",
                "path AS source_path"))

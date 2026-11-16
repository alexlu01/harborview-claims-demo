# Databricks notebook source
# MAGIC %md
# MAGIC # AI Search over policy wording
# MAGIC A hybrid (semantic + keyword) index that stays in sync with the governed chunk table.

# COMMAND ----------
import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (EndpointType, VectorIndexType, PipelineType,
    DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn)
w = WorkspaceClient()
ENDPOINT, INDEX = "harborview_ais", "e2e_ai_workshop_catalog.core.policy_chunks_index"
if ENDPOINT not in [e.name for e in w.vector_search_endpoints.list_endpoints()]:
    w.vector_search_endpoints.create_endpoint_and_wait(name=ENDPOINT, endpoint_type=EndpointType.STANDARD)
try:
    w.vector_search_indexes.get_index(INDEX)
    w.vector_search_indexes.sync_index(INDEX)
except Exception:
    w.vector_search_indexes.create_index(
        name=INDEX, endpoint_name=ENDPOINT, primary_key="chunk_id",
        index_type=VectorIndexType.DELTA_SYNC,
        delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
            source_table="e2e_ai_workshop_catalog.core.policy_chunks", pipeline_type=PipelineType.TRIGGERED,
            columns_to_sync=["chunk_id", "form_id", "chunk_to_retrieve"],
            embedding_source_columns=[EmbeddingSourceColumn(name="chunk_to_embed",
                                                            embedding_model_endpoint_name="databricks-gte-large-en")]))
while not w.vector_search_indexes.get_index(INDEX).status.ready:
    time.sleep(20)

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT form_id, chunk_to_retrieve
# MAGIC FROM vector_search(index => 'e2e_ai_workshop_catalog.core.policy_chunks_index',
# MAGIC                    query_text => 'sump pump overflow water backup coverage',
# MAGIC                    num_results => 3, query_type => 'HYBRID')

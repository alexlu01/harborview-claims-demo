"""SQL for the Harborview operations dashboard datasets (tested via scripts/sql.sh before deploy)."""
DS = {
 "ds_usage": """SELECT event_time, date_trunc('HOUR', event_time) AS hour, coalesce(request_tags['step'], 'untagged') AS step,
 CASE WHEN status_code = 200 AND destination_model IS NULL THEN 'Blocked by policy' WHEN status_code = 200 THEN 'Answered' ELSE 'Error' END AS outcome,
 coalesce(destination_model, 'none') AS model, coalesce(input_tokens, 0) AS input_tokens, coalesce(output_tokens, 0) AS output_tokens, coalesce(input_tokens, 0) + coalesce(output_tokens, 0) AS total_tokens,
 latency_ms, CASE WHEN status_code = 200 AND destination_model IS NULL THEN 1 ELSE 0 END AS blocked
FROM system.ai_gateway.usage WHERE service_name = 'e2e_ai_workshop_catalog.agent.claims_llm'""",
 "ds_quality": """SELECT t.trace_id, date_trunc('HOUR', t.request_time) AS hour, a.assessment_name AS judge,
 CASE WHEN lower(a.feedback.value) IN ('yes', 'true', '"yes"', '"true"') THEN 1.0 ELSE 0.0 END AS passed
FROM e2e_ai_workshop_catalog.ops.claims_agent_trace_unified t LATERAL VIEW explode(t.assessments) x AS a
WHERE a.feedback.value IS NOT NULL AND a.assessment_name IN ('correctness', 'coverage_accuracy', 'safety', 'cites_policy_section', 'retrieval_groundedness', 'safety_monitor', 'cites_sources_monitor')""",
 "ds_traces": """SELECT trace_id, request_time, date_trunc('HOUR', request_time) AS hour, state, execution_duration_ms / 1000.0 AS seconds
FROM e2e_ai_workshop_catalog.ops.claims_agent_trace_unified""",
 "ds_dq": """SELECT e.timestamp AS ts, x.dataset AS dataset_name, x.name AS expectation, x.passed_records AS passed, x.failed_records AS failed,
 x.passed_records / greatest(x.passed_records + x.failed_records, 1) AS pass_rate
FROM event_log('1abf00a9-7a44-46a1-a3ff-58cbc867991c') e
LATERAL VIEW explode(from_json(e.details:flow_progress.data_quality.expectations::string, 'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) t AS x
WHERE e.event_type = 'flow_progress' AND e.details:flow_progress.data_quality.expectations IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY x.dataset, x.name ORDER BY e.timestamp DESC) = 1""",
 "ds_claims": """SELECT claim_id, status, loss_type, claim_amount, loss_date FROM claims""",
}

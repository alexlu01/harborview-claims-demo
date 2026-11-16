CREATE OR REPLACE FUNCTION e2e_ai_workshop_catalog.agent.get_claim(id STRING COMMENT 'Claim ID such as C-1042')
RETURNS TABLE (claim_id STRING, policy_id STRING, loss_type STRING, loss_date STRING,
               claim_amount DOUBLE, status STRING, adjuster STRING)
COMMENT 'Look up one claim by ID. Returns no rows if the claim does not exist.'
RETURN SELECT claim_id, policy_id, loss_type, CAST(loss_date AS STRING), claim_amount, status, adjuster
       FROM e2e_ai_workshop_catalog.core.claims WHERE claim_id = id;

CREATE OR REPLACE FUNCTION e2e_ai_workshop_catalog.agent.get_policy_coverage(id STRING COMMENT 'Policy ID such as P-20417')
RETURNS TABLE (policy_id STRING, line STRING, form_id STRING, deductible DOUBLE,
               coverage_a_limit DOUBLE, water_backup_limit DOUBLE, endorsements STRING)
COMMENT 'Coverage summary for a policy: form, deductible, limits and attached endorsements.'
RETURN SELECT policy_id, line, form_id, deductible, coverage_a_limit, water_backup_limit, endorsements
       FROM e2e_ai_workshop_catalog.core.policies WHERE policy_id = id;

CREATE OR REPLACE FUNCTION e2e_ai_workshop_catalog.agent.calc_payout(
  claim_amount DOUBLE COMMENT 'Covered loss amount', deductible DOUBLE COMMENT 'Policy deductible',
  coverage_limit DOUBLE COMMENT 'Applicable coverage limit')
RETURNS DOUBLE
COMMENT 'Payout = min(claim amount minus deductible, limit), never below zero.'
RETURN GREATEST(0.0, LEAST(claim_amount - deductible, coverage_limit));
;

CREATE OR REPLACE FUNCTION e2e_ai_workshop_catalog.agent.search_policy_wording(query STRING COMMENT 'What to look up in Harborview policy forms and endorsements')
RETURNS TABLE (form_id STRING, chunk_to_retrieve STRING)
COMMENT 'Hybrid (semantic + keyword) search over Harborview policy forms and endorsements. Returns the top 4 passages with their form ID: cite sections as [FORM-ID §n.n].'
RETURN SELECT form_id, chunk_to_retrieve
       FROM vector_search(index => 'e2e_ai_workshop_catalog.core.policy_chunks_index', query_text => query,
                          num_results => 4, query_type => 'HYBRID')

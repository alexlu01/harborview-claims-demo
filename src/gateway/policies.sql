-- Service-policy SQL is transpiled to CEL: only a SQL subset is allowed (no translate/regex), so digits are
-- masked with nested REPLACE and the digit-only shape ###-##-#### is matched. Form IDs (HV-HO-3) and ISO dates never match.
-- NOTE: the attached policy picks up a replaced body by name after a few minutes. Unsupported SQL (e.g. translate)
-- fails closed: every request through claims_llm is denied with 'a policy on this service could not be evaluated'.
CREATE OR REPLACE FUNCTION e2e_ai_workshop_catalog.agent.block_ssn(event VARIANT)
RETURNS VARIANT
LANGUAGE SQL
RETURN
  CASE
    WHEN event:type::string = 'request'
     AND replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(event:context.message::string, '0', '#'), '1', '#'), '2', '#'), '3', '#'), '4', '#'), '5', '#'), '6', '#'), '7', '#'), '8', '#'), '9', '#') LIKE '%###-##-####%'
    THEN to_variant_object(named_struct('result', 'DENY',
         'reason', 'Requests containing Social Security numbers are blocked by Harborview Mutual policy.'))
    ELSE to_variant_object(named_struct('result', 'ALLOW', 'reason', ''))
  END

from eval.scorers import _has_citation

def test_cites_logic():
    assert _has_citation("Covered [HV-END-WB §2.1].")
    assert not _has_citation("Covered under the endorsement.")

from eval.scorers import cites_policy_section, coverage_judge

def test_cites_required_when_docs_needed():
    assert cites_policy_section(outputs="Covered under the endorsement.", expectations={"needs_docs": True}).value == "no"
    assert cites_policy_section(outputs="Covered [HV-END-WB §2.1].", expectations={"needs_docs": True}).value == "yes"

def test_cites_not_required_for_lookup_questions():
    fb = cites_policy_section(outputs="Claim C-1006 is open, $4,200.", expectations={"needs_docs": False})
    assert fb.value == "yes" and "not required" in fb.rationale

def test_coverage_judge_is_boolean_so_mean_is_computed():
    assert coverage_judge("databricks:/x").feedback_value_type is bool

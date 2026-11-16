import re
from agent.prompts import PROMPT_V1, PROMPT_V2, CITATION_RE

def test_v2_requires_citations_and_search():
    assert "search_policy_wording" in PROMPT_V2 and "[" in PROMPT_V2
    assert "search_policy_wording" not in PROMPT_V1

def test_citation_regex():
    assert re.search(CITATION_RE, "Covered [HV-END-WB §2.1].")
    assert not re.search(CITATION_RE, "Covered under the endorsement.")

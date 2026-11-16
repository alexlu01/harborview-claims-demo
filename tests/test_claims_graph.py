from agent.claims_graph import to_text

def test_to_text_passthrough():
    assert to_text("hello") == "hello"

def test_to_text_handles_block_lists():
    blocks = [{"type": "text", "text": "Covered under "}, {"type": "tool_use", "id": "x"}, {"type": "text", "text": "HV-END-WB §2.1."}]
    assert to_text(blocks) == "Covered under HV-END-WB §2.1."

def test_to_text_none():
    assert to_text(None) == ""

import json
from agent.claims_graph import llm_kwargs

def test_llm_kwargs_routes_through_unity_gateway_without_temperature():
    kw = llm_kwargs("cat.agent.claims_llm", {"project": "claims-workshop"})
    assert kw["endpoint"] == "cat.agent.claims_llm"
    assert kw["use_ai_gateway"] is True
    assert "temperature" not in kw  # some routed models (e.g. the Claude fallback) reject temperature
    tags = kw["extra_params"]["extra_headers"]["Databricks-Ai-Gateway-Request-Tags"]
    assert json.loads(tags) == {"project": "claims-workshop"}

def test_llm_kwargs_no_tags():
    assert "extra_params" not in llm_kwargs("cat.agent.claims_llm", None)

def test_build_tools_empty_needs_no_workspace():
    from agent.claims_graph import build_tools
    assert build_tools([], None) == []

def test_to_text_decodes_json_encoded_block_list():
    s = json.dumps([{"type": "reasoning", "summary": []}, {"type": "text", "text": "Payout is $6,850 [HV-END-WB §2.1]."}])
    assert to_text(s) == "Payout is $6,850 [HV-END-WB §2.1]."

def test_to_text_keeps_plain_text_that_looks_like_brackets():
    assert to_text("[HV-END-WB §2.1] applies.") == "[HV-END-WB §2.1] applies."

def test_format_passages_prefixes_form_id_for_citations():
    from langchain_core.documents import Document
    from agent.claims_graph import format_passages
    docs = [Document(page_content="§2.1 Water Backup Coverage. We cover...", metadata={"form_id": "HV-END-WB"}),
            Document(page_content="§1.1 Coverage A.", metadata={"form_id": "HV-HO-3"})]
    out = format_passages(docs)
    assert out.startswith("[HV-END-WB] §2.1 Water Backup Coverage.")
    assert "\n\n[HV-HO-3] §1.1" in out

def test_format_passages_empty():
    from agent.claims_graph import format_passages
    assert format_passages([]) == "No matching policy wording found."

def test_format_passages_prefers_chunk_to_retrieve_metadata():
    from langchain_core.documents import Document
    from agent.claims_graph import format_passages
    d = Document(page_content="Company: Harborview...\nContent: §2.1 ...", metadata={"form_id": "HV-END-WB", "chunk_to_retrieve": "§2.1 Water Backup Coverage."})
    assert format_passages([d]) == "[HV-END-WB] §2.1 Water Backup Coverage."

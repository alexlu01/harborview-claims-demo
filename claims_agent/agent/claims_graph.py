"""Shared Harborview claims agent core (used by notebooks and the deployed agent)."""
import json
from typing import Any

TAG_HEADER = "Databricks-Ai-Gateway-Request-Tags"

def to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        if content.startswith('[{"type"'):  # gateway may return the block list JSON-encoded
            try:
                return to_text(json.loads(content))
            except ValueError:
                pass
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return str(content)

def llm_kwargs(llm_endpoint: str, request_tags: dict | None = None) -> dict:
    """ChatDatabricks kwargs for a Unity Gateway model service (no temperature: some routed models reject it)."""
    kw: dict = {"endpoint": llm_endpoint, "use_ai_gateway": True}
    if request_tags:
        kw["extra_params"] = {"extra_headers": {TAG_HEADER: json.dumps(request_tags)}}
    return kw

SEARCH_DESCRIPTION = ("Search Harborview policy forms and endorsements for coverage, exclusion, limit and deadline "
                      "wording. Each passage starts with its form ID; cite as [FORM-ID §section].")

def format_passages(docs) -> str:
    """Tool output for the LLM: one passage per block, prefixed with its form ID so it can cite."""
    if not docs:
        return "No matching policy wording found."
    return "\n\n".join(f"[{d.metadata.get('form_id', '?')}] {(d.metadata.get('chunk_to_retrieve') or d.page_content).strip()}"
                       for d in docs)

def _policy_search_tool(index_name: str, workspace_client=None):
    """AI Search hybrid retrieval. The inner RETRIEVER span returns Documents, which the
    RetrievalGroundedness judge reads as retrieval context."""
    import mlflow
    from mlflow.entities import SpanType
    from databricks_langchain import DatabricksVectorSearch
    from langchain_core.tools import tool
    store = DatabricksVectorSearch(index_name=index_name,  # text = embedding source (chunk_to_embed)
                                   columns=["chunk_id", "form_id", "chunk_to_retrieve"],
                                   **({"workspace_client": workspace_client} if workspace_client is not None else {}))

    @mlflow.trace(name="retrieve_policy_wording", span_type=SpanType.RETRIEVER)
    def retrieve(query: str):
        return store.similarity_search(query, k=4, query_type="HYBRID")

    @tool("search_policy_wording", description=SEARCH_DESCRIPTION)
    def search_policy_wording(query: str) -> str:
        return format_passages(retrieve(query))

    return search_policy_wording

def build_tools(uc_functions: list[str], retriever_index: str | None = None, workspace_client=None) -> list:
    """Governed tools: UC functions plus (optionally) AI Search over policy wording."""
    tools: list = []
    if uc_functions:
        from databricks_langchain import UCFunctionToolkit
        tools += list(UCFunctionToolkit(function_names=uc_functions).tools)
    if retriever_index:
        tools.append(_policy_search_tool(retriever_index, workspace_client))
    return tools

def build_agent(llm_endpoint: str, system_prompt: str, uc_functions: list[str],
                retriever_index: str | None = None, request_tags: dict | None = None):
    from databricks_langchain import ChatDatabricks
    from langgraph.prebuilt import create_react_agent
    llm = ChatDatabricks(**llm_kwargs(llm_endpoint, request_tags))
    return create_react_agent(llm, build_tools(uc_functions, retriever_index), prompt=system_prompt)

def answer(agent, question: str) -> str:
    out = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return to_text(out["messages"][-1].content)

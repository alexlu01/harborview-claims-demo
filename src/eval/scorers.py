import re
from mlflow.entities import Feedback
from mlflow.genai.scorers import scorer
from mlflow.genai.judges import make_judge
from agent.prompts import CITATION_RE

def _has_citation(text: str) -> bool:
    return re.search(CITATION_RE, text or "") is not None

@scorer
def cites_policy_section(outputs, expectations=None) -> Feedback:
    """Coverage answers must cite [FORM-ID §section]; plain claim lookups don't need one."""
    if expectations is not None and not expectations.get("needs_docs", True):
        return Feedback(value="yes", rationale="Citation not required: claim lookup question")
    ok = _has_citation(outputs if isinstance(outputs, str) else str(outputs))
    return Feedback(value="yes" if ok else "no",
                    rationale="Found [FORM §section] citation" if ok else "No policy citation found")

def coverage_judge(model: str):
    return make_judge(
        name="coverage_accuracy",
        instructions=("You are a senior claims examiner. Question: {{ inputs }}\nAgent answer: {{ outputs }}\n"
                      "Expected facts: {{ expectations }}\n"
                      "Return true only if the coverage decision, any limit or deductible, and any payout amount "
                      "match the expected facts exactly and nothing material is invented. Otherwise return false."),
        model=model, feedback_value_type=bool)

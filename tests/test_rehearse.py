import importlib.util, pathlib, sys
from types import SimpleNamespace as NS

_p = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "rehearse.py"
_spec = importlib.util.spec_from_file_location("rehearse", _p)
rehearse = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(_p.parents[1] / "src"))
_spec.loader.exec_module(rehearse)

TOOLS = [f"cat__agent__{t}" for t in ("get_claim", "get_policy_coverage", "calc_payout")] + ["retrieve_policy_wording"]


def _trace(tid, question, spans):
    return NS(info=NS(trace_id=tid), data=NS(request='{"messages":[{"content":"%s"}]}' % question,
                                             spans=[NS(name=s) for s in spans]))


def test_hero_trace_found_behind_newer_eval_traces():
    newer = [_trace(f"e{i}", "What is the status of claim C-1043?", TOOLS[:2]) for i in range(25)]
    hero = _trace("h1", "Is the water damage on claim C-1042 covered, and what is the payout after the deductible?", TOOLS)
    assert rehearse.hero_trace(newer + [hero], "cat").info.trace_id == "h1"


def test_hero_trace_none_when_hero_lacks_a_tool():
    hero = _trace("h1", "Is the water damage on claim C-1042 covered, and what is the payout?", TOOLS[:2])
    assert rehearse.hero_trace([hero], "cat") is None


def test_non_hero_trace_with_all_tools_does_not_count():
    other = _trace("o1", "Payout for claim C-1043?", TOOLS)
    assert rehearse.hero_trace([other], "cat") is None


def test_hero_trace_without_retrieval_does_not_count():
    hero = _trace("h1", "Is the water damage on claim C-1042 covered, and what is the payout?", TOOLS[:3])
    assert rehearse.hero_trace([hero], "cat") is None

from fakes import ScriptedModel

from driftwhy.audit import load_events
from driftwhy.drift import load_drift
from driftwhy.explain import Explanation
from driftwhy.graph import analyse_all
from driftwhy.guard import check
from driftwhy.llm import ModelExplainer
from driftwhy.report import text_report

EVENTS = load_events("examples/cloudtrail.json")
REAL = EVENTS[1].id


def ex(verdict, evidence):
    return Explanation(verdict=verdict, who="x", why="y", evidence=evidence, confidence="high")


def test_real_evidence_passes():
    assert check(ex("revert", [REAL]), EVENTS) == (ex("revert", [REAL]), [])


def test_invented_ids_are_dropped():
    fixed, notes = check(ex("revert", [REAL, "made-up"]), EVENTS)
    assert fixed.evidence == [REAL] and fixed.verdict == "revert"
    assert notes == ["the model cited events that don't exist: made-up"]


def test_a_verdict_on_invented_evidence_is_unclear():
    fixed, notes = check(ex("keep", ["made-up"]), EVENTS)
    assert (fixed.verdict, fixed.confidence) == ("unclear", "low")
    assert len(notes) == 2


def test_a_verdict_with_no_events_is_unclear():
    fixed, notes = check(ex("keep", []), [])
    assert fixed.verdict == "unclear"
    assert notes == ["the model said keep with no audit events to go on"]


def test_the_guard_runs_in_the_graph_and_shows_in_the_report():
    lam = load_drift("examples/drift.json")[2]  # no events in the trail
    answer = {"verdict": "keep", "who": "user bob", "why": "Bob raised it.", "evidence": ["e9"]}
    (item,) = analyse_all([lam], EVENTS, ModelExplainer(ScriptedModel([answer])))
    assert item.explanation.verdict == "unclear"
    assert "  note:    the model cited events that don't exist: e9" in text_report([item])

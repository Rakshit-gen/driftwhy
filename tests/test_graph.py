import threading

from fakes import ScriptedModel

from driftwhy.audit import load_events
from driftwhy.drift import load_drift
from driftwhy.graph import analyse_all
from driftwhy.llm import ModelExplainer
from driftwhy.rules import rules_explain

DRIFT = load_drift("examples/drift.json")
EVENTS = load_events("examples/cloudtrail.json")


def test_every_resource_is_analysed_and_kept_in_order():
    items = analyse_all(DRIFT, EVENTS, rules_explain)
    assert [it.drift.address for it in items] == [d.address for d in DRIFT]
    assert [it.explanation.verdict for it in items] == ["revert", "unclear", "unclear", "revert"]
    assert items[0].risks == ["port 22 open to the internet"]
    assert [e.name for e in items[1].events] == ["ModifyInstanceAttribute", "CreateTags"]


def test_no_drift_still_finishes():
    assert analyse_all([], EVENTS, rules_explain) == []


def test_branches_run_concurrently():
    seen = set()
    lock = threading.Lock()

    def slow(d, c, r, ev):
        with lock:
            seen.add(threading.get_ident())
        threading.Event().wait(0.05)
        return rules_explain(d, c, r, ev)

    analyse_all(DRIFT, EVENTS, slow)
    assert len(seen) > 1


def test_with_a_model():
    answers = [
        {"verdict": "revert", "who": "user alice", "why": "SSH opened to everyone."},
        {"verdict": "keep", "who": "role oncall/priya", "why": "Resized in INC-2291."},
        {"verdict": "unclear", "who": "unknown", "why": "No events."},
        {"verdict": "revert", "who": "role ci-deploy/github-actions", "why": "Deleted by CI."},
    ]
    # Branches run concurrently, so hand out answers by resource, not by call order.
    by_address = dict(zip([d.address for d in DRIFT], answers, strict=True))

    def explainer(d, c, r, ev):
        return ModelExplainer(ScriptedModel([by_address[d.address]]))(d, c, r, ev)

    items = analyse_all(DRIFT, EVENTS, explainer)
    assert [it.explanation.verdict for it in items] == ["revert", "keep", "unclear", "revert"]

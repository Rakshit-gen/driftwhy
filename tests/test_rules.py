from driftwhy.audit import load_events
from driftwhy.diff import changes
from driftwhy.drift import load_drift
from driftwhy.match import events_for
from driftwhy.risk import risks
from driftwhy.rules import rules_explain

DRIFT = load_drift("examples/drift.json")
EVENTS = load_events("examples/cloudtrail.json")


def explain(d):
    c = changes(d)
    return rules_explain(d, c, risks(d, c), events_for(d, EVENTS))


def test_rules_on_the_example():
    sg, api, lam, queue = (explain(d) for d in DRIFT)
    assert (sg.verdict, sg.who) == ("revert", "user alice")
    assert (api.verdict, api.who) == ("unclear", "role oncall/priya")
    assert api.evidence == [
        "d92b0c41-5e6a-4f7d-9c3b-2a8e1f4d6b04",
        "e05c1d52-6f7b-4a8e-8d4c-3b9f2a5e7c05",
    ]
    assert (lam.verdict, lam.who, lam.evidence) == ("unclear", "unknown", [])
    assert (queue.verdict, queue.who) == ("revert", "role ci-deploy/github-actions")

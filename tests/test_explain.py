import pytest
from pydantic import ValidationError

from driftwhy.audit import load_events
from driftwhy.diff import changes
from driftwhy.drift import load_drift
from driftwhy.explain import Explanation, describe
from driftwhy.match import events_for
from driftwhy.risk import risks

DRIFT = load_drift("examples/drift.json")
EVENTS = load_events("examples/cloudtrail.json")


def text(d):
    c = changes(d)
    return describe(d, c, risks(d, c), events_for(d, EVENTS))


def test_description_has_the_change_flags_and_events():
    t = text(DRIFT[0])
    assert "- ingress: added {" in t
    assert "Risk flags: port 22 open to the internet" in t
    assert "Event 8b6d4f10-2c3e-4a8f-b7d2-1e9a5c3f7b02: 2026-10-10 14:03 UTC," in t
    assert "by user alice via console.ec2.amazonaws.com" in t


def test_description_says_when_nothing_was_found():
    t = text(DRIFT[2])
    assert "- timeout: 30 -> 90" in t
    assert "Events: none found in the audit log." in t
    assert "It was deleted outside Terraform." in text(DRIFT[3])


def test_verdict_must_be_one_of_three():
    Explanation(verdict="keep", who="x", why="y")
    with pytest.raises(ValidationError):
        Explanation(verdict="maybe", who="x", why="y")

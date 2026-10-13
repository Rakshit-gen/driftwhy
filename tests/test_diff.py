from driftwhy.diff import Change, changes, diff
from driftwhy.drift import load_drift


def test_scalar_and_nested_changes():
    assert diff({"a": 1, "t": {"x": "1"}}, {"a": 2, "t": {"x": "1", "y": "2"}}) == [
        Change("a", 1, 2),
        Change("t.y", None, "2"),
    ]


def test_lists_compare_as_sets():
    rule = {"port": 443}
    assert diff({"r": [rule]}, {"r": [{"port": 22}, rule]}) == [
        Change("r", None, {"port": 22}, "added")
    ]
    assert diff({"r": [rule, {"port": 22}]}, {"r": [{"port": 22}, rule]}) == []


def test_tags_all_is_ignored_and_deletions_have_no_changes():
    sg, api, lam, queue = load_drift("examples/drift.json")
    assert [c.path for c in changes(api)] == ["instance_type", "tags.incident"]
    (rule,) = changes(sg)
    assert rule.kind == "added" and rule.new["from_port"] == 22
    assert changes(lam) == [Change("timeout", 30, 90)]
    assert changes(queue) == []

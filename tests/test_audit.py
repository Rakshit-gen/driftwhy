import json

from driftwhy.audit import actor_of, load_events


def test_reads_the_example_trail_in_time_order():
    events = load_events("examples/cloudtrail.json")
    assert [e.name for e in events][:2] == ["DeleteQueue", "AuthorizeSecurityGroupIngress"]
    assert events[1].actor == "user alice"
    assert events[3].actor == "role oncall/priya"
    assert [e.read_only for e in events] == [False, False, True, False, False, False]


def test_reads_one_event_per_line(tmp_path):
    records = json.load(open("examples/cloudtrail.json"))["Records"]
    p = tmp_path / "trail.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records))
    assert len(load_events(p)) == len(records)


def test_actor_names():
    assert actor_of({"type": "Root", "arn": "arn:aws:iam::1:root"}) == "root account"
    assert actor_of({"type": "AWSService", "invokedBy": "autoscaling.amazonaws.com"}) == (
        "autoscaling.amazonaws.com"
    )

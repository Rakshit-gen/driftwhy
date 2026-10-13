from driftwhy.audit import load_events
from driftwhy.drift import load_drift
from driftwhy.match import events_for, identifiers

DRIFT = load_drift("examples/drift.json")
EVENTS = load_events("examples/cloudtrail.json")


def names(d, **kw):
    return [e.name for e in events_for(d, EVENTS, **kw)]


def test_each_resource_gets_its_own_events():
    sg, api, lam, queue = DRIFT
    assert names(sg) == ["AuthorizeSecurityGroupIngress"]
    assert names(api) == ["ModifyInstanceAttribute", "CreateTags"]
    assert names(lam) == []
    assert names(queue) == ["DeleteQueue"]
    assert names(api, include_reads=True)[0] == "DescribeInstances"


def test_identifiers_match_whole_values_only():
    sg = DRIFT[0]
    assert identifiers(sg) == {"sg-0a1b2c3d4e5f60718", "web"}
    api = DRIFT[1]
    assert "api" not in identifiers(api)  # no name attribute on the instance


def test_a_name_inside_a_longer_value_does_not_match():
    from dataclasses import replace

    sg = replace(DRIFT[0], before={"name": "web"})
    tagged = [e for e in EVENTS if e.name == "PutBucketTagging"]
    other = replace(tagged[0], text=tagged[0].text.replace("media-uploads", "web-uploads"))
    assert events_for(sg, [other]) == []
    assert events_for(sg, [replace(other, text=other.text.replace('"web-uploads"', '"web"'))])

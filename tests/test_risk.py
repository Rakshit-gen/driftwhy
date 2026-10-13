from driftwhy.diff import Change, changes
from driftwhy.drift import Drift, load_drift
from driftwhy.risk import risks


def test_example_risks():
    sg, api, lam, queue = load_drift("examples/drift.json")
    assert risks(sg, changes(sg)) == ["port 22 open to the internet"]
    assert risks(api, changes(api)) == []
    assert risks(queue, changes(queue)) == ["deleted outside Terraform"]


def test_https_to_the_world_is_fine_but_a_port_range_is_not():
    d = Drift("aws_security_group.x", "aws_security_group", "update", {}, {})
    https = {"from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}
    wide = {"from_port": 0, "to_port": 65535, "ipv6_cidr_blocks": ["::/0"]}
    assert risks(d, [Change("ingress", None, https, "added")]) == []
    assert risks(d, [Change("ingress", None, wide, "added")]) == ["port 0 open to the internet"]


def test_public_access_encryption_and_iam():
    d = Drift("aws_iam_role.x", "aws_iam_role", "update", {}, {})
    found = risks(
        d,
        [Change("block_public_acls", True, False), Change("storage_encrypted", True, False)],
    )
    assert found == ["IAM change", "block_public_acls turned off", "storage_encrypted turned off"]

import json

import pytest

from driftwhy.drift import DriftError, load_drift

EXAMPLE = "examples/drift.json"


def test_reads_the_example():
    drift = load_drift(EXAMPLE)
    assert [d.address for d in drift] == [
        "aws_security_group.web",
        "aws_instance.api",
        "aws_lambda_function.thumbnails",
        "aws_sqs_queue.retry",
    ]
    assert [d.action for d in drift] == ["update", "update", "update", "delete"]
    assert drift[3].after is None


def test_no_drift_is_an_empty_list(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"format_version": "1.2"}))
    assert load_drift(p) == []


def test_rejects_other_json(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("[1, 2]")
    with pytest.raises(DriftError, match="terraform show -json"):
        load_drift(p)
    p.write_text("{nope")
    with pytest.raises(DriftError, match="not JSON"):
        load_drift(p)

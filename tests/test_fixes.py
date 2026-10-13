from driftwhy.audit import load_events
from driftwhy.drift import load_drift
from driftwhy.fixes import hcl, next_step
from driftwhy.graph import analyse_all
from driftwhy.rules import rules_explain

ITEMS = analyse_all(
    load_drift("examples/drift.json"), load_events("examples/cloudtrail.json"), rules_explain
)


def test_hcl_values():
    assert hcl("t3.large") == '"t3.large"'
    assert hcl([1, True, None]) == "[1, true, null]"
    assert hcl({"b": "2", "a": 1}) == '{\n  a = 1\n  b = "2"\n}'


def test_keep_writes_the_running_values_into_code():
    sg, api, lam, queue = ITEMS
    assert next_step(api, "keep") == (
        "In the resource block for aws_instance.api:\n"
        'instance_type = "t3.large"\n'
        'tags = {\n  Name = "api"\n  incident = "INC-2291"\n}'
    )
    rule = next_step(sg, "keep")
    assert "# add\ningress {\n" in rule
    assert '  cidr_blocks = ["0.0.0.0/0"]\n' in rule
    assert "description" not in rule  # empty strings are left out


def test_revert_and_deleted_resources():
    sg, api, lam, queue = ITEMS
    assert next_step(sg).startswith("terraform apply -target=aws_security_group.web  # puts back")
    assert "recreates" in next_step(queue, "revert")
    assert next_step(queue, "keep").startswith("terraform state rm aws_sqs_queue.retry")
    assert next_step(lam) == "No change until someone decides."

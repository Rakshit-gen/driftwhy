from driftwhy.audit import load_events
from driftwhy.drift import load_drift
from driftwhy.graph import analyse_all
from driftwhy.report import summary, text_report
from driftwhy.rules import rules_explain

ITEMS = analyse_all(
    load_drift("examples/drift.json"), load_events("examples/cloudtrail.json"), rules_explain
)


def test_summary_counts_decisions_over_suggestions():
    assert summary(ITEMS) == "4 resources drifted: 2 to revert, 0 to keep, 2 undecided."
    assert summary(ITEMS, {1: "keep", 2: "skip"}) == (
        "4 resources drifted: 2 to revert, 1 to keep, 1 undecided."
    )


def test_text_report():
    text = text_report(ITEMS, {1: "keep"})
    assert "aws_security_group.web  REVERT (suggested, medium confidence)" in text
    assert (
        '  changed: ingress: added from_port=22, to_port=22, protocol="tcp", cidr_blocks=' in text
    )
    assert "  risk:    port 22 open to the internet" in text
    assert "  who:     user alice, 2026-10-10 14:03 UTC" in text
    assert "aws_instance.api  KEEP (decided)" in text
    assert '           instance_type = "t3.large"' in text
    assert "  who:     unknown\n" in text


def test_no_drift():
    assert text_report([]).startswith("No drift")

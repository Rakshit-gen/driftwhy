from driftwhy.cli import main

ARGS = ["examples/drift.json", "--audit", "examples/cloudtrail.json", "--model", "rules"]


def test_report_on_the_example(capsys):
    assert main(ARGS) == 0
    out = capsys.readouterr().out
    assert out.startswith("4 resources drifted: 2 to revert, 0 to keep, 2 undecided.")


def test_without_an_audit_log_nothing_is_explained(capsys):
    assert main(["examples/drift.json", "--model", "rules"]) == 0
    assert "2 to revert" not in capsys.readouterr().out


def test_errors_exit_2(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert main(["missing.json"]) == 2
    assert main(["examples/drift.json", "--model", "groq:openai/gpt-oss-20b"]) == 2
    assert "GROQ_API_KEY" in capsys.readouterr().err

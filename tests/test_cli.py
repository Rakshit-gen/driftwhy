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


def test_review_asks_about_each_resource(capsys, monkeypatch):
    answers = iter(["", "k", "maybe", "s", "r"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    assert main(ARGS + ["--review"]) == 0
    out = capsys.readouterr().out
    assert out.count("keep, revert or skip?") == 0  # the prompt goes to input(), not print
    assert "type k, r or s" in out
    final = out[out.index("4 resources drifted") :]
    assert final.startswith("4 resources drifted: 2 to revert, 1 to keep, 1 undecided.")
    assert "aws_security_group.web  REVERT (decided)" in final  # empty answer took the default
    assert "aws_instance.api  KEEP (decided)" in final


def test_review_can_be_stopped(capsys, monkeypatch):
    def stop(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", stop)
    assert main(ARGS + ["--review"]) == 130
    assert "nothing was changed" in capsys.readouterr().err


def test_markdown_and_json(capsys):
    import json

    assert main(ARGS + ["-f", "markdown"]) == 0
    md = capsys.readouterr().out
    assert md.startswith("**4 resources drifted")
    assert "| `aws_security_group.web` | revert (suggested) | user alice |" in md
    assert md.count("<details>") == 4
    assert main(ARGS + ["-f", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["decision"] for r in rows] == ["revert", "unclear", "unclear", "revert"]
    assert rows[0]["changes"][0]["new"]["from_port"] == 22

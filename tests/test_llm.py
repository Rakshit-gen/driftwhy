import pytest
from fakes import ScriptedModel

from driftwhy.drift import load_drift
from driftwhy.llm import ModelExplainer, make_explainer
from driftwhy.rules import rules_explain

KEEP = {"verdict": "keep", "who": "role oncall/priya", "why": "Incident fix.", "evidence": []}


def test_model_explainer_sends_the_description_and_parses_the_answer():
    model = ScriptedModel([KEEP])
    d = load_drift("examples/drift.json")[1]
    ans = ModelExplainer(model)(d, [], [], [])
    assert ans.verdict == "keep"
    system, human = model.prompts[0]
    assert "infrastructure drift" in system.content
    assert human.content.startswith("Resource: aws_instance.api")


def test_a_failed_call_is_retried():
    model = ScriptedModel([ValueError("bad json"), KEEP])
    d = load_drift("examples/drift.json")[1]
    assert ModelExplainer(model)(d, [], [], []).verdict == "keep"


def test_make_explainer(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert make_explainer() is rules_explain
    assert make_explainer("rules") is rules_explain
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        make_explainer("groq:openai/gpt-oss-120b")
    with pytest.raises(ValueError, match="unknown model"):
        make_explainer("gpt-4")
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-used")
    assert isinstance(make_explainer(), ModelExplainer)  # builds the client, calls nothing

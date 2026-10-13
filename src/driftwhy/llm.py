"""Pick the explainer: a chat model through LangChain, or the rules."""

import os

from .explain import Explanation, messages
from .rules import rules_explain

# Checked against Groq's model list on 2026-10-13. Override with --model.
DEFAULT_MODEL = "groq:openai/gpt-oss-120b"


class ModelExplainer:
    """Asks a chat model for an Explanation, retrying the odd malformed answer."""

    def __init__(self, chat_model):
        self.chain = chat_model.with_structured_output(Explanation).with_retry(stop_after_attempt=3)

    def __call__(self, d, changes, risks, events) -> Explanation:
        return self.chain.invoke(messages(d, changes, risks, events))


def make_explainer(spec: str | None = None):
    """ "rules", or "groq:<model id>". With no spec: Groq if GROQ_API_KEY is set,
    else the rules."""
    if spec is None:
        spec = DEFAULT_MODEL if os.environ.get("GROQ_API_KEY") else "rules"
    if spec == "rules":
        return rules_explain
    provider, _, model = spec.partition(":")
    if provider != "groq" or not model:
        raise ValueError(f"unknown model {spec!r}: use rules or groq:<model id>")
    if not os.environ.get("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is not set (or use --model rules)")
    from langchain_groq import ChatGroq

    return ModelExplainer(ChatGroq(model=model, temperature=0))

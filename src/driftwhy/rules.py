"""A model-free explainer: says who did it and applies the fixed risk rules.

It can't read intent from the events the way a model can, so it never says
keep. It is the fallback with no API key, and the baseline the model has to
beat.
"""

from .explain import Explanation


def rules_explain(d, changes, risks, events) -> Explanation:
    if not events:
        return Explanation(
            verdict="unclear",
            who="unknown",
            why="No audit event touched this resource. Ask the team that owns it.",
        )
    last = events[-1]
    who = last.actor
    ids = [e.id for e in events]
    if risks:
        return Explanation(
            verdict="revert",
            who=who,
            why=f"{last.name} by {who} is risky ({'; '.join(risks)}) and nothing here explains it.",
            evidence=ids,
            confidence="medium",
        )
    return Explanation(
        verdict="unclear",
        who=who,
        why=f"Changed by {who} ({', '.join(e.name for e in events)}). Ask them whether to keep it.",
        evidence=ids,
        confidence="low",
    )

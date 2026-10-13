"""Check a model's answer against the evidence it was given."""

from .explain import Explanation


def check(ex: Explanation, events) -> tuple[Explanation, list[str]]:
    """Drop cited events that weren't given, and don't let a verdict stand on
    nothing. Returns the corrected answer and notes on what was changed."""
    notes = []
    known = {e.id for e in events}
    invented = [i for i in ex.evidence if i not in known]
    if invented:
        notes.append(f"the model cited events that don't exist: {', '.join(invented)}")
        ex = ex.model_copy(update={"evidence": [i for i in ex.evidence if i in known]})
    if ex.verdict != "unclear" and not events:
        notes.append(f"the model said {ex.verdict} with no audit events to go on")
        ex = ex.model_copy(update={"verdict": "unclear", "confidence": "low"})
    elif invented and not ex.evidence:
        notes.append("none of its evidence was real, so the verdict is set to unclear")
        ex = ex.model_copy(update={"verdict": "unclear", "confidence": "low"})
    return ex, notes

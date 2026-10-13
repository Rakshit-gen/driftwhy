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
    actors = {e.actor for e in events}
    if ex.who not in actors and ex.who != "unknown":
        # Accept "alice" for "user alice", but not a name that isn't in the events.
        match = [a for a in actors if a.endswith((" " + ex.who, "/" + ex.who))]
        real = match[0] if len(match) == 1 else (events[-1].actor if events else "unknown")
        if not match:
            notes.append(f"the model named {ex.who!r}, who is not in the events")
        ex = ex.model_copy(update={"who": real})
    return ex, notes

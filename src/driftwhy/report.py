"""Plain-text report of the findings."""

import json

from .diff import Change
from .fixes import next_step


def change_line(c: Change) -> str:
    if c.kind == "changed":
        return f"{c.path}: {json.dumps(c.old)} -> {json.dumps(c.new)}"
    item = c.new if c.kind == "added" else c.old
    short = ", ".join(f"{k}={json.dumps(v)}" for k, v in item.items() if v not in ("", [], None))
    return f"{c.path}: {c.kind} {short}" if isinstance(item, dict) else f"{c.path}: {c.kind} {item}"


def decision_of(item, decisions: dict | None) -> tuple[str, bool]:
    """(decision, whether a person made it)."""
    if decisions and item.index in decisions:
        return decisions[item.index], True
    return item.explanation.verdict, False


def summary(items, decisions=None) -> str:
    counts = {"revert": 0, "keep": 0, "unclear": 0, "skip": 0}
    for it in items:
        counts[decision_of(it, decisions)[0]] += 1
    parts = [f"{counts['revert']} to revert", f"{counts['keep']} to keep"]
    parts.append(f"{counts['unclear'] + counts['skip']} undecided")
    noun = "resource" if len(items) == 1 else "resources"
    return f"{len(items)} {noun} drifted: " + ", ".join(parts) + "."


def text_report(items, decisions=None) -> str:
    if not items:
        return "No drift: the infrastructure matches the Terraform state."
    out = [summary(items, decisions), ""]
    for it in items:
        out += item_lines(it, decisions)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def item_lines(it, decisions=None) -> list[str]:
    out = []
    decision, by_person = decision_of(it, decisions)
    ex = it.explanation
    label = "decided" if by_person else f"suggested, {ex.confidence} confidence"
    out.append(f"{it.drift.address}  {decision.upper()} ({label})")
    for c in it.changes:
        out.append(f"  changed: {change_line(c)}")
    for r in it.risks:
        out.append(f"  risk:    {r}")
    when = f", {it.events[-1].time:%Y-%m-%d %H:%M} UTC" if it.events else ""
    out.append(f"  who:     {ex.who}{when}")
    out.append(f"  why:     {ex.why}")
    step = next_step(it, decision).replace("\n", "\n           ")
    out.append(f"  next:    {step}")
    return out

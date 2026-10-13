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
    for n in it.notes:
        out.append(f"  note:    {n}")
    step = next_step(it, decision).replace("\n", "\n           ")
    out.append(f"  next:    {step}")
    return out


def markdown_report(items, decisions=None) -> str:
    """A table and details, for a pull request or issue comment."""
    if not items:
        return "No drift: the infrastructure matches the Terraform state.\n"
    out = [f"**{summary(items, decisions)}**", "", "| resource | decision | who | risk |"]
    out.append("|---|---|---|---|")
    for it in items:
        decision, by_person = decision_of(it, decisions)
        mark = decision if by_person else f"{decision} (suggested)"
        risk = "; ".join(it.risks) or "-"
        out.append(f"| `{it.drift.address}` | {mark} | {it.explanation.who} | {risk} |")
    for it in items:
        decision, _ = decision_of(it, decisions)
        out += ["", f"<details><summary><code>{it.drift.address}</code></summary>", ""]
        out += [f"- {change_line(c)}" for c in it.changes] or ["- deleted outside Terraform"]
        out += ["", it.explanation.why, ""]
        out += [f"> {n}" for n in it.notes]
        out += ["```", next_step(it, decision), "```", "</details>"]
    return "\n".join(out) + "\n"


def json_report(items, decisions=None) -> str:
    rows = []
    for it in items:
        decision, by_person = decision_of(it, decisions)
        rows.append(
            {
                "address": it.drift.address,
                "action": it.drift.action,
                "decision": decision,
                "decided_by_person": by_person,
                "changes": [
                    {"path": c.path, "kind": c.kind, "old": c.old, "new": c.new} for c in it.changes
                ],
                "risks": it.risks,
                "explanation": it.explanation.model_dump(),
                "events": [e.id for e in it.events],
                "notes": it.notes,
                "next_step": next_step(it, decision),
            }
        )
    return json.dumps(rows, indent=2) + "\n"

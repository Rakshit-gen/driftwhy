"""What the model is asked, and the shape of its answer."""

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .audit import Event
from .diff import Change
from .drift import Drift

Verdict = Literal["keep", "revert", "unclear"]


class Explanation(BaseModel):
    verdict: Verdict = Field(
        description="keep: write the change into Terraform. revert: let Terraform put it back."
        " unclear: the evidence doesn't say."
    )
    who: str = Field(description="who made the change, from the events, or 'unknown'")
    why: str = Field(description="the likely reason, in one or two plain sentences")
    evidence: list[str] = Field(
        default_factory=list, description="eventIDs of the events this is based on"
    )
    confidence: Literal["low", "medium", "high"] = "low"


SYSTEM = """You review infrastructure drift: changes made outside Terraform.
For one resource you get the attributes that changed, any risk flags, and the
CloudTrail events that touched it. Decide whether the change should be kept
(written into the Terraform code) or reverted (Terraform puts it back).

Rules:
- Base the answer only on the events given. Cite their eventIDs in evidence.
  Never invent an eventID, a person or a ticket.
- If no event explains the change, the verdict is unclear and who is unknown.
- A change made during an incident, with a ticket or incident tag, by the
  on-call role, is usually a fix that should be kept and written into code.
- A risky change (see the flags) is only kept if the events show a clear,
  deliberate reason. Otherwise revert.
- Plain, short sentences."""


def describe(d: Drift, changes: list[Change], risks: list[str], events: list[Event]) -> str:
    lines = [f"Resource: {d.address} ({d.type})"]
    if d.action == "delete":
        lines.append("It was deleted outside Terraform.")
    for c in changes:
        if c.kind == "changed":
            lines.append(f"- {c.path}: {json.dumps(c.old)} -> {json.dumps(c.new)}")
        else:
            item = c.new if c.kind == "added" else c.old
            lines.append(f"- {c.path}: {c.kind} {json.dumps(item, sort_keys=True)}")
    lines.append("Risk flags: " + (", ".join(risks) if risks else "none"))
    if not events:
        lines.append("Events: none found in the audit log.")
    for e in events:
        params = json.dumps(e.params, sort_keys=True)
        lines.append(
            f"Event {e.id}: {e.time:%Y-%m-%d %H:%M} UTC, {e.name} by {e.actor}"
            f" via {e.user_agent or 'unknown client'}, parameters {params}"
        )
    return "\n".join(lines)


def messages(d: Drift, changes, risks, events) -> list:
    return [SystemMessage(SYSTEM), HumanMessage(describe(d, changes, risks, events))]

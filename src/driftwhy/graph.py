"""The LangGraph workflow.

    START --(one Send per drifted resource)--> analyse --> collect --> review --> END

Each resource is analysed on its own branch, so a slow model call for one
doesn't hold up the rest, and the branches run concurrently. The review step
is optional: it stops the graph once per resource and waits for a person to
answer keep, revert or skip. That needs a checkpointer, so the graph can be
resumed where it stopped.
"""

import operator
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from .audit import Event
from .diff import Change, changes
from .drift import Drift
from .explain import Explanation
from .guard import check
from .match import events_for
from .risk import risks


@dataclass
class Item:
    index: int  # position in the drift file, to keep the report in that order
    drift: Drift
    changes: list[Change]
    risks: list[str]
    events: list[Event]
    explanation: Explanation
    decision: str | None = None  # what a person chose: keep, revert or skip
    notes: list[str] = field(default_factory=list)


class State(TypedDict, total=False):
    drift: list[Drift]
    events: list[Event]
    items: Annotated[list[Item], operator.add]
    decisions: dict[int, str]  # item index -> what the reviewer chose


class Branch(TypedDict):
    index: int
    drift: Drift
    events: list[Event]


DECISIONS = ("keep", "revert", "skip")


def build_graph(explainer, checkpointer=None, review: bool = False, max_events: int = 20):
    def fan_out(state: State):
        return [
            Send("analyse", {"index": i, "drift": d, "events": state["events"]})
            for i, d in enumerate(state["drift"])
        ] or [Send("collect", {})]

    def analyse(b: Branch):
        d = b["drift"]
        c = changes(d)
        r = risks(d, c)
        ev = events_for(d, b["events"])
        cut = []
        if len(ev) > max_events:
            # Keep the prompt small: the latest changes are the ones that matter.
            cut = [f"{len(ev) - max_events} earlier events were not shown to the model"]
            ev = ev[-max_events:]
        ex, notes = check(explainer(d, c, r, ev), ev)
        notes = cut + notes
        return {"items": [Item(b["index"], d, c, r, ev, ex, notes=notes)]}

    def collect(state: State):
        return {}

    def review_node(state: State):
        # One interrupt per resource. On resume LangGraph replays this node and
        # hands back the answers already given, in order.
        decisions = {}
        for it in sorted(state["items"], key=lambda it: it.index):
            answer = interrupt(
                {
                    "address": it.drift.address,
                    "verdict": it.explanation.verdict,
                    "why": it.explanation.why,
                    "risks": it.risks,
                }
            )
            if answer not in DECISIONS:
                raise ValueError(f"answer must be one of {', '.join(DECISIONS)}, got {answer!r}")
            decisions[it.index] = answer
        return {"decisions": decisions}

    g = StateGraph(State)
    g.add_node("analyse", analyse)
    g.add_node("collect", collect)
    g.add_conditional_edges(START, fan_out, ["analyse", "collect"])
    g.add_edge("analyse", "collect")
    if review:
        g.add_node("review", review_node)
        g.add_edge("collect", "review")
        g.add_edge("review", END)
    else:
        g.add_edge("collect", END)
    return g.compile(checkpointer=checkpointer)


def analyse_all(drift: list[Drift], events: list[Event], explainer, max_events=20) -> list[Item]:
    out = build_graph(explainer, max_events=max_events).invoke(
        {"drift": drift, "events": events, "items": []}
    )
    return sorted(out["items"], key=lambda it: it.index)

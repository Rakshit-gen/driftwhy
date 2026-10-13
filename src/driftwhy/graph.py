"""The LangGraph workflow.

    START --(one Send per drifted resource)--> analyse --> collect --> END

Each resource is analysed on its own branch, so a slow model call for one
doesn't hold up the rest, and the branches run concurrently.
"""

import operator
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .audit import Event
from .diff import Change, changes
from .drift import Drift
from .explain import Explanation
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


class Branch(TypedDict):
    index: int
    drift: Drift
    events: list[Event]


def build_graph(explainer, checkpointer=None):
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
        return {"items": [Item(b["index"], d, c, r, ev, explainer(d, c, r, ev))]}

    def collect(state: State):
        return {}

    g = StateGraph(State)
    g.add_node("analyse", analyse)
    g.add_node("collect", collect)
    g.add_conditional_edges(START, fan_out, ["analyse", "collect"])
    g.add_edge("analyse", "collect")
    g.add_edge("collect", END)
    return g.compile(checkpointer=checkpointer)


def analyse_all(drift: list[Drift], events: list[Event], explainer) -> list[Item]:
    out = build_graph(explainer).invoke({"drift": drift, "events": events, "items": []})
    return sorted(out["items"], key=lambda it: it.index)

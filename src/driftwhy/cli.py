"""Command line entry point."""

import argparse
import sys

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from . import __version__
from .audit import load_events
from .drift import DriftError, load_drift
from .graph import analyse_all, build_graph
from .llm import make_explainer
from .report import item_lines, json_report, markdown_report, text_report

FORMATS = {"text": text_report, "markdown": markdown_report, "json": json_report}

SHORT = {
    "k": "keep",
    "r": "revert",
    "s": "skip",
    "keep": "keep",
    "revert": "revert",
    "skip": "skip",
}


def review(drift, events, explainer, ask=None):
    """Walk a person through each resource. Returns (items, decisions)."""
    ask = ask or input
    app = build_graph(explainer, InMemorySaver(), review=True)
    cfg = {"configurable": {"thread_id": "review"}}
    out = app.invoke({"drift": drift, "events": events, "items": []}, cfg)
    while "__interrupt__" in out:
        (question,) = out["__interrupt__"]
        state = app.get_state(cfg).values
        item = next(it for it in state["items"] if it.drift.address == question.value["address"])
        print("\n".join(item_lines(item)))
        default = item.explanation.verdict if item.explanation.verdict != "unclear" else "skip"
        while True:
            raw = ask(f"keep, revert or skip? [{default}] ").strip().lower() or default
            if raw in SHORT:
                break
            print("type k, r or s")
        print()
        out = app.invoke(Command(resume=SHORT[raw]), cfg)
    return sorted(out["items"], key=lambda it: it.index), out.get("decisions", {})


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="driftwhy",
        description="Find out who changed your infrastructure outside Terraform, and whether"
        " to keep it.",
    )
    p.add_argument("drift", help="`terraform show -json` of a refresh-only plan")
    p.add_argument(
        "--audit",
        action="append",
        default=[],
        help="CloudTrail export (JSON or JSON lines); repeat for several files",
    )
    p.add_argument(
        "--model",
        help="rules, or groq:<model id> (default: groq:openai/gpt-oss-120b when GROQ_API_KEY"
        " is set, else rules)",
    )
    p.add_argument("-f", "--format", choices=FORMATS, default="text")
    p.add_argument("--review", action="store_true", help="decide on each resource, one by one")
    p.add_argument("--version", action="version", version=f"driftwhy {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        drift = load_drift(args.drift)
        events = sorted((e for path in args.audit for e in load_events(path)), key=lambda e: e.time)
        explainer = make_explainer(args.model)
        if args.review:
            items, decisions = review(drift, events, explainer)
        else:
            items, decisions = analyse_all(drift, events, explainer), None
    except (DriftError, ValueError, OSError) as e:
        print(f"driftwhy: {e}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nstopped; nothing was changed", file=sys.stderr)
        return 130
    print(FORMATS[args.format](items, decisions), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())

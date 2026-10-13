"""Command line entry point."""

import argparse
import sys

from . import __version__
from .audit import load_events
from .drift import DriftError, load_drift
from .graph import analyse_all
from .llm import make_explainer
from .report import text_report


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
    p.add_argument("--version", action="version", version=f"driftwhy {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        drift = load_drift(args.drift)
        events = sorted((e for path in args.audit for e in load_events(path)), key=lambda e: e.time)
        explainer = make_explainer(args.model)
        items = analyse_all(drift, events, explainer)
    except (DriftError, ValueError, OSError) as e:
        print(f"driftwhy: {e}", file=sys.stderr)
        return 2
    print(text_report(items), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())

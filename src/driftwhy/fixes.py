"""Turn a decision into the concrete next step."""

import json

from .diff import Change


def hcl(value, indent: int = 0) -> str:
    """A Terraform value literal for JSON-shaped data."""
    pad = "  " * (indent + 1)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int | float):
        return json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(hcl(v, indent) for v in value) + "]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        body = "\n".join(f"{pad}{k} = {hcl(v, indent + 1)}" for k, v in sorted(value.items()))
        return "{\n" + body + "\n" + "  " * indent + "}"
    raise TypeError(f"can't write {type(value).__name__} as HCL")


def block(name: str, attrs: dict) -> str:
    body = "\n".join(f"  {k} = {hcl(v, 1)}" for k, v in sorted(attrs.items()))
    return f"{name} {{\n{body}\n}}"


def code_change(after: dict, changes: list[Change]) -> str:
    """The lines to put in the resource block so the code matches what's running."""
    out, done = [], set()
    for c in changes:
        top = c.path.split(".")[0]
        if c.kind == "added":
            out.append("# add\n" + block(top, {k: v for k, v in c.new.items() if v != ""}))
        elif c.kind == "removed":
            out.append("# remove\n" + block(top, {k: v for k, v in c.old.items() if v != ""}))
        elif top not in done:
            # A nested change (tags.incident) rewrites the whole top-level attribute.
            out.append(f"{top} = {hcl(after.get(top))}")
            done.add(top)
    return "\n".join(out)


def next_step(item, decision: str | None = None) -> str:
    d = item.drift
    decision = decision or item.explanation.verdict
    if decision == "revert":
        verb = "recreates" if d.action == "delete" else "puts back"
        return f"terraform apply -target={d.address}  # {verb} what the code says"
    if decision == "keep":
        if d.action == "delete":
            return f"terraform state rm {d.address}  # and delete its block from the code"
        return f"In the resource block for {d.address}:\n" + code_change(d.after, item.changes)
    return "No change until someone decides."

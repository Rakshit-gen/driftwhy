"""Fixed rules for drift that needs a person, whatever the model says."""

from .diff import Change
from .drift import Drift

WORLD = {"0.0.0.0/0", "::/0"}
WEB_PORTS = {80, 443}


def _opens_to_world(rule: dict) -> bool:
    cidrs = set(rule.get("cidr_blocks") or []) | set(rule.get("ipv6_cidr_blocks") or [])
    if not cidrs & WORLD:
        return False
    lo, hi = rule.get("from_port", 0), rule.get("to_port", 0)
    return not (lo == hi and lo in WEB_PORTS)


def risks(d: Drift, changes: list[Change]) -> list[str]:
    out = []
    if d.action == "delete":
        out.append("deleted outside Terraform")
    if d.type.startswith("aws_iam_"):
        out.append("IAM change")
    for c in changes:
        if c.kind == "added" and c.path in ("ingress", "egress") and isinstance(c.new, dict):
            if c.path == "ingress" and _opens_to_world(c.new):
                port = c.new.get("from_port")
                out.append(f"port {port} open to the internet")
        if c.path.startswith("block_public") and c.new is False:
            out.append(f"{c.path} turned off")
        if "encrypt" in c.path and c.new is False:
            out.append(f"{c.path} turned off")
    return out

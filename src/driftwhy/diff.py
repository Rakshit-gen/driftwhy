"""What exactly changed inside one drifted resource."""

import json
from dataclasses import dataclass

# Attributes the provider derives from others; a change there is never news.
NOISE = {"tags_all"}


@dataclass(frozen=True)
class Change:
    path: str  # e.g. "instance_type", "tags.incident", "ingress"
    old: object
    new: object
    kind: str = "changed"  # "changed", "added" (to a list) or "removed" (from a list)


def _key(item) -> str:
    return json.dumps(item, sort_keys=True)


def diff(before, after, path: str = "") -> list[Change]:
    if isinstance(before, dict) and isinstance(after, dict):
        out = []
        for k in sorted(set(before) | set(after)):
            if not path and k in NOISE:
                continue
            sub = f"{path}.{k}" if path else k
            out += diff(before.get(k), after.get(k), sub)
        return out
    if isinstance(before, list) and isinstance(after, list):
        # Blocks like ingress rules have no stable order, so compare them as sets:
        # say which items appeared and which went away.
        old = {_key(x): x for x in before}
        new = {_key(x): x for x in after}
        out = [Change(path, None, new[k], "added") for k in new if k not in old]
        out += [Change(path, old[k], None, "removed") for k in old if k not in new]
        return out
    if before != after:
        return [Change(path, before, after)]
    return []


def changes(d) -> list[Change]:
    """Changes for a Drift; a resource deleted outside Terraform has none to list."""
    if d.after is None:
        return []
    return diff(d.before, d.after)

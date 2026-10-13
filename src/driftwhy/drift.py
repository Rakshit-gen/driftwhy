"""Read drift from `terraform show -json` of a refresh-only plan.

    terraform plan -refresh-only -out drift.out
    terraform show -json drift.out > drift.json

Each entry in `resource_drift` says what Terraform last recorded (`before`)
and what the provider reports now (`after`).
"""

import json
from dataclasses import dataclass, field


class DriftError(ValueError):
    pass


@dataclass
class Drift:
    address: str
    type: str
    action: str  # "update" or "delete" (removed outside Terraform)
    before: dict
    after: dict | None
    changes: list = field(default_factory=list)  # filled in by diff.changes()


def load_drift(path) -> list[Drift]:
    try:
        with open(path) as f:
            doc = json.load(f)
    except json.JSONDecodeError as e:
        raise DriftError(f"{path}: not JSON ({e})") from e
    if not isinstance(doc, dict) or "format_version" not in doc:
        raise DriftError(f"{path}: expected the output of `terraform show -json`")
    out = []
    for r in doc.get("resource_drift") or []:
        if r.get("mode", "managed") != "managed":
            continue
        actions = r.get("change", {}).get("actions", [])
        action = "delete" if "delete" in actions else "update"
        out.append(
            Drift(
                address=r["address"],
                type=r.get("type", ""),
                action=action,
                before=r["change"].get("before") or {},
                after=r["change"].get("after"),
            )
        )
    return out

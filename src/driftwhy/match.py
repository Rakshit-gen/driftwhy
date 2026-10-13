"""Find the audit events that touched a drifted resource."""

import json

from .audit import Event
from .drift import Drift

# Attributes that name a resource in API calls, across the common AWS types.
ID_KEYS = ("id", "arn", "name", "function_name", "bucket", "url", "queue_url", "identifier")


def identifiers(d: Drift) -> set[str]:
    out = set()
    for k in ID_KEYS:
        v = d.before.get(k)
        if isinstance(v, str) and len(v) >= 3:
            out.add(v)
    return out


def events_for(d: Drift, events: list[Event], include_reads: bool = False) -> list[Event]:
    """Write events whose record contains one of the resource's identifiers as a
    whole JSON string, so "api" matches "api" but not "api-gateway"."""
    needles = [json.dumps(i) for i in identifiers(d)]
    return [
        e
        for e in events
        if (include_reads or not e.read_only) and any(n in e.text for n in needles)
    ]

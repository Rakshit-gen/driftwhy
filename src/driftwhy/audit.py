"""Read a CloudTrail export. Three shapes are accepted:

- the `{"Records": [...]}` files a trail writes to S3
- the output of `aws cloudtrail lookup-events`, where each event's record is a
  JSON string in `CloudTrailEvent`
- one record per line, or a plain JSON array of records
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Event:
    id: str
    time: datetime
    name: str  # e.g. "ModifyInstanceAttribute"
    source: str  # e.g. "ec2.amazonaws.com"
    actor: str  # who: an IAM user, or role/session for an assumed role
    actor_type: str  # "IAMUser", "AssumedRole", "Root", "AWSService", ...
    user_agent: str
    read_only: bool
    params: dict  # requestParameters
    text: str  # the whole record as JSON, for matching identifiers


def actor_of(identity: dict) -> str:
    arn = identity.get("arn", "")
    if identity.get("type") == "AssumedRole" and ":assumed-role/" in arn:
        return "role " + arn.split(":assumed-role/", 1)[1]  # "role oncall/priya"
    if identity.get("type") == "Root":
        return "root account"
    if identity.get("userName"):
        return "user " + identity["userName"]
    return arn or identity.get("invokedBy") or identity.get("type", "unknown")


def parse_time(value: str) -> datetime:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def parse_event(r: dict) -> Event:
    identity = r.get("userIdentity") or {}
    return Event(
        id=r.get("eventID", ""),
        time=parse_time(r["eventTime"]),
        name=r.get("eventName", ""),
        source=r.get("eventSource", ""),
        actor=actor_of(identity),
        actor_type=identity.get("type", ""),
        user_agent=r.get("userAgent", ""),
        read_only=bool(r.get("readOnly"))
        or r.get("eventName", "").startswith(("Describe", "Get", "List")),
        params=r.get("requestParameters") or {},
        text=json.dumps(r, sort_keys=True),
    )


def load_events(path) -> list[Event]:
    with open(path) as f:
        text = f.read()
    try:
        doc = json.loads(text)
        if isinstance(doc, dict) and "Events" in doc:
            records = [json.loads(e["CloudTrailEvent"]) for e in doc["Events"]]
        else:
            records = doc.get("Records", []) if isinstance(doc, dict) else doc
    except json.JSONDecodeError:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return sorted((parse_event(r) for r in records), key=lambda e: e.time)

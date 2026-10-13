# driftwhy

Find out who changed your infrastructure outside Terraform, and whether to keep it.

A refresh-only plan tells you that something drifted. It doesn't tell you who
changed it, when, or whether the change was a 2am incident fix that should be
written into the code or a mistake that Terraform should undo. driftwhy reads
the drift and your CloudTrail events, matches them up, and for each drifted
resource says who did it, what it suggests, and the exact next step.

It is a LangGraph agent: each resource is analysed on its own branch, a model
(Groq through LangChain) reads the events and suggests keep, revert or
unclear, and an optional review step pauses for a person to decide on each
one. Fixed rules flag risky drift whatever the model says, and every answer is
checked against the real events before it is shown.

## Quickstart

```sh
uv tool install git+https://github.com/Rakshit-gen/driftwhy

terraform plan -refresh-only -out drift.out
terraform show -json drift.out > drift.json
aws cloudtrail lookup-events --start-time 2026-10-01 > trail.json

export GROQ_API_KEY=...        # optional, see below
driftwhy drift.json --audit trail.json
```

`lookup-events` covers the last 90 days of management events in one region.
`--audit` also takes the `{"Records": [...]}` files a trail writes to S3, or
one record per line. Repeat it for several files or regions.

## Example

`examples/` has a hand-written drift file and trail (not from a real
account): SSH opened to the internet from the console, an instance resized
during an incident, a Lambda timeout changed with no trace in the trail, and
a queue deleted by the CI role. With no model (`--model rules`), this is the
output:

```
$ driftwhy examples/drift.json --audit examples/cloudtrail.json --model rules
4 resources drifted: 2 to revert, 0 to keep, 2 undecided.

aws_security_group.web  REVERT (suggested, medium confidence)
  changed: ingress: added from_port=22, to_port=22, protocol="tcp", cidr_blocks=["0.0.0.0/0"]
  risk:    port 22 open to the internet
  who:     user alice, 2026-10-10 14:03 UTC
  why:     AuthorizeSecurityGroupIngress by user alice is risky (port 22 open to the internet) and nothing here explains it.
  next:    terraform apply -target=aws_security_group.web  # puts back what the code says

aws_instance.api  UNCLEAR (suggested, low confidence)
  changed: instance_type: "t3.medium" -> "t3.large"
  changed: tags.incident: null -> "INC-2291"
  who:     role oncall/priya, 2026-10-11 02:17 UTC
  why:     Changed by role oncall/priya (ModifyInstanceAttribute, CreateTags). Ask them whether to keep it.
  next:    No change until someone decides.

aws_lambda_function.thumbnails  UNCLEAR (suggested, low confidence)
  changed: timeout: 30 -> 90
  who:     unknown
  why:     No audit event touched this resource. Ask the team that owns it.
  next:    No change until someone decides.

aws_sqs_queue.retry  REVERT (suggested, medium confidence)
  risk:    deleted outside Terraform
  who:     role ci-deploy/github-actions, 2026-10-09 09:12 UTC
  why:     DeleteQueue by role ci-deploy/github-actions is risky (deleted outside Terraform) and nothing here explains it.
  next:    terraform apply -target=aws_sqs_queue.retry  # recreates what the code says
```

The rules can say who did something and flag what's risky, but they can't
read intent, so they never suggest keep. That is the model's job: the
instance resize was made by the on-call role and tagged with an incident, which
is what the prompt tells the model to look for. No live model output is shown
here because this README only shows output from real runs, and none were made
for it.

## Deciding

```sh
driftwhy drift.json --audit trail.json --review
```

shows one resource at a time and asks keep, revert or skip (Enter takes the
suggestion, or skip when it's unclear). The graph stops at each question with a LangGraph interrupt and
resumes from its checkpoint with the answer. The report then marks those as
decided rather than suggested, and the next step follows the decision:

- keep: the HCL to put in the resource block so the code matches what's running
  (or `terraform state rm` for something deleted on purpose)
- revert: `terraform apply -target=<address>`, which puts back what the code says

## Output and CI

```sh
driftwhy drift.json --audit trail.json -f markdown   # for an issue or PR comment
driftwhy drift.json --audit trail.json -f json
driftwhy drift.json --audit trail.json --fail-on risk   # exit 1 on risky drift
```

`--fail-on` takes `any`, `risk` or `revert`. Errors exit 2.

## Models

With `GROQ_API_KEY` set, the default is `groq:openai/gpt-oss-120b` (checked
against Groq's model list on 2026-10-13). Pick another with
`--model groq:<model id>`, or `--model rules` for no model at all. Each
resource is one model call with the latest 20 events (`--max-events`).

What keeps the model honest:

- It must answer in a fixed schema (verdict, who, why, evidence, confidence),
  and malformed answers are retried.
- Event IDs it cites that weren't given to it are dropped. If none of its
  evidence was real, or there were no events at all, the verdict becomes
  unclear.
- It can only name someone who appears in the events.
- Risk flags (ports open to the internet, deletions, IAM, public access,
  encryption turned off) come from fixed rules, not the model.

## How it works

```
START --(one Send per resource)--> analyse --> collect --> review --> END
```

`analyse` diffs the resource (lists like ingress rules are compared as sets,
`tags_all` is ignored), finds the audit write events whose record contains one
of the resource's identifiers as a whole value, applies the risk rules, asks
the explainer, and checks the answer. `review` is only added with `--review`.

## Measured vs Claimed

| Claim | Value | How measured | Date |
|---|---|---|---|
| Finds who changed each resource in the example | 3 of 3 with events; the 4th correctly unknown | `tests/test_match.py`, `tests/test_rules.py` | 2026-10-13 |
| Made-up evidence and names are caught | invented event IDs dropped, verdict downgraded, unknown names replaced | `tests/test_guard.py` with a scripted model | 2026-10-13 |
| Branches run concurrently | more than one thread used | `tests/test_graph.py` | 2026-10-13 |
| Model quality on real drift | not measured | no live model runs yet | |

## Status

Works: everything above, with 49 tests that never call a model API (a
scripted fake stands in for it).

Not done: AWS only (CloudTrail); other clouds' audit logs aren't read. The
HCL for keep covers plain attributes and blocks, not dynamic blocks or values
that come from variables, so check it before pasting. `-target` is the
quickest way to revert one resource, but Terraform recommends a full plan
afterwards.

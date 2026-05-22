# DRP and ADR

This document explains how DRP relates to Architecture Decision Records (ADR).

The short version:

- ADR is a strong human-readable practice for documenting architecture choices.
- DRP is a machine-readable protocol for decision records with validation,
  causal links, and supersession rules.
- DRP can complement ADR rather than replace it.

## What ADR is good at

Architecture Decision Records are useful because they capture the narrative of a
choice:

- the architectural context;
- the decision that was made;
- alternatives considered;
- consequences;
- human reasoning.

ADR is intentionally readable. A good ADR helps future maintainers understand
why a system looks the way it does.

## What DRP adds

DRP focuses on the machine-checkable part of decision history.

It adds:

- stable `record_id` values;
- explicit status values;
- explicit parent and child record links;
- explicit supersession instead of silent overwrite;
- JSON Schema for shape validation;
- semantic validation for protocol rules;
- graph validation for causal consistency;
- fixtures and tests for regression checking.

ADR explains a decision. DRP validates the structured state around a decision.

## Comparison

| Dimension | ADR | DRP |
|---|---|---|
| Primary form | Markdown or prose document | Structured JSON record |
| Main audience | Humans | Humans and tools |
| Main strength | Narrative explanation | Machine-checkable decision state |
| Stable identifiers | Optional or convention-based | Required `record_id` |
| Causal links | Informal references | Explicit parent and child IDs |
| Supersession | Usually handled by text or status | Explicit `supersedes_record_id` |
| Validation | Mostly manual review | Schema plus reference validator |
| CI integration | Project-specific | Built into the reference tooling path |
| Graph invariants | Not usually enforced | Part of the protocol contract |

## How they can work together

A practical repository can use both:

```text
ADR document
  explains the reasoning and context in prose

DRP record
  captures the structured state, causal links, status, and supersession
```

For example, an ADR might describe why a team moved from one storage system to
another. A DRP record can capture the decision as a validateable object, link it
to prior records, and mark a previous decision as superseded.

## Example pairing

ADR narrative:

```text
We decided to switch the event log format to JSONL because it is easier to
stream, inspect, and validate in CI. YAML was considered but rejected because it
introduced ambiguous parsing behavior.
```

DRP structured state:

```json
{
  "record_id": "decision-log-format-jsonl",
  "timestamp": "2026-04-19T12:00:00Z",
  "context": "Choose canonical event log format for validation fixtures.",
  "decision": "Use JSONL as the canonical event log format.",
  "options": ["JSONL", "YAML"],
  "status": "complete",
  "impact": 1,
  "parent_record_ids": [],
  "child_record_ids": [],
  "supersedes_record_id": null,
  "metadata": {
    "adr": "docs/adr/0001-event-log-format.md"
  }
}
```

The ADR gives the human story. The DRP record gives the structured contract.

## When ADR is enough

ADR may be enough when:

- the decision is mostly architectural narrative;
- no automated validation is needed;
- there are few dependencies between decisions;
- the decision history is maintained by a small team;
- free-form prose is sufficient.

## When DRP helps

DRP helps when:

- decisions need stable IDs;
- multiple records depend on each other;
- old decisions must be superseded without silent mutation;
- CI should reject invalid decision history;
- AI agents or tools need structured decision context;
- auditability matters.

## Recommendation

Use ADR for explanation.
Use DRP for structured, validateable decision state.

Together, they give both narrative clarity and protocol-level integrity.

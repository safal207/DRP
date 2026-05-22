# Why DRP

DRP exists because important decisions often outlive the place where they were
made.

A decision may start in a chat thread, issue comment, incident room, meeting
note, architecture document, or agent trace. At the moment it is made, the
context can feel obvious. Weeks later, the decision may still matter, but the
reasoning around it has become hard to recover.

DRP provides a small protocol for preserving that decision history in a
structured, linkable, and validateable form.

## The problem

Most decision records are written as free-form prose. Free-form notes are useful
for human explanation, but they are weak as durable records:

- they do not enforce stable identifiers;
- they do not reliably preserve parent decisions;
- they can be edited without recording what changed;
- they are hard to validate automatically;
- they do not expose broken references or invalid causal order;
- they are difficult to test in CI.

This matters when decisions are reused by people, teams, agents, governance
processes, or later audits.

## What DRP adds

DRP turns a decision into a structured record with explicit fields:

- what was decided;
- why the decision was made;
- what options were considered;
- what earlier records it depends on;
- what later records depend on it;
- whether the record is proposed, incomplete, complete, or superseded;
- whether a newer record replaced it.

The result is not just a note. It is a record that can be checked.

## Why validation matters

A schema can confirm that a record has the right shape. That is necessary, but
not enough.

Decision history also has graph-level rules:

- record identifiers must be unique;
- parent and child references must resolve;
- parent and child links must agree with each other;
- parent records must not happen after child records;
- superseded records must point to real replacement context;
- invalid values such as boolean `impact` must be rejected.

DRP includes a reference validator because these rules are part of the protocol,
not optional application behavior.

## Why this matters for AI systems

AI agents increasingly make or recommend multi-step decisions. Without a stable
record format, those decisions are easy to lose, misread, or replay without the
context that justified them.

DRP gives agentic systems a minimal structure for preserving decision state:

```text
context -> decision record -> causal links -> validation -> audit trail
```

This does not make an agent safe by itself. It creates a record layer that can
be inspected, tested, and connected to other oversight systems.

## Why this matters for teams

Teams often know what was decided, but not why the decision changed.

DRP helps teams preserve:

- incident rollback chains;
- architecture decisions;
- policy updates;
- safety evaluation outcomes;
- product or operational decisions;
- later supersession of earlier decisions.

The goal is not to replace human narrative. The goal is to make the core state
of a decision machine-checkable.

## What DRP is not

DRP is not:

- a project management tool;
- a database;
- a workflow engine;
- an identity system;
- a replacement for all design documentation;
- a guarantee that a decision was good.

DRP records structure and relationships. It does not prove correctness or
wisdom. That remains a human, organizational, or system-level judgment.

## Where to go next

- Read the formal protocol: [SPEC.md](SPEC.md)
- Read the validation contract: [VALIDATION.md](VALIDATION.md)
- See design rationale: [DESIGN.md](DESIGN.md)
- Try examples: [../examples](../examples)
- Inspect invalid fixtures: [../fixtures/invalid](../fixtures/invalid)

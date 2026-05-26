# DRP Public Announcement Drafts

This document contains concise public copy for explaining DRP. It is meant to
be edited before posting, not treated as a formal protocol document.

## Short repository pitch

DRP is a lightweight protocol for structured decision records with causal links,
explicit supersession, JSON Schema, and validator-backed integrity.

It helps teams and AI systems preserve what was decided, why it was decided,
what it depended on, and what replaced it later.

## One-sentence version

DRP turns scattered decision notes into machine-readable, validateable records
with causal history and auditable supersession.

## Short social post

I released DRP: a lightweight Decision Record Protocol for structured,
machine-readable decision history.

It captures:

- what was decided
- why it was decided
- what options were considered
- what prior records it depends on
- what later replaced it

The repo includes a formal spec, JSON Schema, reference validator, examples,
fixtures, tests, and auditability benchmark material.

Repository: https://github.com/safal207/DRP

## Longer professional post

I have been working on DRP, a Decision Record Protocol for preserving decisions
as structured, linkable, and validateable records.

The motivation is simple: many important decisions begin in chats, tickets,
meeting notes, incident rooms, or AI agent traces. At the time, the context feels
obvious. Later, the decision may still matter, but the reasoning chain is hard
to reconstruct.

DRP defines a small protocol for recording:

- the decision context
- the decision itself
- considered options
- status
- impact
- parent and child decision links
- explicit supersession instead of silent overwrite

The repository includes:

- formal specification
- JSON Schema
- reference validator
- valid and invalid fixtures
- tests
- CLI usage
- auditability benchmark material
- comparison with ADR

DRP is not meant to replace human-readable decision documents. It is a structured
protocol layer that can complement ADRs, postmortems, safety reviews, and agent
oversight systems.

Repository: https://github.com/safal207/DRP

## Technical community post

DRP is a small spec-first repository for machine-readable decision records.

It defines a JSON record model plus validation rules for:

- unique record IDs
- status and impact constraints
- parent and child causal links
- bidirectional link consistency
- timestamp ordering
- explicit supersession
- invalid fixture regression testing

The goal is to make decision history easier to validate, test, and audit across
teams and toolchains.

This is early and intentionally lightweight. Feedback on the spec, validator,
fixtures, and use cases is welcome.

Repository: https://github.com/safal207/DRP

## Suggested launch checklist

Before posting publicly:

- confirm CI is green on `main`;
- confirm README badges render;
- confirm `docs/WHY_DRP.md` and `docs/COMPARISON_ADR.md` are linked;
- confirm latest release notes are readable;
- create a few `good first issue` tasks for examples, fixtures, or docs;
- pin the repository if using it as a public portfolio artifact.

## What to avoid saying

Avoid claims that DRP does not prove yet:

- do not claim it guarantees safe AI behavior;
- do not claim it proves decisions are correct;
- do not claim production adoption without evidence;
- do not claim it replaces ADR, governance systems, or audit processes.

Safer framing:

- DRP provides structure.
- DRP provides validation.
- DRP improves auditability.
- DRP creates a testable decision-record layer.

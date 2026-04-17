# DRP Design Rationale

This document explains *why* DRP looks the way it does. It is not
normative — [SPEC.md](SPEC.md) is. It exists to prevent well-meaning
but corrosive changes to the format.

## Records are append-only

A DRP record, once emitted, is meant to stand as historical fact. The
protocol does not define an edit operation. The reasons:

1. **Auditability requires a stable past.** If records could be edited
   in place, older records could silently change their meaning,
   defeating the whole point of keeping them.
2. **Diffing works.** Append-only records diff cleanly. Two batches can
   be compared by `record_id` without needing an edit history.
3. **Distribution is easier.** Immutable records can be cached,
   mirrored, and merged without conflict resolution logic.

The cost is that corrections require a second record. That is the job
of supersession.

## `superseded` exists instead of in-place mutation

When a decision needs to be revised, DRP requires emitting a new record
and marking the old one with `status: superseded` plus a
`supersedes_record_id` pointer **on the replacing record** (see §8 of
the spec).

Alternatives considered and rejected:

- **Editing the old record.** Loses history; see above.
- **Soft-delete flags.** Ambiguous: "deleted" does not say *why*, nor
  what replaced it.
- **A single `previous_version` field on the new record without a
  distinct status.** Loses the ability to distinguish "this decision is
  still active" from "this decision has been replaced" by looking at
  the record alone.

Supersession is modeled as a first-class relation with its own
invariants (S1–S5) precisely so validators can treat it as a real
semantic state, not a variation of `complete`.

## Parent/child causal links are explicit

A decision is rarely taken in isolation. DRP models causality with
`parent_record_ids` and the inverse `child_record_ids`.

Why both sides:

1. **Local reasoning.** A record can state, in isolation, which
   decisions motivated it.
2. **Traversal in either direction.** Given the batch, you can walk
   up (to motivations) or down (to consequences) without recomputing
   the graph.
3. **Forcing bidirectional consistency catches bugs.** If a producer
   writes only one side, the validator flags it (G3). This prevents
   silently asymmetric graphs.

The redundancy is deliberate. It is cheap to store and the validator
enforces that the two sides agree.

## Validator is required in addition to JSON Schema

JSON Schema (Draft 2020-12) is expressive, but it cannot cleanly
express:

- uniqueness of `record_id` across a batch;
- resolution of references (parent, child, supersedes);
- bidirectional consistency of parent/child edges;
- timestamp ordering between referenced records;
- the difference between `impact == 1` and `impact == true` when a JSON
  parser coerces booleans to integers.

These are all graph-level or cross-field invariants. Trying to bolt
them into schema produces brittle, hard-to-read schemas that still do
not cover every case. Shipping a reference validator is cleaner: the
schema covers shape, the validator covers meaning.

## `impact` is intentionally constrained

`impact` is restricted to `{-1, 0, 1, null}` — not a free integer, not
a float, not a string enum like `"high" / "low"`.

Reasons:

1. **Cross-record comparability.** `impact` should be aggregable across
   decisions without scale calibration. A three-way ordinal is the
   largest set that survives aggregation without becoming meaningless.
2. **Resistance to grade inflation.** A 1–10 scale collapses to 7–9 in
   practice. A three-way ordinal forces a coarse but honest signal.
3. **`null` is first-class.** "Not yet assessed" is different from
   "zero impact" and the protocol refuses to conflate them.
4. **Booleans are rejected.** `true` and `false` are not impact values;
   accepting them would silently map to `1` / `0` in languages that
   conflate the types, corrupting aggregates.

If finer-grained impact is needed, it belongs in `metadata`, where it
does not participate in cross-record aggregation.

## Small, closed field set

Top-level fields are closed (`additionalProperties: false`). Extensions
go in `metadata`. This keeps the core record shape stable and avoids a
slow drift into heterogeneous records where each producer invents its
own top-level keys.

## No embedded protocol version

A record does not carry a `drp_version` field. Versioning applies to
the *batch* and to the *tool that produced it*. Embedding a version in
every record invites half-migrated batches where records disagree about
what version they conform to.

## Timestamps are UTC ISO 8601

A single canonical timestamp format avoids ambiguity. UTC avoids
timezone arithmetic during graph validation (G4, S4). Producers that
want to record local time can put it in `metadata`.

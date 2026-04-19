# DRP Auditability Benchmark Pack

The auditability pack at
[`benchmark/drp_auditability_pack/`](../benchmark/drp_auditability_pack/)
is a small, opinionated collection of DRP artifacts designed to exercise
and illustrate the properties DRP is trying to improve over free-form
decision logs. It is not a performance benchmark and it is not a
research claim -- see section 4 for what it does *not* do.

This document explains what the pack contains, how to use it, and what
the design choices are.

## 1. Purpose

The pack exists for three reasons:

1. **Illustration.** Each fixture maps to a realistic safety or
   governance scenario drawn from the use case docs
   (see [USE_CASE_SAFETY_EVAL.md](USE_CASE_SAFETY_EVAL.md),
   [USE_CASE_INCIDENT_ROLLBACK.md](USE_CASE_INCIDENT_ROLLBACK.md),
   [USE_CASE_POLICY_SUPERSESSION.md](USE_CASE_POLICY_SUPERSESSION.md)).
   Reviewers can see what DRP records look like under real pressure,
   not just on minimal examples.
2. **Regression surface.** The fixtures exercise the invariants the
   reference validator enforces and several the validator deliberately
   does *not* enforce. Any future tooling (downstream validators, audit
   linters, CI helpers) can be evaluated against the same pack.
3. **Seed for empirical work.** See [RESEARCH_NOTE.md](RESEARCH_NOTE.md)
   for how the pack is intended to seed later, more rigorous evaluation
   of structured decision records.

## 2. Categories

The pack is organized into four subdirectories. Each category has a
distinct purpose.

### 2.1 `valid/`

Chains that the reference validator accepts and that represent
well-formed audit trails for a realistic scenario.

Included:

- `go_no_go_chain.json` -- safety eval summary -> restricted deploy ->
  later expansion to general availability (supersession).
- `incident_rollback_chain.json` -- deploy -> incident report -> emergency
  rollback -> corrective patched redeploy (two chained supersessions).
- `policy_supersession_chain.json` -- policy v1 -> v2 (audit-driven) ->
  v3 (scheduled review).

These are the positive cases for manual inspection or downstream
tooling.

### 2.2 `invalid/`

Chains with a concrete structural defect the reference validator
catches. Each fixture isolates a single class of defect.

Included:

- `missing_parent_reference.json` -- a decision cites an eval record as
  parent but the eval record is absent from the batch. Catches G1.
- `cyclic_chain.json` -- two policy records with equal timestamps and
  mutual parent/child edges form a cycle. Catches G6; G4 alone cannot.
- `broken_supersession_target.json` -- a corrective decision names a
  superseded record that is not in the batch. Catches S2.
- `broken_bidirectional_links.json` -- a decision lists a parent, but
  the parent record does not list it as a child. Catches G3.

Each fixture is expected to cause `drp-validate` to exit with code `1`.

### 2.3 `ambiguous/`

Chains that are *structurally valid* -- the validator accepts them -- but
that illustrate audit-hostile shapes. These are the cases where schema
and graph validation are not enough.

Included:

- `vague_rationale.json` -- all fields are present and the graph is
  consistent, but `context`, `decision`, and `rationale` are too thin
  to support audit. A reviewer reading only the records cannot
  reconstruct what was actually being decided or why.
- `incomplete_chain.json` -- an original deploy record and a patched
  redeploy exist, but the intervening incident and rollback decisions
  were only captured in external tools. The DRP chain alone tells a
  misleading story.
- `conflicting_active_successor.json` -- two records both claim to
  supersede the same earlier record. DRP does not forbid this (see
  [USE_CASE_POLICY_SUPERSESSION.md section 6](USE_CASE_POLICY_SUPERSESSION.md)).
  Tooling that wants a single active successor must detect and resolve
  this at a higher layer.

The ambiguous category is the honest part of the benchmark. It
communicates that DRP improves auditability *conditional on records
being written honestly and the chain being complete*. It does not
fabricate quality.

### 2.4 `comparison/`

A before/after pair expressing the same incident two ways.

Included:

- `unstructured_incident_note.md` -- a plausible free-form incident note.
- `structured_incident_chain.json` -- the same incident as a DRP batch.
- `README.md` -- a small side-by-side comparing what each artifact
  supports for common reviewer queries.

This is illustration, not measurement. It shows what questions become
definite under DRP and which remain matters of prose.

## 3. Properties DRP is trying to improve

The pack exercises four properties in particular.

1. **Stable identity.** Every decision has a `record_id` that other
   records and external systems can reference. The pack assumes these
   identifiers are durable.
2. **Explicit causality.** `parent_record_ids` and `child_record_ids`
   make the motivating evidence for a decision explicit and walkable in
   both directions.
3. **Explicit supersession.** `supersedes_record_id` makes the
   "this replaces that" relationship a first-class, machine-checkable
   fact rather than a prose claim.
4. **Append-only history.** A revised decision is a new record, not an
   edit. The fixtures in `valid/` and `comparison/` show chains where
   every correction is its own record.

## 4. What the pack does NOT claim

- It does not claim DRP makes decisions better. It only claims DRP
  makes decision *records* structurally auditable.
- It does not claim these fixtures are representative of any real
  team's distribution of decisions. They are small, illustrative, and
  cherry-picked to exercise specific shapes.
- It does not claim coverage of every possible auditability failure
  mode. The ambiguous category is a sample, not an exhaustive taxonomy.
- It does not provide quantitative metrics. No pass/fail percentages
  are reported here beyond the per-file validator outcomes.
- It does not replace the regression `fixtures/` directory, which
  targets the validator implementation. The benchmark pack targets
  scenarios, not validator branches.

## 5. How to use the pack

### 5.1 Manual review

Open a fixture alongside the corresponding use case doc and check
whether the questions that doc raises (e.g. "what is currently in
effect?", "which record replaces which?") can be answered from the
fixture alone. The `comparison/` pair is the most direct way to do this
end-to-end.

### 5.2 Validator check

Run the reference validator over every fixture. Expected outcomes:

- `valid/` -- all files exit `0`.
- `invalid/` -- all files exit `1` with at least one error.
- `ambiguous/` -- all files exit `0` (the validator intentionally does
  not flag these).
- `comparison/structured_incident_chain.json` -- exits `0`.

You can do this by hand with `scripts/drp-validate`, or by running the
helper at [`scripts/run_benchmark.py`](../scripts/run_benchmark.py),
which walks the pack and summarizes outcomes per category.

### 5.3 Downstream tooling

If you are building auditability tooling on top of DRP (e.g. "tell me
the active policy", "flag decisions with empty rationale", "flag
multiple active successors"), the pack is a ready set of inputs for
your tool. The ambiguous category in particular is where downstream
tooling has something to contribute that the reference validator
deliberately does not.

## 6. Stability

The pack is versioned with the rest of the repository. Scenarios may be
added in future minor releases. A fixture may be removed or renamed
only in a major release, and only when the case it covered has become
redundant with other fixtures. Where a scenario is renamed, the pack
notes the change in [CHANGELOG.md](../CHANGELOG.md).

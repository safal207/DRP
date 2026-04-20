# DRP Specification

**Version:** 0.1.0
**Status:** Draft

This document is the normative specification of the Decision Record
Protocol (DRP). Lower-case terms like "record" and "batch" are defined
below. Upper-case MUST / SHOULD / MAY follow [RFC 2119].

[RFC 2119]: https://www.rfc-editor.org/rfc/rfc2119

## 1. Purpose

DRP defines a data format for representing individual decisions as
structured, immutable records and for expressing causal and supersession
relationships between those records. The goals are:

1. **Auditability.** Every decision is a self-contained record with a
   stable identifier and a timestamp.
2. **Machine-checkability.** Records validate against a published schema
   and a published set of invariants.
3. **Traceability.** Decisions can point to the decisions that motivated
   them and, when revised, to the decisions they replace.

DRP does *not* prescribe storage, transport, or UI. A DRP record is a
JSON value. A DRP batch is a JSON array of records.

## 2. Terminology

- **Record** — a single JSON object conforming to §4.
- **Batch** — a JSON array whose elements are records. A batch is the
  unit of validation for graph-level invariants (§7).
- **Record ID** — the value of a record's `record_id` field. Unique
  within a batch.
- **Parent** — a record referenced by another record's
  `parent_record_ids`.
- **Child** — the inverse: a record that references a given record as
  its parent.
- **Supersession** — the relation expressed by `supersedes_record_id`.
- **Validator** — the reference implementation in `tools/drp_validator.py`
  that enforces both schema and semantic invariants.

## 3. Encoding

- A record MUST be a valid JSON object.
- A batch MUST be a valid JSON array.
- Timestamps MUST be ISO 8601 strings in UTC with either a trailing `Z`
  or an explicit `+00:00` offset (e.g. `2026-04-17T12:34:56Z`). The
  `-00:00` offset is *not* accepted: RFC 3339 assigns it the distinct
  meaning "unknown local offset", which is incompatible with the
  UTC-only contract of DRP timestamps.
- String fields MUST be UTF-8.

## 4. Record model

A record has the following fields.

### 4.1 Required fields

| Field       | Type            | Description |
|-------------|-----------------|-------------|
| `record_id` | string          | Stable identifier, unique within a batch. Non-empty after trimming. |
| `timestamp` | string          | ISO 8601 UTC, see §3. |
| `context`   | string          | Why the decision is being made. Non-empty after trimming. |
| `decision`  | string          | What was decided. Non-empty after trimming. |
| `options`   | array\<string\> | Options that were considered. Non-empty; each element a non-empty trimmed string. |
| `status`    | string          | One of `draft`, `proposed`, `complete`, `superseded`, `rejected`. See §6. |

### 4.2 Optional fields

| Field                  | Type                      | Description |
|------------------------|---------------------------|-------------|
| `rationale`            | string                    | Free-text explanation. |
| `impact`               | integer \| null           | Exactly one of `-1`, `0`, `1`, or `null`. See §4.4. |
| `parent_record_ids`    | array\<string\>           | IDs of records that motivated this one. See §7. |
| `child_record_ids`     | array\<string\>           | IDs of records motivated by this one. See §7. |
| `supersedes_record_id` | string                    | Record this one replaces. Required iff `status == "superseded"`. See §8. |
| `tags`                 | array\<string\>           | Free-form labels. Each a non-empty trimmed string. |
| `metadata`             | object                    | Free-form additional metadata. |

### 4.3 Unknown fields

Validators MUST reject unknown top-level fields. This is enforced by
`additionalProperties: false` in the schema and by the validator.
Implementation-specific extensions MUST be nested inside `metadata`.

### 4.4 `impact`

`impact` is intentionally constrained to a small ordinal set:

- `-1` — the decision is expected to have a negative effect on the
  measured dimension;
- `0`  — no significant effect;
- `1`  — positive effect;
- `null` — impact is unknown or not yet assessed.

Booleans (`true` / `false`) MUST NOT be accepted. Any other value MUST be
rejected. The rationale for keeping this set small is discussed in
[DESIGN.md](DESIGN.md).

## 5. Field-level invariants

The following MUST hold for every record:

1. `record_id` is a non-empty string after trimming whitespace.
2. `timestamp` parses as ISO 8601 UTC.
3. `context` is a non-empty string after trimming whitespace.
4. `decision` is a non-empty string after trimming whitespace.
5. `options` is an array of length ≥ 1; every element is a non-empty
   trimmed string.
6. `status` is one of the allowed values in §6.
7. `impact`, if present, is exactly one of `-1`, `0`, `1`, `null`.
8. `parent_record_ids`, if present, is an array of strings.
9. `child_record_ids`, if present, is an array of strings.
10. `tags`, if present, is an array of non-empty trimmed strings.

## 6. Status model

`status` takes one of five values. The state machine is not enforced by
the protocol beyond the constraints below; DRP records what a system
asserts, it does not dictate workflow.

| Value         | Meaning |
|---------------|---------|
| `draft`       | The record is being composed. Not yet proposed. |
| `proposed`    | The decision has been proposed but not committed. |
| `complete`    | The decision is committed. This is the terminal "active" state. |
| `superseded`  | The record supersedes an earlier decision. It is **active** and replaces the decision named by `supersedes_record_id`. See §8. |
| `rejected`    | The decision was considered and explicitly declined. |

`complete` and `superseded` are distinct states. `complete` means an
active decision that does not replace anything. `superseded` means an
active decision that **replaces an earlier record**, identified by
`supersedes_record_id`. Consumers that want to know whether an older
record has been replaced can scan the batch for any record whose
`supersedes_record_id` equals that older record's `record_id`.

## 7. Causal links

`parent_record_ids` express that a decision was motivated by one or more
prior decisions. `child_record_ids` are the inverse.

For a batch, the following MUST hold:

- **G1. Parent resolution.** Every ID in `parent_record_ids` MUST refer
  to a record present in the batch.
- **G2. Child resolution.** Every ID in `child_record_ids` MUST refer to
  a record present in the batch.
- **G3. Bidirectional consistency.** If record `A` lists `B` in
  `parent_record_ids`, then record `B` MUST list `A` in
  `child_record_ids`, and vice versa.
- **G4. Timestamp ordering.** If `A` is a parent of `C`, then
  `A.timestamp` MUST be ≤ `C.timestamp`. Equal timestamps are permitted
  on a parent/child edge (e.g. two decisions recorded in the same
  second), but any resulting cycle is still a G6 violation — see below.
- **G5. No self-reference.** A record MUST NOT appear in its own
  `parent_record_ids` or `child_record_ids`.
- **G7. Unique edges.** Within a single record, `parent_record_ids` and
  `child_record_ids` MUST NOT contain duplicate entries. The schema
  enforces this with `uniqueItems: true`; the reference validator
  repeats the check so it holds even when the schema is not run
  through an external engine.
- **G6. Acyclicity.** The parent/child relation MUST be a directed
  acyclic graph. If all timestamps on an edge path are strictly ordered,
  G4 already rules out cycles; G6 is stated explicitly so that cycles
  formed by records sharing a timestamp are also rejected. The reference
  validator runs a dedicated cycle detector (iterative DFS) regardless
  of timestamp values.

A record MAY have multiple parents and multiple children.

## 8. Supersession

Supersession is the relation "record A supersedes record B", meaning A
replaces B. The *superseding* record is the newer one; the
*superseded* record is the older one it replaces. The field
`supersedes_record_id` lives on the **superseding** record and names
the superseded record.

Rules:

- **S1.** If `status == "superseded"`, `supersedes_record_id` MUST be
  present and non-empty. (A `superseded` record is, by definition, a
  superseding record — see §6.)
- **S2.** `supersedes_record_id`, when present, MUST resolve to a
  record in the batch.
- **S3.** A record MUST NOT supersede itself.
- **S4.** The superseding record's timestamp MUST be ≥ the superseded
  record's timestamp.
- **S5.** `supersedes_record_id` is distinct from `parent_record_ids`.
  Supersession is a replacement relation; parent/child is a causal
  relation. A record MAY express both, but each must be stated
  explicitly.
- **S6.** A `supersedes_record_id` MAY be present on a record whose
  `status` is not `superseded` (for example, a `draft` that already
  names its target), but when `status == "superseded"` the pointer is
  required.
- **S7.** DRP does not forbid two records from naming the same
  `supersedes_record_id`. This situation ("two candidate successors of
  the same ancestor") is structurally valid and can arise from
  concurrent edits or branching histories. Resolving which successor is
  currently active is the responsibility of downstream tooling
  (storage, policy engines, UIs), not of the protocol or the reference
  validator. The canonical discussion is in
  [USE_CASE_POLICY_SUPERSESSION.md](USE_CASE_POLICY_SUPERSESSION.md).

Note that `superseded` is a *real semantic state*, not a loose synonym
for `complete`. A validator MUST enforce S1–S6 before accepting a
superseded record.

## 9. Examples

### 9.1 Minimal valid record

```json
{
  "record_id": "dec-001",
  "timestamp": "2026-04-17T10:00:00Z",
  "context": "We need a decision format.",
  "decision": "Adopt DRP 0.1.",
  "options": ["Adopt DRP", "Use free-form notes"],
  "status": "complete"
}
```

### 9.2 Invalid: empty options

```json
{
  "record_id": "dec-002",
  "timestamp": "2026-04-17T10:00:00Z",
  "context": "x",
  "decision": "y",
  "options": [],
  "status": "complete"
}
```

Violates §5.5 (`options` must be non-empty).

### 9.3 Invalid: impact is a boolean

```json
{
  "record_id": "dec-003",
  "timestamp": "2026-04-17T10:00:00Z",
  "context": "x",
  "decision": "y",
  "options": ["a"],
  "status": "complete",
  "impact": true
}
```

Violates §4.4 and §5.7.

### 9.4 Invalid: superseded without `supersedes_record_id`

```json
{
  "record_id": "dec-004",
  "timestamp": "2026-04-17T10:00:00Z",
  "context": "x",
  "decision": "y",
  "options": ["a"],
  "status": "superseded"
}
```

Violates §8 S1.

See `examples/` and `fixtures/` for more.

## 10. Versioning

The protocol is versioned with Semantic Versioning. The file
[VERSION](../VERSION) holds the current version.

- **Major** — a change that can cause previously valid records to be
  rejected, or previously invalid records to be accepted.
- **Minor** — backward-compatible additions (new optional fields, new
  enum members, relaxed invariants).
- **Patch** — editorial and bug-fix changes to the spec, schema, or
  reference validator that do not alter behavior.

Records SHOULD NOT embed a protocol version. The batch — and the tool
that produced it — is the version-carrying artifact.

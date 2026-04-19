# DRP FAQ

Short, practical answers. For the normative behavior, see
[SPEC.md](SPEC.md).

## What is the difference between `complete` and `superseded`?

Both are active states. `complete` means the decision stands on its
own. `superseded` means the record replaces an earlier decision, named
by `supersedes_record_id`. The older, replaced record keeps whatever
status it had (typically `complete`); consumers find out it was
replaced by scanning the batch for any record that supersedes it. See
§8 of the spec.

## When should I use `parent_record_ids`?

Use `parent_record_ids` when a decision was motivated by one or more
earlier decisions. If you are about to write in prose "this follows
from decision X", link X as a parent instead.

Do not use `parent_record_ids` for superseding. That is what
`supersedes_record_id` is for.

## Can a record have multiple parents?

Yes. A record can have any number of parents and any number of
children. The only constraints are graph acyclicity (§7 G6) and
timestamp ordering (§7 G4).

## Can `impact` be `null`?

Yes. `null` is the explicit "not yet assessed" value. It is distinct
from `0`, which means "assessed and the effect is neutral". Omitting
`impact` entirely is also allowed and is equivalent to `null`.

## Can `impact` be `true` or `false`?

No. Booleans are rejected at both the schema and semantic layer.
See [DESIGN.md](DESIGN.md) for why.

## Can old records be edited?

No. Records are append-only. If a decision needs revision, emit a new
record with `status: "superseded"` and `supersedes_record_id` pointing
at the old record it replaces. See §8 of the spec.

## What if I made a typo in an old record?

Two options:

1. If the typo does not change the meaning of the record and the record
   has not been published, you are free to fix it before publishing.
2. If the record has been published, emit a corrected record that
   supersedes the old one and explain the correction in `rationale`.

DRP does not define a separate "corrigendum" concept — supersession is
the single revision mechanism.

## What makes a batch invalid?

A batch is invalid if any of the following is true:

- any record fails schema validation;
- any record fails semantic validation
  (empty strings, bad timestamps, booleans as impact, etc.);
- two records share a `record_id`;
- a `parent_record_ids`, `child_record_ids`, or `supersedes_record_id`
  reference does not resolve within the batch;
- parent/child references disagree (A lists B as parent but B does not
  list A as child, or vice versa);
- a parent's timestamp is later than its child's timestamp;
- a record marked `superseded` has no `supersedes_record_id`.

See [VALIDATION.md](VALIDATION.md) for the full list.

## Can I validate a single record?

Yes. The validator accepts both a single record and a batch. Graph
invariants that require other records (parent resolution, etc.) are
vacuous for a single-record input, but schema and semantic checks
still apply.

## Can I add custom fields?

Not at the top level. Unknown top-level fields are rejected. Put
extensions inside `metadata`, which is a free-form object.

## Does DRP define a workflow?

No. DRP defines a data format and invariants, not a process. Whether
your workflow goes `draft → proposed → complete` or skips straight to
`complete` is up to you. The spec only constrains:

- the set of allowed `status` values (§6);
- the supersession rules (§8).

## How do I integrate DRP into my system?

1. Emit DRP records as JSON. Stable `record_id`s are your
   responsibility — UUIDs work, so do domain-specific identifiers.
2. Store or transport them however you want.
3. Run `scripts/drp-validate` (or the library equivalent) in CI, on
   ingestion, or before publication.

DRP is a format, not a service.

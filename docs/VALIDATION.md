# DRP Validation

This document describes what the reference validator checks, in what
order, and what the CLI contract is. Spec section references (§) point
into [SPEC.md](SPEC.md).

## 1. Layers

Validation is organized in three layers. Each layer runs only if the
previous one succeeded.

### 1.1 Schema validation

Checks the machine-readable shape of each record against
`schema/drp.schema.json`:

- presence of required fields (§4.1);
- types of all fields;
- enumeration membership for `status`;
- enumeration membership for `impact`
  (covers the `-1 / 0 / 1 / null` constraint, §4.4);
- rejection of unknown top-level fields (§4.3).

Schema validation is necessary but **not sufficient**: it cannot express
uniqueness, cross-record references, or timestamp ordering.

### 1.2 Semantic validation

Per-record checks that JSON Schema cannot express cleanly:

- `record_id`, `context`, `decision` are non-empty after trimming
  (§5.1, §5.3, §5.4);
- `options` is a non-empty array of non-empty trimmed strings (§5.5);
- `timestamp` parses as ISO 8601 UTC (§3, §5.2);
- `tags`, if present, are non-empty trimmed strings;
- `impact` rejects booleans explicitly (booleans are not integers in
  Python, but JSON readers that coerce `True`/`False` to `1`/`0` would
  otherwise slip through — see §4.4);
- `status == "superseded"` implies `supersedes_record_id` is present
  and non-empty (§8 S1);
- a record does not supersede itself (§8 S3).

### 1.3 Graph validation

Cross-record checks that require the full batch:

- `record_id` is unique across the batch (§4.1);
- every `parent_record_ids` entry resolves to a record in the batch
  (§7 G1);
- every `child_record_ids` entry resolves to a record in the batch
  (§7 G2);
- parent and child references are bidirectionally consistent
  (§7 G3);
- for every parent edge, parent timestamp ≤ child timestamp (§7 G4);
- no record appears in its own parent/child list (§7 G5);
- the parent/child graph is acyclic (§7 G6); this check runs after all
  reference resolution is confirmed, using iterative DFS — it catches
  cycles that G4 misses when two or more nodes share the same timestamp;
- `supersedes_record_id`, if present, resolves to a record in the batch
  (§8 S2);
- the superseding record's timestamp is ≥ the superseded record's
  timestamp (§8 S4).

## 2. Error reporting

Each validation error is reported with:

1. the layer (`schema`, `semantic`, or `graph`);
2. the offending `record_id` when identifiable;
3. the field or edge involved;
4. a human-readable message.

The validator does **not** stop at the first error within a layer —
it collects all errors in that layer and then stops if any were found.
This means a single run can surface every schema problem at once, then
every semantic problem at once, then every graph problem at once.

## 3. Input modes

The CLI and library both accept:

- a JSON object (a single record);
- a JSON array (a batch of records).

A single record is validated as a batch of size 1. Graph-level
invariants that reference other records are therefore vacuous for
single-record inputs.

## 4. CLI contract

The reference CLI is `scripts/drp-validate`.

### Usage

```sh
drp-validate <path-to-json> [--json]
```

### Exit codes

Exit codes are exposed as constants in `tools/drp_validator.py`
(`EXIT_OK`, `EXIT_INVALID`, `EXIT_USAGE`). They are stable across
releases.

| Constant       | Code | Meaning |
|----------------|------|---------|
| `EXIT_OK`      | `0`  | Input is valid under all three layers. |
| `EXIT_INVALID` | `1`  | Validation failed. One or more errors were printed. |
| `EXIT_USAGE`   | `2`  | Input could not be read or parsed as JSON, or usage is wrong. |

### Plain-text output (default)

On success, the CLI prints a single line:

```
OK: <N> record(s) validated
```

On failure, it prints one line per error, grouped by layer:

```
[schema]  dec-003: 'impact' must be one of -1, 0, 1, null
[semantic] dec-004: 'options' must be a non-empty array
[graph]   dec-010: parent reference 'dec-999' does not resolve
FAIL: <K> error(s)
```

No other output is written to stdout. Diagnostic messages (if any) go
to stderr.

### JSON output (`--json`)

For CI jobs, editors, and other tools, pass `--json` to receive a
single JSON document on stdout.

On success:

```json
{"status": "OK", "record_count": 1, "errors": []}
```

On validation failure:

```json
{
  "status": "FAIL",
  "record_count": 2,
  "errors": [
    {"layer": "graph", "record_id": "dup-1", "field": "record_id",
     "message": "duplicate record_id 'dup-1' within batch"}
  ]
}
```

On I/O or parse errors:

```json
{"status": "ERROR", "message": "file not found: path/to/file.json"}
```

The `errors` array preserves the order in which errors were discovered
(see §5). The exit code is unchanged by `--json`: `0` / `1` / `2` have
the same meaning as in plain-text mode.

## 5. Determinism

- Validator output for a given input is stable: errors are emitted in
  record order, then in the order in which they were discovered within
  a record.
- The validator does not perform network access.
- The validator does not modify its input.

## 6. What the validator does NOT do

- It does not assess the quality of a decision.
- It does not enforce a workflow on `status` transitions beyond the
  constraints in §6 and §8.
- It does not canonicalize timestamps or record IDs.
- It does not deduplicate records.

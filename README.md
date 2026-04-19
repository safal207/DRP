# Decision Record Protocol (DRP)

DRP is a lightweight, machine-readable protocol for recording decisions as
immutable, linkable records. A DRP record captures *what* was decided,
*why*, *what was considered*, and *how* it relates to earlier or later
decisions. Records form a directed acyclic graph via explicit causal links
and an explicit supersession relation.

This repository is the **canonical specification and reference tooling** for
DRP. It is intentionally not an application; it defines the data format,
the invariants, and the validator that any DRP-compatible system should
honor.

## Why DRP

Most decision logs degrade into free-form prose that cannot be audited,
queried, or diffed. DRP fixes this by:

- treating each decision as a structured record with a stable `record_id`;
- forbidding silent mutation; corrections are expressed as *supersession*;
- making causality explicit through `parent_record_ids`;
- shipping a schema **and** a validator, because schema alone cannot express
  graph-level invariants (bidirectional links, timestamp ordering,
  supersession resolution, etc.).

## Status

| Item       | Value              |
|------------|--------------------|
| Version    | `0.1.0` (see [VERSION](VERSION)) |
| Stability  | Draft -- breaking changes possible before `1.0.0` |
| License    | MIT ([LICENSE](LICENSE)) |

## Repository layout

```
.
+-- README.md                  - this file
+-- LICENSE                    - MIT
+-- VERSION                    - current protocol version
+-- CHANGELOG.md               - version history
+-- CONTRIBUTING.md            - how to propose changes
+-- docs/
|   +-- SPEC.md                - formal specification
|   +-- VALIDATION.md          - validator rules and CLI contract
|   +-- DESIGN.md              - rationale behind design choices
|   +-- FAQ.md                 - common questions
|   +-- USE_CASE_SAFETY_EVAL.md      - go/no-go decisions around safety evaluations
|   +-- USE_CASE_INCIDENT_ROLLBACK.md - incident response and rollback chain
|   +-- USE_CASE_POLICY_SUPERSESSION.md - policy evolution and governance change
|   +-- BENCHMARKS.md          - auditability benchmark pack overview
|   \-- RESEARCH_NOTE.md       - research framing and evaluation seed
+-- schema/
|   \-- drp.schema.json        - JSON Schema (Draft 2020-12)
+-- examples/                  - illustrative, valid records
+-- fixtures/
|   +-- valid/                 - regression fixtures that must validate
|   \-- invalid/               - regression fixtures that must fail
+-- benchmark/
|   \-- drp_auditability_pack/ - scenario-grounded benchmark pack
+-- tools/
|   \-- drp_validator.py       - reference validator implementation
+-- scripts/
|   +-- drp-validate           - CLI wrapper around the validator
|   \-- run_benchmark.py       - runs the auditability pack
\-- tests/                     - automated tests for schema + validator
```

## Quick start

Validate a file using the reference validator:

```sh
python3 tools/drp_validator.py examples/minimal_valid.json
# or
./scripts/drp-validate examples/minimal_valid.json
```

For CI jobs and tool integrations, use `--json` for a machine-readable
result on stdout:

```sh
./scripts/drp-validate examples/minimal_valid.json --json
# {"status": "OK", "record_count": 1, "errors": []}
```

Exit code is `0` on success, `1` on validation failure, `2` on unreadable
input. See [docs/VALIDATION.md](docs/VALIDATION.md) for the full CLI
contract.

Run the test suite:

```sh
python3 -m pytest tests/
```

## Key documents

- [Specification](docs/SPEC.md) - normative definition of the record model.
- [Validation](docs/VALIDATION.md) - what the validator checks and how.
- [Design rationale](docs/DESIGN.md) - why DRP looks the way it does.
- [FAQ](docs/FAQ.md) - practical questions.
- [JSON Schema](schema/drp.schema.json) - machine-readable shape.
- [Examples](examples/) - idiomatic records.
- [Fixtures](fixtures/) - positive and negative validator fixtures.

## Use cases

Realistic scenarios showing where DRP is intended to be applied:

- [Safety evaluation / go-no-go](docs/USE_CASE_SAFETY_EVAL.md) -
  recording deploy / no-deploy / restricted-deploy decisions around a
  safety eval, including later supersession.
- [Incident response / rollback](docs/USE_CASE_INCIDENT_ROLLBACK.md) -
  recording emergency mitigations and subsequent corrective actions as
  a traceable chain.
- [Policy supersession / governance change](docs/USE_CASE_POLICY_SUPERSESSION.md) -
  representing policy evolution so that the currently effective policy
  is always recoverable.

## Benchmarks and research framing

- [Auditability benchmark pack](benchmark/drp_auditability_pack/) -
  compact valid / invalid / ambiguous / comparison fixtures grounded in
  the use cases above.
- [Benchmarks overview](docs/BENCHMARKS.md) - what the pack is, what it
  checks, and what it explicitly does not claim.
- [Research note](docs/RESEARCH_NOTE.md) - problem framing, hypotheses,
  a minimal evaluation outline, and the limits of the current
  repository.

## Conformance

A system is DRP-conformant at version `X.Y.Z` if every record it produces
validates successfully against the schema **and** the reference validator
at that version. Schema-only validation is not sufficient; see
[VALIDATION.md](docs/VALIDATION.md).

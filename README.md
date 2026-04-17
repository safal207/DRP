# DRP — Decision Record Protocol

DRP is a lightweight, machine-readable protocol for recording decisions as
immutable, linkable records. A DRP record captures *what* was decided,
*why*, *what was considered*, and *how* it relates to earlier or later
decisions. Records form a directed acyclic graph via explicit causal links
and an explicit supersession relation.

This repository is the **canonical specification and reference tooling** for
DRP. It is intentionally not an application — it defines the data format,
the invariants, and the validator that any DRP-compatible system should
honor.

## Why DRP

Most decision logs degrade into free-form prose that cannot be audited,
queried, or diffed. DRP fixes this by:

- treating each decision as a structured record with a stable `record_id`;
- forbidding silent mutation — corrections are expressed as *supersession*;
- making causality explicit through `parent_record_ids`;
- shipping a schema **and** a validator, because schema alone cannot express
  graph-level invariants (bidirectional links, timestamp ordering,
  supersession resolution, etc.).

## Status

| Item       | Value              |
|------------|--------------------|
| Version    | `0.1.0` (see [VERSION](VERSION)) |
| Stability  | Draft — breaking changes possible before `1.0.0` |
| License    | MIT ([LICENSE](LICENSE)) |

## Repository layout

```
.
├── README.md                  — this file
├── LICENSE                    — MIT
├── VERSION                    — current protocol version
├── CHANGELOG.md               — version history
├── CONTRIBUTING.md            — how to propose changes
├── docs/
│   ├── SPEC.md                — formal specification
│   ├── VALIDATION.md          — validator rules and CLI contract
│   ├── DESIGN.md              — rationale behind design choices
│   └── FAQ.md                 — common questions
├── schema/
│   └── drp.schema.json        — JSON Schema (Draft 2020-12)
├── examples/                  — illustrative, valid records
├── fixtures/
│   ├── valid/                 — regression fixtures that must validate
│   └── invalid/               — regression fixtures that must fail
├── tools/
│   └── drp_validator.py       — reference validator implementation
├── scripts/
│   └── drp-validate           — CLI wrapper around the validator
└── tests/                     — automated tests for schema + validator
```

## Quick start

Validate a file using the reference validator:

```sh
python3 tools/drp_validator.py examples/minimal_valid.json
# or
./scripts/drp-validate examples/minimal_valid.json
```

Run the test suite:

```sh
python3 -m pytest tests/
```

## Key documents

- [Specification](docs/SPEC.md) — normative definition of the record model.
- [Validation](docs/VALIDATION.md) — what the validator checks and how.
- [Design rationale](docs/DESIGN.md) — why DRP looks the way it does.
- [FAQ](docs/FAQ.md) — practical questions.
- [JSON Schema](schema/drp.schema.json) — machine-readable shape.
- [Examples](examples/) — idiomatic records.
- [Fixtures](fixtures/) — positive and negative validator fixtures.

## Conformance

A system is DRP-conformant at version `X.Y.Z` if every record it produces
validates successfully against the schema **and** the reference validator
at that version. Schema-only validation is not sufficient; see
[VALIDATION.md](docs/VALIDATION.md).

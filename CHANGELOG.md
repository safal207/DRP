# Changelog

All notable changes to the DRP protocol and its reference tooling are
recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Protocol and tooling share a single version number. A change that affects
the record format, the schema, or the set of enforced invariants is a
**protocol change** and is reflected in [VERSION](VERSION).

## [Unreleased]

## [0.1.0] — 2026-04-17

First public release of the DRP protocol repository.

### Added
- Formal specification (`docs/SPEC.md`) defining the record model, field
  semantics, status model, causal links, supersession, and invariants.
- Validation contract (`docs/VALIDATION.md`) distinguishing schema,
  semantic, and graph validation layers and defining CLI exit codes.
- Design rationale (`docs/DESIGN.md`) and FAQ (`docs/FAQ.md`).
- JSON Schema (`schema/drp.schema.json`, Draft 2020-12) covering the
  machine-checkable shape of a DRP record.
- Reference validator (`tools/drp_validator.py`) implementing schema,
  semantic, and graph validation with human-readable errors.
- CLI wrapper (`scripts/drp-validate`) with documented exit codes.
- Example records (`examples/`) illustrating minimal, complete, causal,
  and superseded usage.
- Regression fixtures (`fixtures/valid/`, `fixtures/invalid/`) for every
  invariant the validator enforces.
- Automated tests (`tests/`) for schema, validator, and invariants.
- Contribution guide (`CONTRIBUTING.md`) and PR template.

[Unreleased]: https://github.com/safal207/DRP/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/safal207/DRP/releases/tag/v0.1.0

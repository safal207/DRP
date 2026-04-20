# Changelog

All notable changes to the DRP protocol and its reference tooling are
recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Protocol and tooling share a single version number. A change that affects
the record format, the schema, or the set of enforced invariants is a
**protocol change** and is reflected in [VERSION](VERSION).

## [Unreleased]

### Added
- Use case documents grounding DRP in realistic safety and governance
  workflows: `docs/USE_CASE_SAFETY_EVAL.md`,
  `docs/USE_CASE_INCIDENT_ROLLBACK.md`,
  `docs/USE_CASE_POLICY_SUPERSESSION.md`.
- Auditability benchmark pack (`benchmark/drp_auditability_pack/`) with
  `valid/`, `invalid/`, `ambiguous/`, and `comparison/` categories.
  Fixtures are scenario-grounded (safety eval, incident rollback,
  policy supersession). The `invalid/` category isolates a single
  defect per fixture across G1-G6, S1-S4, schema-level required-field,
  and schema-level enum failures.
- Benchmarks documentation (`docs/BENCHMARKS.md`) explaining what the
  pack covers, what each category means, what it does not claim, and
  how to extend it (naming, category placement, verification).
- Research note (`docs/RESEARCH_NOTE.md`) stating the problem framing,
  hypotheses, a minimal evaluation outline, and explicit limits of the
  v0.1.0 repository.
- Helper `scripts/run_benchmark.py` that walks the pack, invokes the
  reference validator, and prints a per-category pass/fail summary.
  Supports `--json` for machine-readable output and `--verbose` for
  per-file error messages; returns a distinct exit code for usage
  errors (missing or non-directory `--pack`) versus expectation
  mismatches. Wraps the existing validator API; no protocol change.
- Tests for the benchmark runner (`tests/test_benchmark.py`) covering
  smoke, JSON shape, verbose output, bad `--pack` handling, and
  expectation mismatch detection.
- CI step that runs `scripts/run_benchmark.py` over the pack on every
  push and pull request (extends `.github/workflows/ci.yml`).
- README links to the new use cases, benchmark pack, benchmarks doc,
  and research note.

No protocol, schema, or validator behavior changes in this entry.

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

# Changelog

All notable changes to the DRP protocol and its reference tooling are
recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Protocol and tooling share a single version number. A change that affects
the record format, the schema, or the set of enforced invariants is a
**protocol change** and is reflected in [VERSION](VERSION).

## [Unreleased]

### Changed
- Validator: `-00:00` UTC offset is now rejected (RFC 3339 assigns it
  "unknown local offset", which is not UTC). `+00:00` and `Z` remain
  the only accepted forms. The SPEC §3 sentence is updated to state
  this explicitly.
- Validator: `_parse_iso_utc` simplified to a single unambiguous offset
  check.
- CLI: `ERROR` diagnostics (I/O, parse, oversize-input) are now written
  to stderr in both plain-text and `--json` mode, so stdout stays
  reserved for validation output. Exit codes are unchanged.

### Added
- Validator: input-size limits to bound memory and CPU on untrusted
  input — `DRP_MAX_FILE_BYTES` (100 MiB), `DRP_MAX_BATCH_SIZE`
  (100 000 records), `DRP_MAX_STRING_LENGTH` (100 000 chars),
  `DRP_MAX_ARRAY_LENGTH` (10 000 elements). All configurable via
  environment variables.
- Validator: schema-layer check for duplicate entries in
  `parent_record_ids` / `child_record_ids` (G7), mirroring the
  existing `uniqueItems: true` in the JSON Schema so that the
  reference validator does not silently drift from the schema when
  used without an external JSON Schema engine.
- SPEC: G7 (unique edges) and S7 (multiple candidate successors of the
  same ancestor are structurally valid; active-successor resolution is
  downstream tooling's concern). G4/G6 wording clarified for records
  with equal timestamps.
- VALIDATION: documented that schema-only validation is insufficient
  (no `format: date-time` on `timestamp`); documented new input-size
  limits; added §7 "Security notes" covering path handling, size
  limits, and determinism.
- Tests: cycles with equal timestamps, duplicate parent/child entries,
  whitespace-only string fields, `-00:00` / `+02:00` offsets,
  `supersedes_record_id` on non-`superseded` status, two successors of
  the same ancestor, batch/string/array size limits, and CLI stderr
  routing for both error and success paths.
- CI: shell wrapper (`scripts/drp-validate`) is now smoke-tested
  end-to-end; `check-jsonschema` is installed and used to validate
  sample records against `schema/drp.schema.json` with an external
  JSON Schema engine.
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

# Contributing to DRP

Thank you for considering a contribution. DRP is a specification first and
a piece of code second, so changes are evaluated against the spec, not just
the implementation.

## Ground rules

1. **The spec is normative.** `docs/SPEC.md` defines the protocol. Code,
   schema, and tests exist to enforce the spec, not the other way around.
2. **Every behavioral change needs a test.** If the validator starts
   accepting or rejecting something new, a fixture in `fixtures/valid/`
   or `fixtures/invalid/` and a test in `tests/` must cover it.
3. **Keep the tooling dependency-light.** The reference validator must run
   on a stock Python 3 install. Optional extras are fine, required deps
   are not.

## Proposing a protocol change

Open a pull request that includes:

1. A clear problem statement in the PR description.
2. An edit to `docs/SPEC.md` showing the new or changed language.
3. An edit to `schema/drp.schema.json` if the machine-checkable shape
   changes.
4. An edit to `tools/drp_validator.py` if a new invariant is introduced.
5. New fixtures under `fixtures/valid/` and `fixtures/invalid/` that
   exercise the change.
6. New tests under `tests/` that assert the new behavior.
7. A `CHANGELOG.md` entry under `[Unreleased]`.

Small editorial or cosmetic changes to docs do not require a schema or
validator change.

## When the schema must be updated

Update `schema/drp.schema.json` when any of the following changes:

- a field is added, removed, renamed, or moved;
- a field's type or enumeration changes;
- required/optional status of a field changes;
- a pattern, format, or bound on a scalar field changes.

Do **not** try to encode graph-level invariants (bidirectional links,
timestamp ordering between referenced records, supersession resolution,
uniqueness across a batch) in the schema. Those live in the validator.
See `docs/DESIGN.md`.

## When validator tests must be updated

Update `tests/` and `fixtures/` when any of the following changes:

- a new invariant is introduced or an existing one is relaxed;
- an error message is reworded in a way callers may depend on;
- a new CLI flag, input mode, or exit code is added;
- the interpretation of an existing field changes.

Every invariant listed in `docs/SPEC.md §Invariants` must have at least one
positive fixture (valid) and one negative fixture (invalid).

## What counts as a breaking change

A change is **breaking** — and requires a major version bump after `1.0.0`
or a prominent note before then — if it can cause a previously valid
record to be rejected or a previously rejected record to be accepted.
Concretely:

- Adding a new required field.
- Narrowing an existing field's type or enum.
- Making an optional field required or vice versa.
- Introducing a new invariant that rejects previously valid graphs.
- Removing a status value.
- Changing the meaning of `impact`, `status`, or the supersession rules.

Non-breaking changes include:

- Adding optional fields.
- Relaxing an invariant (fewer rejections).
- Clarifying documentation without changing behavior.
- Improving error messages.

## Commit and PR hygiene

- Keep PRs focused. One protocol change per PR is ideal.
- Reference the affected section of `docs/SPEC.md` in the PR description.
- Use the template in `.github/pull_request_template.md`.

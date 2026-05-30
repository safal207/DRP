# Contributing to DRP

Thank you for considering a contribution. DRP is a specification first and
a piece of code second, so changes are evaluated against the spec, not just
the implementation.

## Start here

If you are new to DRP, start with small contributions that improve clarity
before changing protocol behavior.

Good first contribution types:

1. **Examples** - add a small valid DRP record for a realistic decision.
2. **Invalid fixtures** - add a focused invalid case that the validator should reject.
3. **FAQ improvements** - clarify a confusing field, status, or rule.
4. **Use-case notes** - explain how DRP applies to a concrete workflow.
5. **CLI docs** - improve copy-paste commands, output examples, or troubleshooting.
6. **Comparison docs** - explain how DRP relates to adjacent practices or tools.

A good first PR should be small, easy to review, and linked to one issue.

## Contributor path

DRP contributions usually fall into four levels:

| Level | Contribution type | Expected files |
|---|---|---|
| 1 | Documentation clarification | `README.md`, `docs/*.md` |
| 2 | New examples or fixtures | `examples/`, `fixtures/` |
| 3 | Validator behavior | `tools/drp_validator.py`, `tests/`, fixtures |
| 4 | Protocol semantics | `docs/SPEC.md`, schema, validator, tests, changelog |

For first-time contributors, Level 1 and Level 2 are the best entry points.
Level 3 and Level 4 should include tests and clear spec references.

## Before opening a PR

Please check:

- the change has a clear purpose;
- the PR is focused on one topic;
- docs are updated when behavior changes;
- tests are updated when validation behavior changes;
- new examples are small and readable;
- invalid fixtures fail for the reason their filename suggests.

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

A change is **breaking** -- and requires a major version bump after `1.0.0`
or a prominent note before then -- if it can cause a previously valid
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

## Good First Issues and Contributor Path

Welcome! If you're new to the project, there are plenty of ways to get involved without needing a deep understanding of the protocol internals.

### Small Contribution Types
We recommend starting with these small contribution types to get familiar with our workflow:
- **Examples**: Add small, self-contained examples of DRP usage to the `examples/` directory.
- **Fixtures**: Create new JSON test fixtures for edge cases under `fixtures/valid/` or `fixtures/invalid/`.
- **Docs**: Fix typos, clarify confusing sections, or expand on concepts in the `docs/` folder.
- **CLI Tests**: Add shell tests or unit tests for the `drp_validator.py` CLI.
- **Comparison Notes**: Document how DRP compares to similar protocols or existing solutions.

### Beginner-Friendly Task Ideas
If you're looking for a specific task to tackle, here are 5 ideas to get started:
1. **Document an edge case**: Find an invariant in `docs/SPEC.md` that is hard to understand and add an explanatory example to the docs.
2. **Add an invalid fixture**: Pick a required field in `schema/drp.schema.json` and create a fixture in `fixtures/invalid/` that omits it.
3. **Enhance a CLI error message**: Modify `tools/drp_validator.py` to print a more descriptive error for a specific validation failure.
4. **Write a quickstart guide**: Create a brief `docs/QUICKSTART.md` showing how to run the validator on a sample file.
5. **Add a CLI test**: Write a basic test in `tests/` that runs the validator via subprocess and checks the exit code.

### What Makes a Good Contribution
A good contribution, especially for your first PR, should be focused and complete. It should include:
- A single, well-defined change (don't mix doc fixes with code changes).
- A clear description of why the change is being made.
- If relevant, the appropriate tests and fixtures (even for docs, ensuring links work is helpful!).
- Adherence to the commit and PR hygiene guidelines listed below.

## Commit and PR hygiene

- Keep PRs focused. One protocol change per PR is ideal.
- Reference the affected section of `docs/SPEC.md` in the PR description.
- Use the template in `.github/pull_request_template.md`.

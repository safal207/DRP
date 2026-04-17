<!--
Thanks for contributing to DRP. Fill in every section. PRs that change
behavior without spec/schema/tests updates will be asked to expand.
-->

## Summary

<!-- One or two sentences. What changes and why. -->

## Spec impact

- [ ] No change to `docs/SPEC.md`.
- [ ] Editorial change to `docs/SPEC.md` (no behavioral change).
- [ ] **Normative** change to `docs/SPEC.md`. Affected section(s):
      <!-- e.g. S4.2, S7 G3 -->

If this is a normative change, describe:
- What invariant or field is added/removed/changed.
- Whether previously valid records may now be rejected (or vice versa).
- Corresponding `CHANGELOG.md` entry.

## Validation / testing

- [ ] Schema (`schema/drp.schema.json`) updated if the machine-checkable
      shape changed.
- [ ] Validator (`tools/drp_validator.py`) updated if a new invariant
      was introduced.
- [ ] Positive fixture(s) added under `fixtures/valid/`.
- [ ] Negative fixture(s) added under `fixtures/invalid/`.
- [ ] Tests added or updated under `tests/`.
- [ ] `python3 -m pytest tests/` passes locally.

## Breaking change?

- [ ] No - strictly additive or editorial.
- [ ] Yes - explain below why it is necessary and how consumers migrate.

## Checklist

- [ ] Branch is up to date with `main`.
- [ ] `CHANGELOG.md` updated under `[Unreleased]`.
- [ ] `VERSION` updated if this PR cuts a release.
- [ ] No new runtime dependencies added to the reference validator.

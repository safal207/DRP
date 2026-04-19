## Summary

One or two sentences. What changes and why.

## Spec impact

- [ ] No change to `docs/SPEC.md`.
- [ ] Editorial change to `docs/SPEC.md` (no behavioral change).
- [ ] Normative change to `docs/SPEC.md`. List affected sections below.

If this is a normative change, describe:

- What invariant or field is added, removed, or changed.
- Whether previously valid records may now be rejected, or vice versa.
- The corresponding `CHANGELOG.md` entry.

## Validation and testing

- [ ] `schema/drp.schema.json` updated if the machine-checkable shape changed.
- [ ] `tools/drp_validator.py` updated if a new invariant was introduced.
- [ ] Positive fixture(s) added under `fixtures/valid/`.
- [ ] Negative fixture(s) added under `fixtures/invalid/`.
- [ ] Tests added or updated under `tests/`.
- [ ] `python3 -m pytest tests/` passes locally.

## Breaking change?

- [ ] No. Strictly additive or editorial.
- [ ] Yes. Explain why it is necessary and how consumers migrate.

## Checklist

- [ ] Branch is up to date with `main`.
- [ ] `CHANGELOG.md` updated under `[Unreleased]`.
- [ ] `VERSION` updated if this PR cuts a release.
- [ ] No new runtime dependencies added to the reference validator.

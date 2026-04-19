# Incident 2026-04-14 -- capability-y regression

**Owner:** on-call / platform safety
**Status:** closed

## Timeline

- 2026-04-14 09:05 UTC: external report plus internal monitoring flagged
  that capability-y v2 was producing responses in a restricted advice
  domain. Reproducible on maybe 0.3% of matched queries. P1.
- 2026-04-14 10:20 UTC: we decided to roll back to v1 globally. Other
  options were on the table (narrow the audience, add a guard rule) but
  rollback was the cleanest thing we could do inside the incident
  window. Flag flipped off for v2.
- 2026-04-16 afternoon UTC: post-incident review. Fix is small and
  covered by a regression test. Signed off by the usual reviewers.
  Re-deployed v2.1 and retained the rollback as the fallback for 72h
  until monitoring confirmed things were clean.

## Notes

- Root cause was a mismatch in how a guardrail rule loaded the restricted
  advice category for v2. v1 loaded it correctly.
- Rollback is still the "emergency fallback" if v2.1 regresses.

## Current status

We are on v2.1. The rollback-to-v1 plan is the documented fallback.

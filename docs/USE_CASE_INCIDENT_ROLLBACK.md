# Use Case: Incident Response and Rollback

This document describes using DRP to record and audit the decisions
made during and after an incident, including emergency rollbacks,
mitigations, and later corrective actions. It is illustrative, not
normative; see [SPEC.md](SPEC.md) for the protocol itself.

## 1. Scenario

A capability has been deployed. Sometime after deployment, one of the
following occurs:

- a safety issue is reported (jailbreak, abuse pattern, regression in a
  guardrail);
- a user-visible bug is identified that has policy implications (e.g.
  the system produces advice in a restricted domain it was not meant to
  enter);
- monitoring detects a metric regression that crosses an incident
  threshold.

An on-call team takes a time-critical decision -- for example:

1. roll back the deployment,
2. disable the capability behind a feature flag,
3. narrow the capability to a smaller audience,
4. continue to serve with additional monitoring.

After the immediate incident is handled, a follow-up review produces a
second decision that either:

- confirms the emergency mitigation,
- replaces it with a more targeted fix (patch, policy update,
  retraining), or
- formally closes the incident with no further action.

Both the *emergency* decision and the *corrective* decision matter, and
the relationship between them matters even more. An auditor asking
"what is currently in effect?" needs a definite answer.

## 2. Why ad hoc notes and logs are insufficient

Incident tooling typically produces:

- an incident channel with a running timeline;
- a status page entry;
- a post-incident review document;
- ticket updates on the original deploy ticket.

These artifacts are valuable, but as an authoritative record of
*decisions* they degrade:

- **Ordering is implicit.** The exact sequence
  *deploy -> rollback -> corrective patch* must be reconstructed from
  timestamps scattered across tools.
- **Supersession is implicit.** A later "actually, we did X instead"
  message in the incident channel quietly overrides an earlier "we are
  rolling back" statement. Nothing marks the earlier statement as
  replaced. A reader later cannot tell which is current.
- **Mutation is invisible.** Status pages and tickets are edited in
  place. A reader cannot tell whether the note "fixed at 14:02" was
  added at 14:02 or three days later.
- **No link to the originating decision.** The rollback decision may
  reference the incident, but rarely references the *deploy decision*
  it replaces, which is the semantically correct parent.

During an incident this is often acceptable. In the reconstruction that
comes afterwards -- an internal review, a customer communication, a
regulator question -- the lack of a definite, machine-checkable chain is
a real problem.

## 3. How DRP helps

The incident timeline is a stream of events. The *decisions* inside
that stream are a small subset, and they are exactly what DRP is
designed to represent.

Each decision becomes a DRP record. The relationship between decisions
is expressed through the two relations DRP already supports:

- `parent_record_ids` -- this decision was motivated by that one;
- `supersedes_record_id` -- this decision replaces that one.

The result is a short, dense chain of records that answers three
questions without human narration:

1. What was the original deploy decision?
2. What emergency action was taken, and which earlier decision did it
   replace?
3. What corrective action, if any, replaced the emergency action?

## 4. What records exist in the chain

A representative chain contains:

1. **Original deploy decision**
   - `record_id`: e.g. `deploy-2026-04-01`
   - `context`: what was deployed and under what conditions
   - `decision`: the deploy decision
   - `options`: candidate deployment postures
   - `status`: `complete`

2. **Incident-triggered emergency decision**
   - `record_id`: e.g. `deploy-2026-04-14-rollback`
   - `supersedes_record_id`: `deploy-2026-04-01`
   - `context`: nature of the incident, what threshold was crossed
   - `decision`: rollback / flag-off / narrow-audience
   - `options`: the emergency options that were considered
   - `rationale`: why the team chose this action under time pressure
   - `status`: `superseded`
   - `impact`: `-1` if the deployment is degraded by this choice, with
     the expectation of later recovery

3. **Corrective follow-up decision (optional but typical)**
   - `record_id`: e.g. `deploy-2026-04-16-patched`
   - `supersedes_record_id`: `deploy-2026-04-14-rollback`
   - `context`: results of the post-incident review
   - `decision`: redeploy with fix / retain rollback / replace with
     alternative capability
   - `options`: the durable options that were considered
   - `status`: `superseded` (active; it replaces the rollback)

A corresponding example is in
[`benchmark/drp_auditability_pack/valid/incident_rollback_chain.json`](../benchmark/drp_auditability_pack/valid/incident_rollback_chain.json).

## 5. What auditability means here

For this scenario, "auditable" means:

- **Unambiguous current state.** Given the batch, the currently
  effective deploy posture is the record not superseded by any other.
  This can be computed mechanically.
- **Full rollback lineage.** The chain `deploy -> rollback -> corrective`
  is a direct walk of `supersedes_record_id` pointers. No prose
  reconstruction needed.
- **Evidence linkage.** Each decision can reference its motivating
  evidence through `parent_record_ids` (e.g. an eval or incident
  summary record), so a reviewer can inspect what was known at the
  time.
- **Append-only.** Nobody can silently rewrite the rollback decision
  after the fact. If the team later concludes the rollback was the
  wrong call, they must emit a new record that supersedes it, which
  itself remains in the chain.

The validator enforces the structural correctness of this chain:
timestamp ordering from deploy to rollback to corrective, resolvable
supersession pointers, no self-references, and acyclicity. See
[VALIDATION.md](VALIDATION.md) for the full list.

## 6. Out of scope

DRP does not:

- detect the incident;
- page on-call;
- execute the rollback;
- replace the incident review template, the post-mortem, or the
  customer communication.

It is the *decision-record layer* that sits alongside those tools. The
incident channel, the status page, and the post-mortem document all
remain. What changes is that the *decisions taken during the incident*
have a structured, append-only, machine-checkable representation
separate from the free-form narrative around them.

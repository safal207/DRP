# Use Case: Safety Evaluation and Go / No-Go Decisions

This document describes a realistic workflow where DRP is used to record
and audit the decisions that surround a safety evaluation of a
capability update (for example, a new model version, a new tool, or a
new deployment surface). It is illustrative, not normative; see
[SPEC.md](SPEC.md) for the protocol itself.

## 1. Scenario

A team is preparing to ship a new version of a capability with a
non-trivial safety surface. Concretely:

- an updated model or updated tool-use capability is staged behind a
  feature flag;
- an evaluation suite is run (red-team prompts, misuse probes,
  regression checks, calibration tests, etc.);
- a reviewer or review committee meets and decides one of:
  *deploy*, *do not deploy*, or *deploy with restrictions*;
- that decision may later be revisited -- for example, a new eval result
  upgrades a *restricted deploy* to a *full deploy*, or a newly
  discovered regression forces a rollback.

The decision is safety-critical. Whoever later audits the process -- an
internal safety team, an external reviewer, a regulator, or a
researcher -- needs to reconstruct exactly:

1. what evidence existed at the time of the decision;
2. what options were considered;
3. what was decided, by whom, and when;
4. whether that decision is still in effect, and if not, what replaced
   it.

## 2. Why ad hoc notes and logs are insufficient

In practice, this workflow is often captured as:

- a meeting doc or ticket comment with free-form prose;
- a Slack thread linked from a launch checklist;
- a spreadsheet cell ("approved by X on date Y");
- a CI log that shows evals passed but does not show the *decision*.

These artifacts share a few problems:

- **Unstable identity.** There is no stable identifier for *the
  decision*. The document URL can move, the Slack thread can be
  archived, the spreadsheet row can be overwritten.
- **Silent mutation.** Prose can be edited in place. A reader six months
  later cannot tell whether a line was present at the time of the
  decision or inserted after an incident.
- **No explicit causality.** A later decision ("we are now restricting
  this to internal users") does not mechanically reference the earlier
  go decision it amends. The chain must be reconstructed by humans.
- **No machine-checkability.** A reviewer cannot ask "show me every
  decision that currently supersedes an earlier go decision", or even
  "show me every active deploy decision".

Free-form records are fine for discussion. They are not fine as the
authoritative trail of a safety-critical decision.

## 3. How DRP helps

DRP does not replace the eval suite, the review meeting, or the sign-off
process. It replaces *the artifact that represents the decision itself*.

Each reviewable event in the workflow becomes a DRP record:

| Event                                    | DRP record                                       |
|------------------------------------------|--------------------------------------------------|
| Eval run produced a summarized result    | `complete` record, `context` = what was tested   |
| Review committee reached a go decision   | `complete` record, parents = eval records        |
| Restricted deploy follows a re-review    | `superseded` record pointing at earlier go record |
| Rollback after incident                  | `superseded` record pointing at active deploy    |
| Later corrective action                  | `superseded` record pointing at rollback         |

Because records are append-only and supersession is a first-class
relation, the chain is the audit trail. No separate "who edited what,
when" log is required.

## 4. What records exist in the chain

A representative chain for this use case contains at least:

1. **Evaluation summary record(s)**
   - `record_id`: e.g. `eval-2026-04-12-capability-x`
   - `context`: what capability was evaluated, against what eval set
   - `decision`: the summary finding (e.g. "passes safety eval at
     threshold T with 2 open regressions")
   - `options`: the candidate conclusions that were considered
   - `status`: `complete`
   - `metadata`: links to raw eval artifacts

2. **Go / no-go / restricted decision record**
   - `record_id`: e.g. `deploy-decision-2026-04-13`
   - `parent_record_ids`: the eval summary record(s)
   - `context`: what is being decided (deploy / restrict / block)
   - `decision`: the explicit outcome
   - `options`: `["deploy", "restricted deploy", "do not deploy"]`
   - `rationale`: the reviewer's stated reasoning
   - `status`: `complete`
   - `impact`: `-1 | 0 | 1 | null` to flag expected direction

3. **Later revision, if any**
   - `record_id`: e.g. `deploy-decision-2026-05-02`
   - `supersedes_record_id`: the earlier go decision
   - `status`: `superseded`
   - `rationale`: why the earlier decision is being replaced
     (new eval evidence, new incident, new policy)

A corresponding example is in
[`benchmark/drp_auditability_pack/valid/go_no_go_chain.json`](../benchmark/drp_auditability_pack/valid/go_no_go_chain.json).

## 5. What auditability means here

For this scenario, "auditable" has a concrete, machine-checkable
meaning:

- **Reconstructable history.** Given the batch, any reviewer can list
  every decision record in timestamp order and see the exact sequence
  of safety decisions.
- **Stable identity.** Every decision has a `record_id` that other
  records can reference. Nothing depends on a document URL.
- **Explicit supersession.** A later decision that replaces an earlier
  one declares that fact via `supersedes_record_id`. A decision that
  has *not* been replaced is detectable by the absence of a superseding
  record. This is exactly what a reviewer needs to answer "is this
  deploy still authorized?".
- **Explicit causality.** Eval records are linked as parents of the
  decision they informed. A reviewer can walk from the decision up to
  the evidence that justified it without trusting narrative prose.
- **No silent mutation.** A corrected decision is a new record. The
  old record is still there, unchanged, with a successor that names it.

The reference validator (see [VALIDATION.md](VALIDATION.md)) enforces
the structural properties above. It does not assess the *quality* of
the safety decision -- that is a human judgment -- but it does guarantee
the chain of decisions is well-formed.

## 6. Out of scope

DRP does not:

- run the safety eval;
- decide whether the evidence is sufficient;
- authenticate reviewers (authentication belongs at the layer that
  produces records -- a producer signs a batch; DRP validates its
  shape);
- store the raw eval artifacts. Raw artifacts live wherever the team
  already stores them; the DRP record references them via `metadata`.

This separation is deliberate. DRP is the *record layer* for
safety-critical decisions, not the evaluation stack.

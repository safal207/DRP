# Use Case: Policy Supersession and Governance Change

This document describes using DRP to record and audit the evolution of
a policy or rule over time: the original rule, one or more replacements,
and any later revocation. It is illustrative, not normative; see
[SPEC.md](SPEC.md) for the protocol itself.

## 1. Scenario

A team maintains a set of policies or rules that govern system
behavior. Examples include:

- allowed and disallowed tool-use patterns for an agent;
- content categories the system refuses to produce;
- which external services a capability is allowed to call;
- thresholds at which a capability escalates to a human reviewer.

Over time, these policies change:

- a new policy replaces an older one;
- an incident prompts a tightening of an existing rule;
- a broader governance change (company, customer, or regulatory)
  requires rewording or re-scoping a rule;
- a policy is retired entirely.

The team needs to answer, at any later point:

1. What is the currently active version of policy P?
2. What was the active version on date D?
3. Why did the policy change from version V1 to V2?
4. Which earlier decisions still reference V1, and have they been
   updated to reference V2?

## 2. Why ad hoc notes and logs are insufficient

A common pattern is to keep policies in a wiki, a Markdown file, or a
policy-management tool. These typically offer:

- a page with the current policy text;
- a version history of the page;
- free-form changelog entries.

The gaps, from an audit perspective:

- **"Current" is an implicit property.** The wiki page shows the latest
  text, but there is no structured record that says "this version
  replaces version V1 as of date D". The replacement relationship is
  implicit in the page history.
- **Prose changelogs drift.** A bullet in a changelog ("tightened
  wording around tool use") does not commit to *which* previous policy
  statement it replaces. Multiple in-flight edits can collide without
  anyone noticing.
- **Cross-references break.** A decision elsewhere in the system
  ("this capability was approved subject to policy P") freezes P by
  name, not by identity. When P is rewritten, the earlier decision now
  points at a moving target.
- **No machine-checkable active set.** A reviewer cannot ask "give me
  the set of currently active policies" without inspecting the
  document tree by hand.

These are tolerable for low-stakes policies. They are not tolerable when
a policy is the thing that determines whether a safety-critical system
is operating within its authorized envelope.

## 3. How DRP helps

DRP models policy change using the same supersession relation it uses
for decisions. Each policy version is a DRP record. Replacing a policy
is emitting a new record with `status: "superseded"` and
`supersedes_record_id` pointing at the previous version. Retirement is
the same shape, with the replacement record's `decision` stating that
the policy no longer applies.

The key properties that follow from the spec:

- The *active* policy is the record not superseded by any other.
- The *history* of a policy is the chain walked backward through
  `supersedes_record_id`.
- A decision that references a policy can link it as
  `parent_record_ids`, and the graph remains consistent even as the
  policy evolves, because the older policy record still exists and is
  still resolvable.

## 4. What records exist in the chain

A representative chain contains:

1. **Original policy record**
   - `record_id`: e.g. `policy-tooluse-v1`
   - `context`: what the policy covers and why it exists
   - `decision`: the normative statement of the policy
   - `options`: the formulations that were considered
   - `status`: `complete`
   - `tags`: `["policy", "tool-use"]`

2. **First revision**
   - `record_id`: e.g. `policy-tooluse-v2`
   - `supersedes_record_id`: `policy-tooluse-v1`
   - `context`: what triggered the revision (incident, governance
     change, new eval finding)
   - `decision`: the revised normative statement
   - `options`: the candidate revisions that were considered
   - `rationale`: why this revision is being made
   - `status`: `superseded`

3. **Second revision or retirement (optional)**
   - `record_id`: e.g. `policy-tooluse-v3`
   - `supersedes_record_id`: `policy-tooluse-v2`
   - `decision`: the next revised statement, or an explicit retirement
   - `status`: `superseded`

Consumer decisions (for example, a deploy authorization) link to the
policy record by ID through `parent_record_ids`. Those earlier decisions
do not change; they remain valid historical records of what was decided
under which policy version.

A corresponding example is in
[`benchmark/drp_auditability_pack/valid/policy_supersession_chain.json`](../benchmark/drp_auditability_pack/valid/policy_supersession_chain.json).

## 5. What auditability means here

For this scenario, "auditable" means:

- **Current effective policy is computable.** Given the batch, the
  active version of policy P is the record with `record_id` beginning
  `policy-P-*` that no other record supersedes. A simple scan returns
  a definite answer.
- **Historical effective policy is computable.** For any date D, the
  active policy at that time is the latest record whose timestamp is
  <= D and that was not yet superseded at D. This is a well-defined
  query against the batch.
- **Cross-references are stable.** A deploy authorization that linked
  `policy-tooluse-v1` as a parent still resolves cleanly after v2 and
  v3 are emitted. The linked parent is never rewritten; supersession
  only adds new records.
- **Retirement is a first-class event.** A retired policy is not a
  deleted page; it is a superseding record whose decision states
  retirement. The history is preserved.

The validator enforces that:

- every `supersedes_record_id` resolves to a record in the batch;
- the superseding record's timestamp is >= the superseded record's
  timestamp;
- no record supersedes itself;
- the parent/child graph is acyclic.

See [VALIDATION.md](VALIDATION.md) for the complete list of enforced
invariants.

## 6. A note on conflicting successors

Supersession in DRP is a relation, not a protocol-enforced uniqueness
constraint: two records can, in principle, each declare themselves to
supersede the same earlier record. The spec does not forbid this, and
there are legitimate cases (for example, split governance that is
later reconciled). A consumer that requires a single active successor
should detect and resolve this at a higher layer -- for example, by
treating multiple active successors as an alert that needs human
triage. The benchmark pack includes a fixture that illustrates this
structural case so tooling can recognize it.

## 7. Out of scope

DRP does not:

- define what a policy *is*;
- provide a DSL for policy content;
- enforce that decisions comply with the policy they cite;
- provide access control over who may emit a policy record.

DRP records the *decision to adopt, revise, or retire* a policy,
together with a durable chain across those events. The policy content
itself, and the enforcement of that content against runtime behavior,
belong to other layers of the system.

# DRP Research Note

**Status:** working note, v0.1.
**Scope:** a compact research framing for the Decision Record Protocol
(DRP) as early-stage safety and auditability infrastructure.
**Audience:** reviewers, collaborators, and future grant / fellowship
readers who need a short, honest picture of what DRP is, what it is
not, and what empirical work would make it stronger.

This note is not a paper and does not present empirical results. It is
a seed artifact that makes DRP's research framing explicit.

## 1. The problem

Safety-critical decisions in modern software systems -- "deploy or not",
"roll back or not", "adopt this policy or not" -- are routinely recorded
in artifacts that are not designed to be audited. Meeting docs, ticket
threads, wiki pages, and post-incident narratives are good at
*communication* but poor at the structural properties that later audit
and review depend on:

- **Stable identity.** The artifact that represents a decision often
  has no durable, referenceable identifier distinct from a moving URL.
- **Explicit supersession.** When a decision is replaced, the
  relationship is usually stated in prose, not as a structured pointer
  from the replacing record to the replaced one.
- **Append-only history.** Documents are editable in place. A reader
  months later cannot tell whether a sentence was present at the time
  of the decision or inserted afterwards.
- **Machine-checkable chains.** A reviewer typically cannot mechanically
  ask "what decision is currently in effect?" or "which decisions
  reference this now-retired policy?".

These gaps do not cause visible harm every day. They cause visible harm
during incidents, audits, regulator questions, post-hoc reviews, and
any situation where the authoritative question is not "what happened?"
but "what did we *decide* and what replaces it now?".

## 2. Why this matters

The need for auditable decision trails is not new, but it is increasing
in pressure. Three drivers:

1. **Agentic and semi-agentic systems.** Systems that take
   consequential actions on behalf of users or organizations
   accumulate decisions -- about policies, about tool-use authorization,
   about escalation -- that need to be reviewable later. The per-system
   rate of consequential decisions is trending up.
2. **Safety evaluation as a governance layer.** Deploy / no-deploy
   decisions based on safety evaluations are increasingly the interface
   between developers and external reviewers (internal safety teams,
   customers, standards bodies, regulators). That interface is only as
   strong as the records it produces.
3. **Incident response as a regulated surface.** Rollbacks, narrowings,
   and mitigations are things external parties increasingly expect to
   be reconstructable after the fact, with a clear chain from the
   original deploy to the current posture.

In all three cases, the binding question is not "is the decision
correct?" but "is the decision legible?".

## 3. Hypothesis

Structured decision records -- specifically, records with stable
identifiers, explicit causal and supersession links, and an append-only
discipline -- **can improve** the traceability, reviewability, and
reconstructability of decision history over ad hoc prose logs.

This is stated as a hypothesis, not a result. Concretely, we expect:

- H1. A reviewer given a well-formed DRP batch can determine the
  currently effective decision for a given subject (policy, deploy,
  rollback posture) without reading prose, in bounded time.
- H2. A reviewer given a DRP batch can reconstruct the history of a
  decision back to its original motivating record without external
  tools.
- H3. Common structural defects in decision trails (missing parent,
  broken supersession target, cycles, bidirectional inconsistency) can
  be detected mechanically by a validator that does not need to
  understand decision content.
- H4. For matched scenarios, DRP chains produce definite answers to
  common reviewer queries more often than equivalent free-form notes.

Hypothesis H3 is already supported by the reference validator; it is
included for completeness.

## 4. A minimal evaluation framing

A principled evaluation does not yet exist. The benchmark pack at
[`benchmark/drp_auditability_pack/`](../benchmark/drp_auditability_pack/)
is the seed for one, and [BENCHMARKS.md](BENCHMARKS.md) documents its
shape.

A minimal evaluation on top of the pack could take the following
form:

1. **Scenario-level.** For each `valid/` chain and each matching
   `comparison/` pair, enumerate a fixed list of reviewer queries
   ("what is currently active?", "what replaced record X?", "what was
   active on date D?") and check which are answerable from the
   artifact alone.
2. **Defect detection.** For each `invalid/` fixture, confirm the
   defect is caught by the reference validator, and record which layer
   (schema / semantic / graph) caught it.
3. **Audit-hostile cases.** For each `ambiguous/` fixture, record that
   the validator accepts it -- this is the expected behavior -- and
   describe what a higher-level audit linter would have to do to flag
   the case.
4. **Human comparison.** For the `comparison/` pair, run a small,
   structured review by multiple readers: ask the same queries against
   the Markdown note and against the DRP chain, and record which
   answers are definite, which are inferred, and which are unanswerable.

None of these steps produces a research claim on their own. Together
they form the outline of a credible, reproducible study.

## 5. Future empirical work

Any stronger claim about DRP-like structures needs experiments the
current repository does not contain. Concrete candidates:

- **Inter-rater study.** Given the same incident scenario, how much do
  multiple reviewers agree on "what is currently in effect?" when
  reading a free-form note versus a DRP chain? The chain is predicted
  to increase agreement.
- **Time-to-answer.** For fixed queries over matched scenarios, how
  long does a reviewer take to produce a justified answer? We predict
  a shorter time and fewer cross-tool lookups when reviewing a DRP
  batch.
- **Defect catch rate.** Given a corpus of real-world decision logs
  converted to DRP form with a controlled set of injected defects, how
  many defects are caught by the validator versus a human reviewer of
  the original logs?
- **Operational burden.** What is the additional cost to teams of
  emitting DRP records alongside existing incident and review
  artifacts? Low overhead is a necessary condition for adoption.
- **Policy adherence.** Can downstream tooling built on DRP (active
  record selector, retired-reference detector, conflicting-successor
  detector) reliably identify governance drift before a human reviewer
  does?

Each of these is a concrete, fundable piece of work. None is done here.

## 6. Limits of the current repository

This section is deliberate; it is what separates an honest seed
artifact from a marketing page.

- **DRP at v0.1.0 is a format and a validator, not a deployment.** It
  has not been used in production by any external team to the authors'
  knowledge.
- **The benchmark pack is small and hand-authored.** It is an
  illustration, not a corpus.
- **No user study has been conducted.** The hypotheses in section 3 are
  motivated by design, not evidence.
- **Only structural defects are checked.** The validator does not
  assess whether a decision is well-founded, whether its stated
  rationale actually supports the conclusion, or whether the chain
  reflects what happened in reality. It only checks that the chain is
  well-formed.
- **No threat model for adversarial producers.** DRP assumes a
  non-adversarial producer. A producer that emits records in bad faith
  can still produce a validator-clean batch. Signing, attestation, and
  adversarial-input handling are out of scope at v0.1.0.
- **No performance characterization.** Validation is O(n) in records
  and edges, but no empirical numbers are published.

## 7. Positioning

DRP is proposed as *infrastructure*, not as a research contribution on
its own. The contribution it aims to make is:

- a small, stable, machine-checkable record format for safety-relevant
  decisions,
- together with a reference validator that enforces the structural
  properties above,
- and a set of illustrative scenarios that make the intended audit
  workload explicit.

The research question it opens is whether format plus validator plus
scenarios is sufficient lift to change the legibility of decision
trails in practice. That question is open, and answering it is the
work the benchmark pack and this note are intended to seed.

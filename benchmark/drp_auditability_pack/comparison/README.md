# Before / after comparison

This directory contains a single incident expressed two ways:

- [`unstructured_incident_note.md`](unstructured_incident_note.md) --
  a plausible free-form incident note of the kind teams typically
  produce in an incident channel or post-mortem doc.
- [`structured_incident_chain.json`](structured_incident_chain.json) --
  the same incident expressed as a DRP batch.

The scenarios are identical: a capability-y v2 deploy, a P1 safety
incident, an emergency rollback, and a corrective patched redeploy.

## What becomes clearer under DRP

For each of these queries, compare how you would answer it against the
two artifacts.

| Query                                                               | Markdown note                             | DRP chain                                                    |
|---------------------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------|
| What is currently in effect?                                        | Read the "Current status" paragraph.      | Scan for the record that no other record supersedes.         |
| Which decision did the rollback replace?                            | Infer from the timeline prose.            | Follow `supersedes_record_id` on the rollback record.        |
| What options were actually on the table at rollback time?           | Implicit; only the chosen path is clear.  | Read `options` and `rationale` on the rollback record.       |
| What was the state on the evening of 2026-04-15?                    | Cross-reference the timeline timestamps.  | Filter records by timestamp; compute active record at time D.|
| Can anything have changed silently after the fact?                  | Yes; the note is editable in place.       | No; records are append-only and each revision is its own record.|
| How do I machine-check that the chain is well-formed?               | You do not.                               | Run `scripts/drp-validate`.                                  |

The markdown note is not *wrong*. It is simply not a structured record
of decisions -- it is a narrative around them. DRP is the structured
record; the narrative can still live alongside it.

The point of this comparison is not that prose notes should disappear.
It is that when the underlying question is "what was decided, when, and
what replaces it", structured decision records produce definite
answers and prose does not.

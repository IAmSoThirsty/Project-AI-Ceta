# S02 failure handling

## Domain failure

A difficult requirement is dropped to make the plan appear complete.

## Required response

Preserve the exact source, task state, and observations. Identify the smallest blocked or unsafe scope. Stop new effects in that scope, retain already committed work, and distinguish validation failure from an uncertain external outcome. Reconcile actual resource state before retrying. Request the specific missing authority, source, or architecture decision through the assigned owner rather than making an unsupported assumption.

If a produced result contradicts the oracle, keep the failure evidence and revise the implementation or conclusion. Never suppress the adverse case, weaken its assertion, invent a successful log, or relabel unexecuted work as complete. Repair must preserve unrelated owner data and current revocation or deletion decisions.

## Escalation and resume

Transfer exact reproduction steps, affected unit and contract IDs, expected and observed results, safe continuation options, and required decisions. Resume only after the missing prerequisite is resolved and the current source and authority are revalidated.

---
name: failure-injection-and-recovery
description: "Use when constructing or verifying CETA failure injection and recovery. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling."
---

# S17 - Failure Injection And Recovery

## Input and output

Require: State and effect boundaries, controlled test environment, recovery rules, and fault-injection points.

Produce: Reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Inject faults before and after intent, dispatch, effect, commit, and publication.
2. Restart.
3. Inspect actual resources.
4. Revalidate authority.
5. Reconcile unknowns.
6. Verify no blind replay or lost user data.

## Verification

Every fault point yields the documented durable state and preserves already committed effects.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A timeout is assumed to prove no external action occurred.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

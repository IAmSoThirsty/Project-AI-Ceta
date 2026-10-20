---
name: cross-subsystem-integration
description: "Use when constructing or verifying CETA cross subsystem integration. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce incrementally integrated native paths with compatibility, recovery, and owner-workflow evidence."
---

# S21 - Cross Subsystem Integration

## Input and output

Require: Approved contract revisions, mapped local units, dependency graph, source baseline, and migration plan.

Produce: Incrementally integrated native paths with compatibility, recovery, and owner-workflow evidence.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Integrate foundations first.
2. Adapt existing owners rather than duplicate them.
3. Validate producer-consumer pairs.
4. Migrate data safely.
5. Test real action paths.
6. Preserve rollback and exact source mapping.

## Verification

The full workflow uses one canonical authority, state, and evidence path without bypasses.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A second hidden implementation creates conflicting sources of truth.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

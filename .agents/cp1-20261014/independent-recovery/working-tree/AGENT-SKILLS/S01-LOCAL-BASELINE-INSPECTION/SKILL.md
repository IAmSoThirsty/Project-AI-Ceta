---
name: local-baseline-inspection
description: "Use when constructing or verifying CETA local baseline inspection. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a source-hashed inventory, entry-point map, current test catalog, and observed integration decisions."
---

# S01 - Local Baseline Inspection

## Input and output

Require: An owner-selected local CETA root, permitted read scope, and the logical-unit registry.

Produce: A source-hashed inventory, entry-point map, current test catalog, and observed integration decisions.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Resolve the selected root and link boundaries.
2. Inspect language and build metadata.
3. Enumerate canonical data and authority owners.
4. Inspect tests and release paths.
5. Classify reuse, extend, and create decisions from evidence.

## Verification

Every proposed real source path exists in the inspected baseline or has an explicit approved create decision.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A remote or remembered layout conflicts with the actual local files.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

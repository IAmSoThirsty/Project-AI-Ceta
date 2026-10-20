---
name: release-qualification
description: "Use when constructing or verifying CETA release qualification. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce an installed-runtime qualification record and accurate release decision for the exact candidate."
---

# S23 - Release Qualification

## Input and output

Require: Exact candidate artifacts, source and dependency manifests, mandatory gates, target environments, and update or rollback rules.

Produce: An installed-runtime qualification record and accurate release decision for the exact candidate.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Validate manifests.
2. Install on clean targets.
3. Run complete local workflows.
4. Test interruption, update, and rollback.
5. Verify data preservation and source-to-binary binding.
6. Block unmet critical gates.

## Verification

The distributed bytes are the same bytes exercised by current installed-product tests.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A development-tree test run qualifies a different packaged build.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

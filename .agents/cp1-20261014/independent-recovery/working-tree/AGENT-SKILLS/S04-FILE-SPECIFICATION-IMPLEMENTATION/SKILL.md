---
name: file-specification-implementation
description: "Use when constructing or verifying CETA file specification implementation. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a focused local implementation change with tests, documentation, and source-bound evidence."
---

# S04 - File Specification Implementation

## Input and output

Require: One approved file-level specification, mapped local path, dependencies, write lease, and acceptance IDs.

Produce: A focused local implementation change with tests, documentation, and source-bound evidence.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Read the unit and component contracts.
2. Inspect the existing target.
3. Choose reuse or extension first.
4. Implement complete behavior and failure paths.
5. Run unit and integration checks.
6. Hand off exact artifacts for independent review.

## Verification

The resulting file satisfies its positive, negative, recovery, and contract obligations without unrelated edits.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A stub or superficial wrapper is presented as end-to-end implementation.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

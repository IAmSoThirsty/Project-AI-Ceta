---
name: independent-reproduction
description: "Use when constructing or verifying CETA independent reproduction. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a separately produced verification report with reproduced results and explicit discrepancies."
---

# S24 - Independent Reproduction

## Input and output

Require: Producer deliverables, exact source and environment references, acceptance criteria, and raw evidence.

Produce: A separately produced verification report with reproduced results and explicit discrepancies.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Inspect actual bytes.
2. Reconstruct prerequisites.
3. Rerun critical checks independently.
4. Compare expected and observed outcomes.
5. Retain failed reproduction details.
6. Avoid editing the artifact under review without a new revision.

## Verification

A distinct verifier reproduces the required outcome from the supplied artifacts and evidence.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: The verifier approves by trusting the producer narrative or their own earlier implementation.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

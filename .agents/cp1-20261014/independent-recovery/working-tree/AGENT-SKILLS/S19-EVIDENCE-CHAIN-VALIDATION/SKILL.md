---
name: evidence-chain-validation
description: "Use when constructing or verifying CETA evidence chain validation. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps."
---

# S19 - Evidence Chain Validation

## Input and output

Require: Operation records, artifacts, signatures, lineage, required evidence profile, and trust context.

Produce: A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Resolve every reference.
2. Hash actual bytes.
3. Verify signatures and trust.
4. Check causal order and source revision.
5. Inspect observation coverage.
6. Detect stale tests and truncation limits.
7. Report unsupported claims.

## Verification

Every accepted claim is tied to current admissible evidence and every gap remains visible.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A valid signature is mistaken for proof of successful behavior or factual truth.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

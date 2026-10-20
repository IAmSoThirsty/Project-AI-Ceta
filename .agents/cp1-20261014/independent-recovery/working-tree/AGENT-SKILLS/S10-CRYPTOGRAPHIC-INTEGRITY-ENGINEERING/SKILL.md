---
name: cryptographic-integrity-engineering
description: "Use when constructing or verifying CETA cryptographic integrity engineering. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce domain-bound digests and signatures with protected keys, rotation, and precise verification outcomes."
---

# S10 - Cryptographic Integrity Engineering

## Input and output

Require: Approved trust model, established local cryptographic facilities, canonicalization rules, and key lifecycle policy.

Produce: Domain-bound digests and signatures with protected keys, rotation, and precise verification outcomes.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Pin algorithms and encoding profiles through local reconciliation.
2. Hash exact bytes.
3. Bind signature domain and version.
4. Use protected handles.
5. Verify trust separately from mathematics.
6. Test rotation, tampering, replay, and truncation assumptions.

## Verification

A modified payload or wrong-domain signature fails while valid historical evidence remains inspectable.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A home-grown primitive or unsigned local file is described as absolute tamper-proof authority.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

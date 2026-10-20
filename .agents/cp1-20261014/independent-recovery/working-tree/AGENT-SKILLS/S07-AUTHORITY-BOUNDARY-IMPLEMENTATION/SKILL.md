---
name: authority-boundary-implementation
description: "Use when constructing or verifying CETA authority boundary implementation. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce use-time authorization checks with bounded delegation, replay protection, and revocation evidence."
---

# S07 - Authority Boundary Implementation

## Input and output

Require: Principal and capability contracts, trust policy, target resource model, and scoped effect requirements.

Produce: Use-time authorization checks with bounded delegation, replay protection, and revocation evidence.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Bind actor, audience, proposal, inputs, target, expiry, and ancestry.
2. Validate current revocation.
3. Atomically consume single-use grants.
4. Recheck target identity at effect time.
5. Test concurrent and restored states.

## Verification

A stale or revoked capability cannot authorize effects through any supported entry path.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A signature-valid token bypasses current revocation or target changes.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

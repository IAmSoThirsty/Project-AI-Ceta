---
name: contract-first-design
description: "Use when constructing or verifying CETA contract first design. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures."
---

# S03 - Contract First Design

## Input and output

Require: Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints.

Produce: A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Define exact records and type constraints.
2. Assign mutation ownership.
3. Specify success, failure, partial, and uncertain outcomes.
4. Define compatibility and versioning.
5. Obtain affected-owner review before implementation.

## Verification

Producer and consumer conformance fixtures exercise identical semantics, including denial and uncertainty.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A consumer privately widens a security-critical field or assumes unknown states mean success.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

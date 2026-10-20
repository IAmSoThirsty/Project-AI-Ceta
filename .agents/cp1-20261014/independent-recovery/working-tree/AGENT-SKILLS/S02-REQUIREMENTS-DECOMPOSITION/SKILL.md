---
name: requirements-decomposition
description: "Use when constructing or verifying CETA requirements decomposition. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a requirement-to-unit map with measurable outputs, dependency edges, and acceptance oracles."
---

# S02 - Requirements Decomposition

## Input and output

Require: Approved product goals, exact user requirements, constraints, and existing acceptance obligations.

Produce: A requirement-to-unit map with measurable outputs, dependency edges, and acceptance oracles.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Preserve exact requirements.
2. Split compound goals into testable behaviors.
3. Identify authority and data consequences.
4. Assign one owner.
5. Define completion evidence.
6. Retain ambiguities as explicit decisions.

## Verification

No approved requirement is orphaned, silently narrowed, or replaced by a vague completion label.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A difficult requirement is dropped to make the plan appear complete.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

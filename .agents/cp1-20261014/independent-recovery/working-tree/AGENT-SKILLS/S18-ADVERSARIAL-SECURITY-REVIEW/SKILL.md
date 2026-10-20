---
name: adversarial-security-review
description: "Use when constructing or verifying CETA adversarial security review. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce reproducible boundary findings with impact, exact evidence, and verified repairs."
---

# S18 - Adversarial Security Review

## Input and output

Require: Explicitly authorized isolated targets, threat boundaries, source changes, and security acceptance cases.

Produce: Reproducible boundary findings with impact, exact evidence, and verified repairs.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Trace untrusted inputs to privileged effects.
2. Test injection, traversal, replay, stale identity, secret leakage, and extension escape.
3. Inspect native enforcement.
4. Reproduce fixes independently.
5. Preserve evidence.

## Verification

Each claimed boundary holds under the specified adversarial fixtures or has an explicit blocking finding.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A review tests production targets without scope approval or substitutes model confidence for observed enforcement.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

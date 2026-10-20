---
name: state-transition-engineering
description: "Use when constructing or verifying CETA state transition engineering. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a validated state machine with atomic transitions, causal records, and terminal-state rules."
---

# S08 - State Transition Engineering

## Input and output

Require: Canonical state owner, transition contract, expected versions, and lifecycle requirements.

Produce: A validated state machine with atomic transitions, causal records, and terminal-state rules.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Enumerate legal states.
2. Define guards and effects.
3. Use expected-version updates.
4. Record transition causes.
5. Define cancellation and uncertainty.
6. Replay committed history to verify consistency.

## Verification

Conflicting updates cannot both commit and terminal states cannot be bypassed.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A restarted worker overwrites a newer stop or revocation state.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

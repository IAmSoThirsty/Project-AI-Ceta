---
name: test-generation-and-execution
description: "Use when constructing or verifying CETA test generation and execution. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states."
---

# S16 - Test Generation And Execution

## Input and output

Require: Requirements, unit specifications, canonical contracts, inspected test tooling, and controlled fixtures.

Produce: Executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Derive positive and negative cases.
2. Reproduce original defects.
3. Isolate fixtures.
4. Run unit and real integration paths.
5. Capture commands, environment, logs, and artifacts.
6. Preserve every failed or omitted obligation.

## Verification

A test fails on the known defect and observes the required corrected behavior.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: Generated tests merely restate the implementation or are reported passed without execution.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

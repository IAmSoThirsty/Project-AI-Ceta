---
name: tool-execution-boundary-engineering
description: "Use when constructing or verifying CETA tool execution boundary engineering. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a governed adapter with exact-input binding, qualified restrictions, stop behavior, and receipts."
---

# S14 - Tool Execution Boundary Engineering

## Input and output

Require: Tool manifest, exact operation proposal, resource identities, isolation capabilities, and effect observation plan.

Produce: A governed adapter with exact-input binding, qualified restrictions, stop behavior, and receipts.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Normalize arguments.
2. Classify transitive effects.
3. Bind target identity.
4. Validate current authority.
5. Install restrictions.
6. Dispatch once per operation identity.
7. Observe real effects.
8. Reconcile partial and unknown outcomes.

## Verification

Denied requests never reach the adapter and observed effects stay within approved scope.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A retry, terminal, maintenance, or IPC path bypasses the gate.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

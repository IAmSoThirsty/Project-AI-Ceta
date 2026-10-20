---
name: agent-workflow-engineering
description: "Use when constructing or verifying CETA agent workflow engineering. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce bounded multi-agent execution with fenced ownership, durable handoffs, and separate review."
---

# S12 - Agent Workflow Engineering

## Input and output

Require: Task graph, agent roles, skill manifests, resource limits, authority scope, and handoff contracts.

Produce: Bounded multi-agent execution with fenced ownership, durable handoffs, and separate review.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Decompose outputs.
2. Pin roles and skills.
3. Acquire write leases.
4. Persist assignments.
5. Validate messages and handoffs.
6. Reconcile worker loss.
7. Require evidence-backed finalization.

## Verification

Duplicate deliveries and stale workers cannot produce conflicting canonical effects.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A producer agent self-certifies its deliverable as independently verified.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

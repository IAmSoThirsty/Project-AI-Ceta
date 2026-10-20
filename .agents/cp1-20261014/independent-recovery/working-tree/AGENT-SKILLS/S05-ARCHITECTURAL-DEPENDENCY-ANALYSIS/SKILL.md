---
name: architectural-dependency-analysis
description: "Use when constructing or verifying CETA architectural dependency analysis. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce typed build, runtime, data, and optional dependency maps with affected-owner and test impact."
---

# S05 - Architectural Dependency Analysis

## Input and output

Require: Subsystem graph, local module graph, shared contracts, and a proposed change set.

Produce: Typed build, runtime, data, and optional dependency maps with affected-owner and test impact.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Classify each edge.
2. Detect build cycles.
3. Identify runtime cycles that require ports.
4. Compute affected consumers.
5. Validate bootstrap and shutdown order.
6. Keep optional features from entering the required local path.

## Verification

The construction graph is acyclic and every affected contract consumer is accounted for.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A runtime message loop is incorrectly treated as a mandatory build-order cycle.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

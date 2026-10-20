---
name: durable-storage-engineering
description: "Use when constructing or verifying CETA durable storage engineering. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce durable local records, atomic publication intent, integrity checks, and tested restoration."
---

# S09 - Durable Storage Engineering

## Input and output

Require: Reconciled storage engine, data schemas, transaction boundaries, retention rules, and fault fixtures.

Produce: Durable local records, atomic publication intent, integrity checks, and tested restoration.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Define authoritative versus derived stores.
2. Choose explicit commit boundaries.
3. Handle disk-full and corruption.
4. Coordinate durable event publication.
5. Test crash points.
6. Verify backup restoration and deletion propagation.

## Verification

Each injected crash yields a documented prior, committed, or explicitly uncertain state without silent data loss.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: An in-memory success acknowledgement precedes durable commit.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

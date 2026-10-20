---
name: desktop-interface-implementation
description: "Use when constructing or verifying CETA desktop interface implementation. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a usable native interface with exact decision surfaces, recoverable drafts, and observed outcome presentation."
---

# S15 - Desktop Interface Implementation

## Input and output

Require: Approved user workflows, native command contracts, accessibility requirements, and authoritative state events.

Produce: A usable native interface with exact decision surfaces, recoverable drafts, and observed outcome presentation.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Separate renderer state from authority.
2. Bind actions to exact proposals.
3. Handle stale views and reconnects.
4. Implement keyboard and assistive paths.
5. Show partial and uncertain outcomes.
6. Test native effects behind controls.

## Verification

Critical approval, denial, stop, and recovery workflows function through accessible controls.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: A control looks safe while an alternate keyboard or IPC path still performs an unauthorized effect.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.

# 15-COMMUNICATION-AND-INTERACTION - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [03-COMPANION-INTELLIGENCE](../03-COMPANION-INTELLIGENCE/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

## Ordered work

1. Inspect the existing local implementation and classify every logical unit as reuse, extend, or create; record exact source digests.
2. Approve canonical interfaces, domain records, error semantics, and state ownership with affected producers and consumers.
3. Create positive, negative, boundary, and recovery fixtures before relying on the new behavior.
4. Implement pure validation and transformation logic first; then connect canonical state, authority, resources, evidence, and controlled effects as applicable.
5. Integrate the component flows listed below in their actual dependency order, using the existing application composition mechanism.
6. Exercise real cross-subsystem paths and concurrency, cancellation, resource, and recovery failures.
7. Update user and engineering documentation from observed behavior and preserve source-to-test-to-artifact traceability.
8. Submit exact artifacts and raw evidence to independent verification; close the subsystem gate only after all required obligations pass.

## Component integration units

| Component | Flow to construct |
| --- | --- |
| [15.01 Conversation](15.01-CONVERSATION/README.md) | Accept exact messages and drafts; preserve order and identity; stream assistant responses; reconcile delivery and storage; render history with provenance. |
| [15.02 Voice](15.02-VOICE/README.md) | Obtain microphone permission; capture bounded audio; transcribe with uncertainty; confirm consequential ambiguity; synthesize approved output; support interruption and cleanup. |
| [15.03 Channels](15.03-CHANNELS/README.md) | Configure an optional channel; verify endpoint and sender identity; normalize incoming data; authorize outgoing content and recipient; record delivery uncertainty accurately. |
| [15.04 Attachments](15.04-ATTACHMENTS/README.md) | Stage bytes; validate type and size; inspect unsafe structures; store under scoped ownership; create source references; ingest only through qualified parsers. |
| [15.05 Human Intervention](15.05-HUMAN-INTERVENTION/README.md) | Present the exact decision and consequences; authenticate the responding human; bind the response to the proposal revision; expire stale prompts; resume only authorized work. |
| [15.06 Multimodal Interaction](15.06-MULTIMODAL-INTERACTION/README.md) | Validate image or media input; extract authorized observations; preserve spatial and temporal source references; combine with dialogue context; expose uncertainty. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

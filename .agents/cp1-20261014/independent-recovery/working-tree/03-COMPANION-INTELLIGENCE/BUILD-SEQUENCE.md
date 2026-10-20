# 03-COMPANION-INTELLIGENCE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md), [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md), [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md).

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
| [03.01 Companion Identity](03.01-COMPANION-IDENTITY/README.md) | Create a persistent companion profile; bind it to approved identity and preferences; evolve it through recorded changes; expose only currently available capabilities. |
| [03.02 Dialogue Intelligence](03.02-DIALOGUE-INTELLIGENCE/README.md) | Accept a turn; preserve exact user wording; identify consequential ambiguity; assemble authorized context; generate a response plan; expose factual basis and proposed actions. |
| [03.03 Continuity And Adaptation](03.03-CONTINUITY-AND-ADAPTATION/README.md) | Load continuity records; apply explicit preferences; propose uncertain adaptations; reconcile interrupted sessions; restore task and dialogue references. |
| [03.04 Initiative And Deliberation](03.04-INITIATIVE-AND-DELIBERATION/README.md) | Identify a useful initiative; state rationale and alternatives; assess authority; ask for decisions where required; create a governed task only after valid approval. |
| [03.05 Companion Operations](03.05-COMPANION-OPERATIONS/README.md) | Translate approved plans into tasks; request tools through orchestration; observe progress; present results and interruptions with evidence links. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

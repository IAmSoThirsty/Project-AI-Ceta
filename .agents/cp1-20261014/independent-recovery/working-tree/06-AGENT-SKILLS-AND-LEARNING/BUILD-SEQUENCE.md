# 06-AGENT-SKILLS-AND-LEARNING - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [06.01 Skill Definitions](06.01-SKILL-DEFINITIONS/README.md) | Define a versioned skill contract; declare dependencies and effects; validate its structure; bind approved instructions and qualification evidence. |
| [06.02 Skill Discovery](06.02-SKILL-DISCOVERY/README.md) | Search approved skills; match task intent and declared requirements; filter unavailable or unauthorized choices; return explainable candidates. |
| [06.03 Skill Execution](06.03-SKILL-EXECUTION/README.md) | Pin a qualified skill; validate inputs; obtain scoped task admission; execute through governed tools; validate outputs and evidence; finalize explicitly. |
| [06.04 Skill Learning](06.04-SKILL-LEARNING/README.md) | Extract a candidate from successful work; remove incidental secrets and authority; define applicability; test unseen cases; request approval; publish a new revision. |
| [06.05 Skill Lifecycle](06.05-SKILL-LIFECYCLE/README.md) | Publish versioned revisions; pin active runs; revoke unsafe versions; invalidate pending invocations; retain auditable history and rollback evidence. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

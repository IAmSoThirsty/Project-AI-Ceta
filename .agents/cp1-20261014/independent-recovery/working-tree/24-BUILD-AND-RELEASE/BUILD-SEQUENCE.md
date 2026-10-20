# 24-BUILD-AND-RELEASE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [01-CONSTITUTIONAL-GOVERNANCE](../01-CONSTITUTIONAL-GOVERNANCE/README.md), [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [03-COMPANION-INTELLIGENCE](../03-COMPANION-INTELLIGENCE/README.md), [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md), [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md), [06-AGENT-SKILLS-AND-LEARNING](../06-AGENT-SKILLS-AND-LEARNING/README.md), [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md), [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md), [12-ENGINEERING-INTELLIGENCE](../12-ENGINEERING-INTELLIGENCE/README.md), [13-NATIVE-DEVELOPMENT-WORKSPACE](../13-NATIVE-DEVELOPMENT-WORKSPACE/README.md), [14-AUTOMATION-AND-SCHEDULING](../14-AUTOMATION-AND-SCHEDULING/README.md), [15-COMMUNICATION-AND-INTERACTION](../15-COMMUNICATION-AND-INTERACTION/README.md), [16-KNOWLEDGE-AND-RESEARCH](../16-KNOWLEDGE-AND-RESEARCH/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md), [21-EXTENSIONS-AND-INTEROPERABILITY](../21-EXTENSIONS-AND-INTEROPERABILITY/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../22-DESKTOP-AND-USER-EXPERIENCE/README.md), [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md).

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
| [24.01 Build Orchestration](24.01-BUILD-ORCHESTRATION/README.md) | Pin source and dependencies; validate configuration; build in a controlled environment; record outputs; reproduce or explain declared nondeterministic fields; hand off exact artifacts. |
| [24.02 Version Management](24.02-VERSION-MANAGEMENT/README.md) | Assign a product release identity; validate component and schema compatibility; generate an immutable release manifest; bind version labels to exact artifacts and evidence. |
| [24.03 Packaging](24.03-PACKAGING/README.md) | Assemble only approved artifacts; validate contents and permissions; create a native installer or portable package; test clean installation and offline use; preserve user data on upgrade and removal. |
| [24.04 Release Integrity](24.04-RELEASE-INTEGRITY/README.md) | Bind release artifacts to the manifest; sign through approved protected facilities where configured; verify trust and exact bytes; record provenance and distribution identity. |
| [24.05 Update And Rollback](24.05-UPDATE-AND-ROLLBACK/README.md) | Validate the exact update; preflight compatibility and capacity; create a recovery point; apply staged changes; verify startup and data; roll back or forward-repair under declared rules. |
| [24.06 Product Completion](24.06-PRODUCT-COMPLETION/README.md) | Reconcile full approved scope; verify every mandatory gate; exercise complete installed workflows; inspect evidence independently; issue an accurate product-completion decision. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

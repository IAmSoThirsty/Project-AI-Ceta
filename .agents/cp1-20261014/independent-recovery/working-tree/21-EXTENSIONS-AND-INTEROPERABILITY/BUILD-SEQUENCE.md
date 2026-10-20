# 21-EXTENSIONS-AND-INTEROPERABILITY - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [06-AGENT-SKILLS-AND-LEARNING](../06-AGENT-SKILLS-AND-LEARNING/README.md), [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [21.01 Extension Manifests](21.01-EXTENSION-MANIFESTS/README.md) | Define extension content and interfaces; validate manifest and dependencies; inspect required effects; stage qualification before activation. |
| [21.02 Extension Lifecycle](21.02-EXTENSION-LIFECYCLE/README.md) | Stage verified artifacts; qualify in isolation; request activation; switch revisions atomically; revoke or uninstall with data and authority cleanup. |
| [21.03 Interoperability Contracts](21.03-INTEROPERABILITY-CONTRACTS/README.md) | Negotiate compatible schemas; authenticate the peer; translate only declared semantics; enforce scope and message limits; reject incompatible or ambiguous operations. |
| [21.04 Extension Security](21.04-EXTENSION-SECURITY/README.md) | Assign an extension principal; grant minimum capabilities; launch in qualified isolation; verify code integrity; monitor and revoke on boundary failure. |
| [21.05 Native Extension Kit](21.05-NATIVE-EXTENSION-KIT/README.md) | Provide native extension construction guidance and contract fixtures; generate only owner-requested templates in the future implementation; qualify extensions against the same runtime rules. |
| [21.06 Extension Catalog](21.06-EXTENSION-CATALOG/README.md) | Index inspectable extension metadata; verify integrity and review state; filter compatibility; present approval requirements; keep acquisition and activation separate. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

# 01-CONSTITUTIONAL-GOVERNANCE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [01.01 Constitutional Sources](01.01-CONSTITUTIONAL-SOURCES/README.md) | Ingest authoritative rule sources; validate provenance and structure; stage a revision; obtain approval; activate atomically and retain earlier revisions. |
| [01.02 Policy Engine](01.02-POLICY-ENGINE/README.md) | Normalize an action proposal; select applicable rules; evaluate typed predicates; resolve explicit precedence; emit a decision with its supporting rule trace. |
| [01.03 Governance Transitions](01.03-GOVERNANCE-TRANSITIONS/README.md) | Create a complete transition proposal; bind approvals to its digest; validate quorum and revocation; commit the decision and its evidence atomically. |
| [01.04 Thirsty Lang](01.04-THIRSTY-LANG/README.md) | Parse the locally reconciled language grammar; resolve names; type-check policy expressions; compile a bounded representation; retain source maps. |
| [01.05 Policy Assurance](01.05-POLICY-ASSURANCE/README.md) | Check rule safety and traceability; exercise boundary fixtures; assess amendments; block activation when required evidence is absent. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

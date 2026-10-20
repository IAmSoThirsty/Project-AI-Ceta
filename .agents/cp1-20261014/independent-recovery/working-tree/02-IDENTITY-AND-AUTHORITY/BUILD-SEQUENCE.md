# 02-IDENTITY-AND-AUTHORITY - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [02.01 Principal Identity](02.01-PRINCIPAL-IDENTITY/README.md) | Enroll a principal through an authorized process; verify credentials; bind device and process identities where required; rotate or revoke without losing attribution. |
| [02.02 Session Authority](02.02-SESSION-AUTHORITY/README.md) | Establish a session; calculate its permitted scope; refresh only through valid reauthentication; terminate and invalidate cached authority. |
| [02.03 Capability Tokens](02.03-CAPABILITY-TOKENS/README.md) | Issue a capability from approved authority; bind exact scope and effect inputs; validate authenticity and current status; consume or revoke according to its usage rule. |
| [02.04 Delegated Authority](02.04-DELEGATED-AUTHORITY/README.md) | Construct a bounded delegation graph; verify parent-child attenuation; propagate revocation; reevaluate dependent work at admission and effect boundaries. |
| [02.05 Authority Recovery](02.05-AUTHORITY-RECOVERY/README.md) | Enter a restricted recovery flow; verify configured recovery proofs; rotate affected authority; invalidate old credentials; test restored control before reopening effects. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

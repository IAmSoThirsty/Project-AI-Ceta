# 18-SECURITY-AND-ENFORCEMENT - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [18.01 Cryptographic Identity](18.01-CRYPTOGRAPHIC-IDENTITY/README.md) | Create or import authorized protected keys; bind intended uses and devices; sign or verify through handles; rotate with historical trust records; revoke compromised material. |
| [18.02 Secret Protection](18.02-SECRET-PROTECTION/README.md) | Store secrets under authenticated encryption through qualified facilities; issue short-lived scoped access; prevent context and log leakage; rotate and invalidate old references. |
| [18.03 Security Policy](18.03-SECURITY-POLICY/README.md) | Define protected boundaries and controls; evaluate requests against the active policy; install qualified enforcement; verify actual activation before admitting effects. |
| [18.04 Risk And Anomaly](18.04-RISK-AND-ANOMALY/README.md) | Collect authorized telemetry; compare against scoped baselines and explicit rules; classify anomalies; request or trigger only preauthorized responses; retain explainable evidence. |
| [18.05 Incident Response](18.05-INCIDENT-RESPONSE/README.md) | Open an incident; preserve relevant evidence; apply authorized containment; assess scope; repair and requalify; reopen effects only after verified recovery. |
| [18.06 Security Assurance](18.06-SECURITY-ASSURANCE/README.md) | Inspect dependency and trust integrity; run boundary-focused checks; assemble evidence; classify open findings; gate release according to explicit acceptance rules. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.

# 18-SECURITY-AND-ENFORCEMENT

## Mission

Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity.

**Invariant:** Risk scores support decisions but cannot grant authority. Cryptographic operations use reconciled, established implementations and explicit threat models.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [18.01 Cryptographic Identity](18.01-CRYPTOGRAPHIC-IDENTITY/README.md) | Create or import authorized protected keys; bind intended uses and devices; sign or verify through handles; rotate with historical trust records; revoke compromised material. | 3 |
| [18.02 Secret Protection](18.02-SECRET-PROTECTION/README.md) | Store secrets under authenticated encryption through qualified facilities; issue short-lived scoped access; prevent context and log leakage; rotate and invalidate old references. | 3 |
| [18.03 Security Policy](18.03-SECURITY-POLICY/README.md) | Define protected boundaries and controls; evaluate requests against the active policy; install qualified enforcement; verify actual activation before admitting effects. | 3 |
| [18.04 Risk And Anomaly](18.04-RISK-AND-ANOMALY/README.md) | Collect authorized telemetry; compare against scoped baselines and explicit rules; classify anomalies; request or trigger only preauthorized responses; retain explainable evidence. | 3 |
| [18.05 Incident Response](18.05-INCIDENT-RESPONSE/README.md) | Open an incident; preserve relevant evidence; apply authorized containment; assess scope; repair and requalify; reopen effects only after verified recovery. | 3 |
| [18.06 Security Assurance](18.06-SECURITY-ASSURANCE/README.md) | Inspect dependency and trust integrity; run boundary-focused checks; assemble evidence; classify open findings; gate release according to explicit acceptance rules. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.

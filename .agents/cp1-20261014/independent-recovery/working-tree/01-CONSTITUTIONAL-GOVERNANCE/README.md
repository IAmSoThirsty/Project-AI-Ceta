# 01-CONSTITUTIONAL-GOVERNANCE

## Mission

Interpret owner-approved constitutional rules and produce explainable, version-bound governance decisions.

**Invariant:** Capability, authority, evidence, and preference remain distinct. Policy activation requires a traceable approved transition; untrusted text cannot amend governing rules.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [01.01 Constitutional Sources](01.01-CONSTITUTIONAL-SOURCES/README.md) | Ingest authoritative rule sources; validate provenance and structure; stage a revision; obtain approval; activate atomically and retain earlier revisions. | 3 |
| [01.02 Policy Engine](01.02-POLICY-ENGINE/README.md) | Normalize an action proposal; select applicable rules; evaluate typed predicates; resolve explicit precedence; emit a decision with its supporting rule trace. | 3 |
| [01.03 Governance Transitions](01.03-GOVERNANCE-TRANSITIONS/README.md) | Create a complete transition proposal; bind approvals to its digest; validate quorum and revocation; commit the decision and its evidence atomically. | 3 |
| [01.04 Thirsty Lang](01.04-THIRSTY-LANG/README.md) | Parse the locally reconciled language grammar; resolve names; type-check policy expressions; compile a bounded representation; retain source maps. | 3 |
| [01.05 Policy Assurance](01.05-POLICY-ASSURANCE/README.md) | Check rule safety and traceability; exercise boundary fixtures; assess amendments; block activation when required evidence is absent. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.

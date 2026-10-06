# Identity and canonical objects

**Document ID:** SPEC-06  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-06-01

Define stable logical identities for human, installation, Companion, project, task, source, artifact, model configuration, policy, worker session, tool, grant, operation, observation, claim, review, and recovery event. A display name is not a credential. Changing weights does not erase Companion history or masquerade as an unchanged configuration. Restarted workers receive new session identities while tasks retain their logical identities.

### REQ-06-02

Use typed, versioned records with bounded fields and explicit absence. Include identifier, schema, owning scope, actor/observer identity, creation metadata, causal reference, provenance, commitments, and lifecycle state. Claims and observations preserve epistemic status, valid time, recorded time, uncertainty, and supersession. Confidence requires a declared meaning and calibration basis; do not fabricate probabilities from model self-report.

### REQ-06-03

Define canonical bytes and domain separation. Reject duplicate security-relevant keys, non-finite numbers, unsupported schemas, ambiguous normalization, unknown authorization fields, invalid references, and unreasonable lengths. Use explicit units and exact security-critical counters. Preserve original signed legacy bytes; translated records receive new identities and conversion provenance.

### REQ-06-04

Namespace invariant IDs and maturity labels by source/version. Do not compare identical-looking C0-C6 values from unrelated scales or treat VERIFIED, SUPPORTED, ACTIVE, PROMOTED, and READY as synonyms. Converters need success, rejection, and round-trip tests where meaningful, with accounting for unrepresentable information. Missing fields stay missing rather than being invented.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B007, B056, B059. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

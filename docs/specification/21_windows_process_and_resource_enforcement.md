# Windows process and resource enforcement

**Document ID:** SPEC-21  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-21-01

Declare the attacker model before model-directed tools: hostile data, malicious model outputs, untrusted repository code, compromised workers, forged IPC, and bypass attempts. State assumptions about OS, kernel service, administrator, drivers, and hardware. Protect broker, store, and key handles from worker identities through actual Windows principals and controls. Two same-privilege processes are not independent trust domains.

### REQ-21-02

Use Job Objects for lifecycle/resource controls, with a separately qualified mechanism for filesystem, network, registry, credential, device, and process isolation. Investigate AppContainer or another justified Windows mechanism against the actual profile. Request bounded elevation when installing a necessary service/principal; do not elevate the entire application or disable defenses. If containment cannot be established, deny the affected untrusted-execution capability and continue safe unrelated functions.

### REQ-21-03

Keep broker APIs narrow and typed. No arbitrary Python objects, shell text, SQL, signing bytes, or module imports. Authenticate peer identity and restrict message origins. Deny unintended inherited handles/credentials. Workers use controlled environments, stable lifetime identity, private temporary storage, restricted egress, and bounded output.

### REQ-21-04

Test Windows path realities: traversal, absolute/relative confusion, UNC, reparse points, junctions, symlinks, hardlinks, alternate streams, reserved devices, case/Unicode ambiguities, short aliases, file replacement, parent rename, and deletion races. Secure opens and retained handles must protect the actual access interval. A final diff cannot undo an unauthorized read.

### REQ-21-05

Keep OctoReflex's Linux eBPF/LSM backend distinct from Windows qualification. A Linux hook protects the domain actually running under it. Do not describe Windows or WSL-hosted operations as protected without observing that boundary. Reuse upper-level contracts while preserving platform-specific evidence.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B065, B066, B067, B068, B069, B070, B071, B072. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

# Dependency, composition and IPC rules

**Document ID:** ARCH-02  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Static structure

`src/ceta/contracts` is a pure leaf dependency. Every domain package may depend on it; domain packages communicate through injected ports declared by the owning contracts, not through imports of each other's concrete stores or widgets. Add `src/ceta/application` for use-case orchestration and `src/ceta/composition` for startup wiring when implementation begins. The composition root may know concrete implementations; the kernel may not depend on the desktop, model runtime, HTTP library or retained legacy module.

Tests may inject controlled infrastructure implementations without replacing the real integration path in system evidence. Imported source algorithms move behind the new contract with attribution. Historical compatibility adapters are bounded import/export/provider surfaces and have explicit retirement conditions. Dynamic imports must not conceal a forbidden static dependency.

## Process boundaries

The desktop presents data and obtains trusted user interaction. The application service owns kernel/store composition and admits work. Inference and arbitrary repository execution use restricted worker identities and cannot open authority storage or keys. A broker authenticates operations and enforces resource access; outcome observation is separately attributable. A hardened custody service handles sensitive material, and actual distributed authorities remain separately administered.

Do not spawn one process merely for every named role. Galahad, Cerberus, Codex, Clotho, Lachesis and Atropos describe responsibilities; placement follows the attacker model, resources and required independence. A second process under the same administrator does not satisfy a separate administrative-domain claim.

## Transport contract

Prefer an authenticated local transport qualified on the target Windows build. Messages have a version, message ID, correlation/causation IDs, sender session, receiving service generation, operation kind, bounded body commitment and absolute validity. The receiver checks actual OS peer/lifetime evidence, accepted schema, exact resource scope and replay state before dispatch. Client-declared role or PID is never sufficient authentication.

Use length-bounded framing, reject duplicate JSON keys and unsupported critical fields, and stop parsing before allocating attacker-declared unbounded content. Sensitive payloads travel only to the permitted consumer, with redacted audit references. IPC does not expose general shell commands, SQL, file handles chosen by a caller, arbitrary signing data or pickle-like object deserialization.

## Port semantics

Kernel ports accept proposed commands and produce decisions/commits; store ports implement transactions only for the trusted writer; worker ports accept admitted work with fences and deadlines; observer ports return typed observations. An acknowledgment means receipt of a request, not a completed effect. Each asynchronous response includes the original task/session/attempt so stale callbacks can be rejected.

## Verification

Implement an import-boundary test, dependency-cycle check and runtime bypass probes. Attempt unauthenticated IPC, stale generations, oversized messages, replayed requests and forged UI approvals. Count every denied call as evidence while ensuring denial logging cannot exhaust stop/recovery capacity. Build-system exceptions require a versioned architecture decision, not a hidden compatibility import.

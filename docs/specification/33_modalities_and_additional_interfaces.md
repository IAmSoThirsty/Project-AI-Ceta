# Modalities and additional interfaces

**Document ID:** SPEC-33  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-33-01

Implement the shared modality contract now: consent, capture scope, device/source identity, time, freshness, uncertainty, retention, cancellation, and provenance. Local voice and selected-screen interpretation are capability lanes in the same system, not new assistants. Use the same request compiler, identity, graph, authority, and evidence. Preserve text-only operation.

### REQ-33-02

Capture requires explicit activation and visible status. Define the selected push-to-talk or other capture policy; no silent always-on recording. Recognition mistakes remain uncertain observations. Ambiguous spoken commands cannot authorize irreversible effects without required confirmation. Modality input cannot bypass privacy or project boundaries.

### REQ-33-03

Network services, browsers, devices, and physical actuators use manifested, qualified adapters. Sending, publishing, purchasing, or operating equipment requires exact targets and action-specific authority. Physical actions need real interlocks and hardware qualification. Missing hardware keeps requirements open and lanes unavailable; mocks prove only their bounded contracts.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B118, B120, B063. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

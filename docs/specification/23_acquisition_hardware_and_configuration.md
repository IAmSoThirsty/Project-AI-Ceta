# Acquisition, hardware, and configuration

**Document ID:** SPEC-23  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-23-01

Provide explicit import/download with source, license, identity, size, and storage needs disclosed beforehand. Support resume, offline import/export, corruption detection, and explicit repair/discard without deleting unrelated files. Reject traversal, links, duplicate/conflicting names, decompression bombs, and oversized metadata before extraction. Activate assets only after complete verification.

### REQ-23-02

Inspect the actual executing machine. Distinguish physical/available RAM, commit pressure, dedicated/shared GPU memory, driver/backend compatibility, and observed placement. An OS-listed GPU does not prove backend support. Do not reuse a developer machine's measurements as product defaults. Unknown admission-critical resources block dependent configurations.

### REQ-23-03

Budget weights, KV cache, context, output, runtime, verification/store work, UI, and recovery reserves. Estimate, then measure loading and sustained use. Do not select the largest model solely because weights fit. Prefer configurations meeting quality and latency criteria. Preserve usable workspace functions without a model.

### REQ-23-04

Acquisition, training, and paid resources require their own permission. A failed probe does not authorize a large download. Preserve current selection until replacement is tested and accepted. Provide real rollback of compatible model configurations without rewriting user history.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B072, B075, B080, B113, B121. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

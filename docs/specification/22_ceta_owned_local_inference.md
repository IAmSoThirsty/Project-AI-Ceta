# CETA-owned local inference

**Document ID:** SPEC-22  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-22-01

Implement one CETA-owned provider contract over replaceable local inference infrastructure. Pin GGUF identity, template, tokenizer, executable, launch configuration, and supported devices. CETA owns startup, stop, unload, replacement, and qualification. Local failure must never trigger implicit external inference. Shared names, tags, or ports cannot establish trusted readiness.

### REQ-22-02

Use an owned worker and authoritative residency/dispatch lease per backend. Bind process lifetime and generation, not merely PID/hostname/tag. Prevent multi-instance races and dispatch into an uncertain backend. Stream disconnect or timeout does not establish cessation of computation. Observe cancellation or owned termination before conflicting work.

### REQ-22-03

Qualify exact template rendering/tokenization for each backend. Include special tokens, attachments, roles, schemas, mandatory instructions, and reserved output. Disable silent truncation/context shifting where supported and reject configurations that cannot meet their stated guarantees. Verify runtime-reported counts where available. Unsupported configurations remain explicitly estimated or unqualified.

### REQ-22-04

Keep inference away from keys, authority stores, unrelated files, and unrestricted networks. Verify model parsers/formats, sizes, dependencies, and licenses. Avoid arbitrary executable deserialization. Changed runtime, template, weights, placement, or relevant settings invalidate qualifications and prepared work.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B073, B074, B075, B076, B077, B078, B079, B080. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

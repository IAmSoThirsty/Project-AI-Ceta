# Fixed engineering decisions

**Document ID:** SPEC-03  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-03-01

Deliver a native Windows x64 application first, with local ownership and a usable offline mode. Retain CETA's product identity, conversations, workspace use, and user-visible capabilities through qualified migration. Use the current Python/PySide6 lineage as the default host technology unless a concrete incompatibility justifies a documented change. A ground-up design does not require replacing a desktop product with a web service or distributed deployment platform.

### REQ-03-02

CETA must own model identity, GGUF execution lifecycle, template/tokenizer binding, context, authority, scheduling, recovery, and evidence. A bundled llama.cpp-derived runtime may be infrastructure behind that CETA-owned contract. Normal use must not require an independently installed Ollama service, paid subscription, or cloud account. Retain legacy external-provider configuration only as migration information or an explicitly selected compatibility adapter; it must not become a mandatory dependency or hidden second execution path.

### REQ-03-03

Design a modular system with a small trusted control boundary, not one process with universal authority. Keep the deterministic kernel independent of UI, model libraries, network clients, and arbitrary plugins. Treat cognition and model execution as untrusted relative to authority and protected storage. Use native code where Windows isolation, secret handling, resource-handle lifetime, or cancellation requires it; reuse an appropriate supported implementation first, otherwise justify a small native helper. Freeze its language and toolchain before workers generate incompatible implementations.

### REQ-03-04

One coherent application may contain several isolated processes. Shared contracts, explicit ownership, consistent identities, one history model per scope, one effect-admission path, and one recovery model create coherence. Physical separation remains real wherever a security claim requires it. Do not confuse one application with one address space, or distributed cryptographic authority with several classes under one administrator.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B065, B073, B121. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

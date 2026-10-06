# Required artifacts and commands

**Document ID:** SPEC-40  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-40-01

Maintain a rebuild charter; source/authority register; twenty-volume coverage; requirement/implementation/test matrix; system contract; ownership/dependency/trust maps; architecture decisions; threat/assumption registers; schemas/migrations; capability/model qualification; budgets; fixtures/runners; independent verifier; cutover/build/install/update/rollback runbooks; user guide; and truthful continuity map. Use established locations or justified equivalents. Do not produce rival registries for the same authority.

### REQ-40-02

Provide working commands for discovery, setup, contract/integration/security tests, real inference, installed offline validation, performance, migration rehearsal, build, verification, and launch. Final commands refer to actual files and were exercised where claimed. Existing verify_desktop_runtime.py and verify_all.py are leads whose present interfaces must be inspected. Implement one orchestrating verification entry point with readable and machine-readable outputs, without rewriting history.

### REQ-40-03

Evidence binds source before/after, actual interpreter/libraries, model/template, hardware, policy/graph, fixture/seed, commands, outputs, failures, effects, skips, and package. Keep first failures separate from repairs. Label source-only, UI, real-model, installed, network-isolated, hardware-backed, independently reviewed, and elapsed-time evidence.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B004, B007, B008, B126. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

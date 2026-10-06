# Shadow Thirst and pre-effect evaluation

**Document ID:** SPEC-15  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-15-01

Translate proposals into a governed intermediate representation with exact targets, inputs, preconditions, intended effects, authority requirements, failure conditions, observations, and compensation strategy. Preserve originals and revisions. The representation must be supported by a real adapter or rejected as unsupported. Natural-language optimism is not simulation evidence.

### REQ-15-02

Provide isolated staging for edits and supported tests. Staging produces exact candidate artifacts/diffs, environmental evidence, test results, and prediction discrepancies. It must inherit no unrelated secrets, external accounts, or production write mounts. Repository tests execute repository code and therefore require hostile-code containment too.

### REQ-15-03

Bind promotion to exact candidate bytes and source revisions. Simulated success neither authorizes changed artifacts nor establishes behavior on another host. Validate material environment differences. Compensation or rollback is a new admitted operation against current state, not blind restoration over subsequent user changes. Record predictions versus outcomes without making prediction accuracy a source of authority.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B043, B044, B046, B100. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

# Supply chain, signing and delivery

**Document ID:** POL-20  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: build system + verifier + publisher. This policy derives from the ground-up master prompt sections 38. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Release candidates MUST bind actual source, dependencies, build environment, runtime resources, executable and installer identities. Record licenses and the software bill of materials. Inspect libraries loaded by the frozen executable rather than inferring them from development package versions.

Keep publisher keys separate from runtime and custody identities. Generic implementation permission does not authorize production signing, credential extraction, public upload, website changes or trust-store modification. Preserve the established personal publisher-verification decision until explicitly changed. A colocated verification key requires its documented independent fingerprint check.

Validate channel, freshness, signature, bytes, compatibility, migration and rollback before activation. An old installer renamed as new fails source-to-binary verification. Interrupted update preserves usable data and recovery. Source companions and reproducible build recipes accompany the exact candidate; reproducibility claims require repeated-build evidence.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05.

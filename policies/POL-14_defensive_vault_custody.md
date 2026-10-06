# Defensive Vault custody

**Document ID:** POL-14  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: custody service + qualified native secret handling. This policy derives from the ground-up master prompt sections 25. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

The Defensive Vault MUST perform object-scoped admission, sealing, release, recovery and retirement. There is no collection-wide unlock or general mounted plaintext drive. Each release binds object/version, purpose, permitted consumer, exact operation, policy, epoch and verified execution environment.

Storage authority never becomes execution authority. Keys for custody, audit, recovery, token binding and release remain compartmentalized according to the chosen profile. A USB descriptor or serial is not a clone-resistant possession credential. Protect metadata and permitted results as well as content.

Secret lifetime handling must be measured in the actual native boundary and recipient. A variable assignment does not prove zeroization. Probe logs, dumps, buffers, swap, temporary files and failures with harmless canaries. Consumer copies and OS/hardware trust assumptions remain explicit. Recovery rotates affected bindings without exposing a universal bypass.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04.

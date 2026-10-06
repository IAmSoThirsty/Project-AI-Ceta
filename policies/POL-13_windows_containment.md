# Windows containment and IPC

**Document ID:** POL-13  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: native broker + installer + qualification verifier. This policy derives from the ground-up master prompt sections 21, 05. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Model workers, untrusted repository tests and arbitrary code MUST run under an explicit qualified resource-security profile. Job Objects manage lifetime/resources; filesystem, network, credential, device and process access are separate required controls. Lack of a necessary boundary disables that operation profile rather than launching the same operation unrestricted.

IPC authenticates actual peer identity and lifetime with narrow typed operations, bounded messages and replay control. No arbitrary shell, SQL, signing, Python-object or plugin-loader endpoint is permitted in the trusted kernel. Child handles, credentials, environment and library search paths are minimized.

Resource authorization applies to real opened objects. Test reparse points, short aliases, hardlinks, alternate streams, UNC, rename/replacement races and breakaway process routes. The host administrator and kernel assumptions are explicit. Linux OctoReflex claims apply to the Linux boundary actually exercised; they are not inherited by Windows actions.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05.

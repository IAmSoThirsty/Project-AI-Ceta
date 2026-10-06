# CBCC distributed authority and cryptographic composition

**Document ID:** POL-15  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: independent authority domains + sealed operation worker. This policy derives from the ground-up master prompt sections 26, 27. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

CBCC protected operations MUST use independently administered technical trust domains and reviewed cryptographic constructions. Collocated keys or containers under one administrator remain a simulation of those domains. Root secret reconstruction inside the application is forbidden for the distributed-root profile.

Use a sound stable-ciphertext envelope relationship and fresh operation-bound authorization. Every authorization-relevant field, recipient, environment, epoch and nonce must be transcript-bound. Public signatures and Merkle proofs are not secret key entropy, and a threshold signature alone is not confidential decryption. Repeated authorized reads with different valid permits must decrypt the same unchanged object correctly.

Authorities independently verify purpose, policy, traversal, resolver scope, revocation, measurement and output restrictions. Quorum loss cannot downgrade into single-host release. Refresh and revocation have documented assumptions about prior shares, cached material and plaintext; preserved ciphertext captured with a past valid quorum requires separate analysis. External review and real-domain qualification remain explicit gates.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04.

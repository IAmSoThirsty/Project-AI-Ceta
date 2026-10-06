# Security model and trust assumptions

**Document ID:** ARCH-04  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Assets and adversaries

Protect user data, private conversations, keys, authoritative state, consent, source history, pending work and qualified model identity. Model outputs, repository content, imported archives, plugins and arbitrary repository tests are hostile-capable inputs. Include compromised ordinary workers, malicious local processes, forged approvals, stolen credentials, stale identity and supply-chain mutation in the threat model.

The initial local application security profile assumes a trusted host kernel and correctly configured privileged broker. An administrator with full control of that host remains outside claims of universal local tamper prevention. Stronger protected-operation profiles add their real hardware, attestation and independently administered domain assumptions. Every assurance claim names its least-supported dependency.

## Trusted computing boundary

Minimize what can authorize or release sensitive material. The UI may capture consent only through its qualified trusted interaction surface; worker text cannot imitate it. The kernel decides authority, the store commits it, and the broker restricts the real effect. Inference workers never receive the publisher key, all-project write access, unrestricted credentials or a general broker escape hatch.

The broker itself uses narrow APIs and limited privileges. A bug in domain logic must not automatically grant arbitrary privileged filesystem access. Separate installation-time authority from everyday task authority. Review its dependency closure, inherited handles and communications as security-critical implementation.

## Layers and distinct guarantees

Job lifetime controls, per-process file/network restrictions, protected-object custody, policy evaluation and cryptographic quorum are different controls. A successful test of one is not a certificate for another. Distinct processes are not distinct administrators. Launch hashing is not remote attestation. Tool-output text is not a verified effect. Document these distinctions in user-visible qualification states.

## Resource-specific enforcement

Authorize real resource identity at open/use time. Handle Windows reparse points, parent renames, short aliases, hardlinks, alternate streams and process breakaway. Scope enforcement must prevent unauthorized reads as well as writes; a final diff cannot repair a disclosure. Network access includes internet, DNS, intranet and local loopback paths, each under the declared profile.

## Degradation and restoration

Unknown required state denies the dependent effect and preserves useful unrelated operations. Corrupt history enters read-only recovery. Missing quorum seals protected operations. Evidence exhaustion blocks new actions before losing required audit capacity. Restoration requires current measurements, identity, policy and evidence rather than a reassuring model answer.

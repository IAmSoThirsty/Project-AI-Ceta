# Design decisions and local binding requirements

## Approved construction decisions

| ID | Decision | Basis and consequence |
| --- | --- | --- |
| D01 | Native CETA capability architecture | Implement the approved capabilities under CETA identities and authority, with no named external product integration. |
| D02 | Documentation-only package | Include populated instructions, contracts, roles, skills, maps, and acceptance plans; include no runtime implementation source. |
| D03 | Self-contained logical structure | Preserve the approved subsystem tree because the local working application was not available for inspection. |
| D04 | Reconcile before editing | Map every logical unit to actual local files and prefer reuse or extension of compliant existing owners. |
| D05 | Canonical ownership | One owner exists for each shared schema, authority decision, state record, evidence signer, and resource reservation. |
| D06 | Explicit effect authority | Bind approved inputs, targets, effects, identity, lifetime, and current revocation at the execution boundary. |
| D07 | Honest recovery | Preserve uncertain effects and inspect actual state before retry; recovery cannot revive known revoked authority. |
| D08 | Independent verification | Builders self-check; a distinct verifier reproduces critical results from exact artifacts and observations. |
| D09 | Local core operation | Optional endpoints, channels, and extensions remain optional; local product workflows have explicit offline qualification. |
| D10 | Complete product acceptance | Preserve all approved scope and existing local gates unless the owner explicitly approves a traceable change. |

## Bindings requiring actual local evidence

The application language and module paths, current constitutional rule text and language grammar, storage engine and schemas, native process and IPC mechanisms, cryptographic implementation and canonical encoding profiles, target operating-system enforcement, supported model artifact formats, build and installer tooling, existing acceptance records, and qualified hardware profiles must be inspected locally. These are explicit implementation inputs rather than invented facts. Each binding record names the observed source, digest, selected existing facility, compatibility impact, required tests, and approving owner where a change is needed.

A blocked binding does not authorize a silent substitute. Continue independently valid inspection or design work, preserve completed evidence, and request the specific consequential decision through the assigned owner. The approved architecture remains the target while its concrete local representation is established.

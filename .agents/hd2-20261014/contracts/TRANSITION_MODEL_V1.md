# Transition assessment v1

Status: IMPLEMENTED_NOT_QUALIFIED. Source interpretations remain preliminary until the lead integrator records their disposition. This pure leaf never grants runtime authorization, commits state, consumes a permit, performs an effect, or qualifies a capability.

The implementation is `src/ceta/contracts/transitions.py`. Import that module directly; the shared package exports and existing schemas remain unchanged. Construct `TransitionModel(state_catalog_bytes, transition_rules_bytes, records_schema_bytes, custody_specification_bytes)`. It accepts only the exact source identities below and freezes every catalog list, every record enumeration, the twenty principal entries, their predicate and failure text, and their original acceptance links. Different bytes require an explicit model/version review. Hash identity binds bytes; it does not establish source adoption or runtime truth.

| Input | Exact authorized path | SHA-256 |
| --- | --- | --- |
| State catalog | T:\00-Active\CETA_Intelligence_Operating_System_Build_Package\contracts\state_catalog.json | 232807fa439247ebc9a3da669710f9badf38ac5166549e3f58c6f2448aba45ca |
| Principal requirements | T:\00-Active\CETA_Intelligence_Operating_System_Build_Package\contracts\transition_rules.json | f36239d7a0d7f21829b88f529ff1b5a4a92ea37eb927afe526203376b955467c |
| Record schema | T:\00-Active\CETA_Intelligence_Operating_System_Build_Package\contracts\schemas\records.schema.json | f83f8a1116492266aa9ffbbf85c4e4677218e99d8771f0de61a3affef8313f79 |
| Explicit custody sequence | T:\00-Active\CETA_Intelligence_Operating_System_Build_Package\docs\specification\25_defensive_vault_custody.md | 35f785363a731ee2c88ec88048ef9f7c4d9b4cca6e132582876a3276d2f8c703 |

The first three inputs also match the supplied D contract copies byte for byte. The fourth is an authorized read of the supplied build package. It is not another repository import.

## Direct edges and unresolved interpretations

The source at transition_rules.json:3 says principal entries are semantic requirements rather than executable enforcement and additional legal transitions require a recorded amendment. Named states alone do not establish an edge. The model therefore retains unresolved states, preserves every principal entry, and denies every absent or unresolved edge. It does not generate a chain by interpolating names.

| Principal entry | Current direct interpretation | Source and exact parent | Original acceptance links |
| --- | --- | --- | --- |
| TR-01 CREATED -> ACTIVE | Supplied principal edge; full guards required | transition_rules.json:6; REQ-09-01/03, REQ-19-01/05 | B027 B057 |
| TR-02 ACTIVE -> WAITING_FOR_CLARIFICATION | Supplied principal edge; bounded-question/raw-preservation guards | transition_rules.json:18; REQ-11-01/02 | B025 B027 B028 |
| TR-03 PENDING -> READY | Supplied principal edge; every hard prerequisite/current policy/evidence | transition_rules.json:31; REQ-18-01/02 | B049 B050 B055 |
| TR-04 READY -> RUNNING | VERIFIED_UNRESOLVED: CLAIMED is separately named | transition_rules.json:44; schema PlanNode.state; REQ-18-03 | B052 B053 B054 |
| TR-05 RUNNING -> SUCCEEDED | Supplied principal edge; exact receipt/output/observation verification | transition_rules.json:57; REQ-18-04 | B046 B055 B056 |
| TR-06 PROPOSED -> PREPARED | VERIFIED_UNRESOLVED: VALIDATED is separately named | transition_rules.json:70; state_catalog.json:24; REQ-20-01 | B058 B059 B063 |
| TR-07 PREPARED -> INTENT_COMMITTED | Supplied principal edge; current authority/read set and atomic durable reservation/intent | transition_rules.json:83; REQ-19-03, REQ-07-01/05 | B009 B016 B031 |
| TR-08 INTENT_COMMITTED -> ADMISSION_REDEEMED | Supplied principal edge; authenticated peer, fence/permit/revocation, protected handle/preconditions, consume once | transition_rules.json:96; REQ-19-01/02/03 | B060 B061 B068 B070 |
| TR-09 ADMISSION_REDEEMED -> RUNNING | VERIFIED_UNRESOLVED: DISPATCHED is separately named | transition_rules.json:110; state_catalog.json:24; REQ-20-01 | B063 B067 B098 |
| TR-10 RUNNING -> PROCESS_EXITED | Supplied principal edge; actual owned termination and retained exit/output | transition_rules.json:123; REQ-20-03, REQ-30-01 | B077 B078 B097 |
| TR-11 PROCESS_EXITED -> VERIFIED | VERIFIED_UNRESOLVED: OBSERVED is separately named | transition_rules.json:136; state_catalog.json:24; REQ-20-01/03 | B097 B099 |
| TR-12 RUNNING -> INDETERMINATE | Supplied principal edge; uncertain possible effect, spent permit retained, dependent work fenced | transition_rules.json:149; REQ-20-04, REQ-30-03 | B098 B102 B103 |
| TR-13 OPEN -> SETTLED_WITH_EVIDENCE | VERIFIED_UNRESOLVED: OBSERVING and RESOLVED_CURRENT_STATE are named; optionality/directness unestablished | transition_rules.json:161; schema RecoveryRecord.status; REQ-30-03 | B098 B100 B102 |
| TR-14 ACTIVE -> STOPPING | Supplied principal edge; authenticated stop, admission disabled, bounded owned stop | transition_rules.json:174; REQ-30-01 | B019 B077 B115 |
| TR-15 STOPPING -> STOPPED | Supplied principal edge; observed worker stop, admission disabled, uncertain effects separate | transition_rules.json:187; REQ-30-01/03 | B019 B078 |
| TR-16 SEALED -> AUTHORIZED_RELEASE | Abbreviated normal sequence; direct shortcut denied | transition_rules.json:199; SPEC-25:10 REQ-25-01/02 | B089 B090 B091 B094 |
| TR-17 AUTHORIZED_RELEASE -> SEALED | Abbreviated normal sequence; direct shortcut denied | transition_rules.json:213; SPEC-25:10/22 REQ-25-01/04 | B095 B096 |
| TR-18 NOT_EVALUATED -> QUALIFIED_WITHIN_SCOPE | Supplied principal edge; declared tests/thresholds, exact configuration, independent evidence; this leaf does not qualify it | transition_rules.json:225; REQ-24-01/02, REQ-36-01 | B081 B086 B121 B126 |
| TR-19 ACTIVE -> SUPERSEDED | Supplied principal edge; authorized correction, original provenance, retrieval/dependent invalidation | transition_rules.json:239; REQ-12-03/04, REQ-29-02 | B034 B035 |
| TR-20 VALIDATED_SNAPSHOT -> ACTIVATED | VERIFIED_UNRESOLVED: AWAITING_CUTOVER separately named | transition_rules.json:251; schema MigrationRecord.status; REQ-31-04 | B105 B106 B112 |

SPEC-25:10 explicitly supplies SEALED -> VERIFYING -> AUTHORIZED_RELEASE -> ZEROIZING -> SEALED. The four source-defined normal edges are available as pure guarded assessments. SEALED -> VERIFYING requires the object request/metadata/provenance predicate (REQ-25-02). VERIFYING -> AUTHORIZED_RELEASE requires all TR-16 proof/policy/epoch/quorum/consumer predicates. AUTHORIZED_RELEASE -> ZEROIZING requires the completed permitted operation and available qualified secret boundary (REQ-25-04). ZEROIZING -> SEALED requires the TR-17 actual cleanup and durable outcome predicates. The original TR-16/17 entries remain in `rules`; `direct_edges` contains the normal steps. Their direct shortcuts return SOURCE_DEFINED_SEQUENCE_SHORTCUT_DENIED.

These four guards describe existing duties, not an implementation of cryptographic custody. The source-defined steps include the SPEC-25 acceptance family B089/B093/B095/B096 while retaining original TR acceptance links. No failure, tamper, recovery, release fallback, key export, or ordinary-decryption edge is invented.

The six unresolved principal paths require a recorded decision specifying whether intermediates are required commits, optional paths, or observational projections; exact guards, transition ownership, payload/event versions, and evidence must accompany that decision. Until then the direct principal path and unnamed subedges both remain denied. All other unruled states remain named and unavailable for unestablished transitions.

## Predicate boundary and denials

`PredicateWitness` is immutable internal input, not a twenty-first wire record, a provider credential, or positive authority. Each required label identifies the concrete predicate and existing component expected to supply its observation. Provider strings and evidence references are unauthenticated. The leaf checks exact bool types, bounded/nonduplicate references, complete known predicate coverage, required provider labels, and positive evidence-backed claims. Missing/false predicates, empty evidence, wrong provider labels, duplicates, or unknown predicates cannot yield a supported direct assessment.

Actual identity, evidence signatures, current policy/revocation/read sets, resource handles, atomic claims, durable intent/consumption and settlement must be established by the existing responsible kernel/store/broker boundary. All returned assessments have runtime_authorized=false. Nothing advances authoritative state.

Failure text is retained exactly from each principal source. Replayed/spent permits, revocation winning admission, incomplete storage, uncertain dispatch, timeout mistaken for termination, exit zero without observation, cleanup uncertainty, unsupported qualification and causal-history reconstruction stay denied or outstanding under their stated predicates. These fixtures do not simulate real races or prove native behavior.

## Validation and remaining duties

`tests/contract/test_transitions.py` checks every catalog list/record enum and all twenty principal bodies/cases, legitimate positive predicates, all six unresolved paths, all four source-defined custody edges and both shortcut denials, each missing/false/empty/wrong-owner guard, boundary/race failure claims, unknown edges, exact source drift, immutable results and source preservation.

The original B001-B128 results remain NOT_RUN. Gate A remains OPEN; formal gates remain NOT_EVALUATED. The full 175 parent requirements, 25 components, 28 packages and eight gates remain in scope. Trusted runtime ownership, the six decisions, all other lifecycle edges, transport/admission integration, durable/crash/native/hardware/installed qualification and source adoption remain required.

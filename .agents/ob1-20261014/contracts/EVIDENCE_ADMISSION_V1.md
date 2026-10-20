# Evidence admission prerequisites — Finding 5

Implementation state: **IMPLEMENTED_NOT_QUALIFIED**. Runtime integration: **OPEN**.
Code: `src/ceta/contracts/evidence_admission.py`; tests:
`tests/contract/test_evidence_admission.py`. These are executable pure binding
predicates and an explicit unavailable runtime boundary, not a connected kernel,
authenticated evidence registry, durable store, qualified verifier or effect path.

## Source authority and preserved contract

The October 8 findings-remediation directive Finding 5 authorizes this repair.
Controlling package sources are `contracts/SEMANTIC_VALIDATION.md`, the
`OperationPermit` and `CapabilityQualification` record roles/validation ordering,
`docs/architecture/SYSTEM_CONTRACT.md`, `DEPENDENCIES_AND_IPC.md`, SPEC-07/19/20/36,
and POL-01/02/04/10/11. Parent requirements include REQ-05-02, REQ-07-01/03/05,
REQ-19-01/02/03, REQ-20-01/02/03/04 and REQ-36-01/03/04. Related original cases
B008/B058/B060/B061/B062/B086/B099 remain unexecuted by these unit tests.

All original twenty wire schemas and existing decoder behavior are preserved.
`RelevantReadSet` and the three resolver value objects here are internal metadata,
not additional admitted wire records. Their construction proves no authentication.
No new event type, state transition, quality threshold, permit or grant is issued.

## Implemented predicates

`check_permit_evidence` decodes shape, then rejects CONSUMED/SETTLED without a
consumption reference. Any non-null consumption reference requires an owner
resolver and an exact event plus CONSUMED permit snapshot. The event must match
the injected prior stream position, payload identity/scope/commitment and permit's
consumption reference. All supplied permit fields except the later status and
causal reference must agree with the consumed snapshot. This prevents replacing
nonce, grant, task, adapter, arguments, resource, budget reservation or issuance
identity while reusing a consumption reference. No source fixes an event-type
vocabulary here: the actual store must establish that the resolved event records
durable consumption under the adopted model. A matching event hash is not that
establishment. SETTLED still requires independent outcome evidence and the kernel's
legal settlement; this check alone does not establish either.

`check_qualification_evidence` rejects zero samples, absent executable commitment,
empty/duplicate bundles and an unavailable evidence resolver. Resolved evidence
must bind the exact qualification record commitment, independently supplied
sample/failure/skip counts, every bundle reference and non-null byte commitment,
and nonempty distinct independence-evidence references within those bundles.
The full record commitment includes scope, capability/profile, source, executable,
configuration/model/OS/hardware/adapter, fixture, frozen threshold-policy reference,
counts, claimed independence, validity and invalidation fields. Changing any of
those inputs requires a newly bound evidence resolution. A string claiming
independence cannot replace its evidence. No invented minimum beyond actual
nonzero samples is used; failures/skips are retained, not silently forced to zero.
This predicate neither evaluates the threshold policy nor establishes evidence
truth, current time, actual independence or acceptance. The real verifier must
perform those duties against authenticated evidence and current candidate state.

`check_preparation_evidence` accepts a proposal and internal expected ReadSet. Its
public call does not accept a worker-selected required-resource tuple. The resolver
captured by composition supplies the complete kernel/registry-resolved dependency
set and actual current snapshot, bound to the exact proposal commitment. Missing
resolver, stale proposal, incomplete dependencies, changed relevant state and
misbound/duplicate/null-revision/cross-scope proposal resources reject. Unrelated
current resources remain irrelevant to freshness, as in the existing ReadSet leaf.
This does not make the callback trusted: real composition must restrict resolver
ownership and authenticate its inputs. Worker-controlled construction of this
class is still incapable of runtime admission.

## Runtime boundary and next integration obligations

`require_runtime_admission` always rejects with
`RUNTIME_EVIDENCE_OWNERS_UNAVAILABLE`. There is no allow flag or simulated peer
authentication. Pure checks return no authority token and perform no effect.

The actual kernel/composition must bind authenticated principal/session, current
task and authority, registry-owned exact target/dependencies, policy/reviews/consent,
trusted time, budget/reservation and exact inputs. The protected store must verify
durable issuance and one-time consumption against the accepted event prefix and
commit admission atomically. The broker must recheck fence/revocation and actual
resource handles at the irreversible boundary. The verifier must authenticate
bundle provenance, complete sample accounting, frozen thresholds, current candidate
identity, freshness/invalidation and the actual required degree of independence.
Missing providers keep their activation lane unavailable. Replay reconstructs
evidence without re-executing effects; uncertain effects require reconciliation.

These obligations are not discharged by injected synthetic test values or a
successful binding predicate. Actual success/denial/replay/cancellation/crash
integration remains OPEN, original cases remain NOT_RUN, and Gate A remains OPEN.
The complete175 requirements/25 components/128 cases/28 packages/20 volumes/406
lifecycle originals/eight gates and every mandatory qualification lane remain.

# State lifecycle map

## Task lifecycle

A task starts proposed. Admission requires a complete contract, current authority, dependency readiness, resource reservation, and evidence capacity. Running tasks may pause, await a human decision, enter cancellation, fail, or become uncertain. Verified-complete requires accepted deliverables and current evidence. A terminal state is not reopened by duplicate queue delivery; a new task or explicit authorized transition is required.

## Operation lifecycle

Prepare exact inputs and target identities, persist intent, obtain admission, dispatch, observe effects, commit result state, publish durable notifications, and finalize evidence. An interruption between dispatch and reliable observation creates uncertainty. Local commit and external effect are not one universal atomic transaction. Stable operation IDs and target-side idempotency or reconciliation control duplicates.

## Skill and extension lifecycle

Candidate or staged content is validated, qualified, reviewed, approved, and then activated as an immutable revision. Updates create new revisions. Deprecated content remains inspectable; revoked content cannot receive new admissions. Running work is pinned to its approved revision and responds to revocation through controlled stopping.

## Memory and source lifecycle

Original sources remain distinct from extraction and summaries. Records may be active, disputed, superseded, archived, or deleted under explicit policy. Corrections append lineage; deletion invalidates indexes and derived views. Restoration reconciles known deletion and revocation records before rebuilding retrieval.

## Release lifecycle

A candidate is built from pinned source, tested, independently verified, packaged, installed on qualified targets, and accepted through release gates. Any relevant change invalidates affected evidence. Updating and rolling back preserve user data and known security decisions. Version labels never substitute for content identity.

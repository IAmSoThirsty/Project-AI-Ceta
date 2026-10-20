# Memory lifecycle binding — working profile v1

Profile: `ceta-memory-lifecycle-binding-v1`. This pure contract check is one
metadata boundary; whole Gate A, current authority and actual data-lifecycle
enforcement remain unfinished.

`MemoryLifecycleContract.check_binding` decodes original MemoryRecord and
MemoryLifecycleEvent bytes with the existing strict twenty-record codec. Its
explicit expected scope and retention-policy reference must match both records.
The event must target the exact current memory ID and before-state. Its after
label must belong to the existing six-state MemoryRecord lifecycle namespace.
The check does not choose which state transitions the adopted policy permits.

DELETED_PAYLOAD cannot be asserted with only NOT_REQUESTED or REQUESTED deletion
metadata. LOCAL_DELETION_OBSERVED, BACKUP_RETENTION_PENDING and PARTIAL require
evidence references, but those references do not prove their underlying claim.
The immutable result preserves the claimed state and both original records,
including their canonical commitments. Every result carries outstanding current
authority/policy, authentic initiator/approval and current-memory/reference
verification. Deletion requests retain derivative-copy and backup accounting;
observed/partial claims additionally retain independent deletion verification.
Free-form index actions cannot prove that every copy was removed.

No result is an allow decision, read permission, accepted transition, deletion
completion, global forgetting, custody release or grant. The future kernel must
resolve current store state, adopted policy, initiator, consent where required,
reference scope, identity/clock and actual outcome evidence. Retention/deletion
commands still need bounded authority and broker/observer paths. Restore/import
must not reactivate withdrawn data or grants. Approved minimal tombstones and
commitments may remain under their separate policy; residual backups and copies
outside control must be declared rather than hidden behind a deletion label.

The caller already holds the supplied bytes. Scope checking here cannot undo an
unauthorized fetch or disclosure; authenticated access checks must precede the
actual resource read and disclosure. Caller-authored records or policy strings
are never treated as authenticated current state by this library. The profile
neither adopts policy bytes nor establishes lawful purpose, a jurisdiction,
rights regime or retention horizon.

Source basis: existing MemoryRecord/MemoryLifecycleEvent, POL-05/POL-06,
SPEC-12/SPEC-29, complete originals 047 Privacy and 055 Knowledge Architecture.
ADR-022 in the adjacent specification records this engineering increment.
Sixteen synthetic contract tests cover scoped identity, stale lifecycle, policy
rebinding, misleading deletion claims and immutable original-byte retention.
No payload store, index, embedding, cache, backup, export, model or personal
profile was accessed, changed or deleted by the implementation or its tests.

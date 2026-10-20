# Combined store transaction mechanics v2

Status: IMPLEMENTED_NOT_QUALIFIED. Owner CMP-03; parents REQ-07-01/03/04/05
and mechanical support for REQ-19-03. Source ARCH-03, SPEC-06/07/19, CMP-03 and
WP-02. Fixture construction continues within WP-01; Gate A and the full WP-02
prerequisite remain open. All original cases and formal gates retain their states.

The existing SqliteJournal accepts explicit profile `ceta-sqlite-store-v2`.
The default remains `ceta-sqlite-journal-v1`. Each profile has an exact schema;
opening one as the other rejects through read-only inspection. Existing stores
are never silently migrated, reset or overwritten. Only fresh fixture roots are
used here. The same pinned SQLite engine and filesystem/durability checks apply.

AtomicStorePort is an owner-internal contract, alongside HistoryPort. StoreKey,
StoreCell, StoreExpectation, StoreChange, StorePosition and StoreCommit are
immutable internal values, not additional admitted wire records. Seven fixed
namespaces are grant, budget, reservation, permit, intent, queue and projection.
Canonical object bytes are bounded by the existing wire allocation limit. A
key includes namespace, owning scope and logical identity. Its revision commits
the full key, generation and content digest. Never-present and tombstoned values
have different generations/revisions; recreation never restores an old revision.

`commit` accepts at most 128 events, scopes, state checks and changes per category.
It validates event/payload bytes with the unchanged EventContract. All expected
scope heads and relevant state revisions are compared inside BEGIN IMMEDIATE.
Original event/payload bytes, immutable transaction provenance, state changes,
current cells and all participating stream heads commit once. Failure unwinds
including BaseException roll back while the connection remains alive. Process
termination is handled by SQLite recovery. No human/model/external-process wait
is performed within the transaction; the infrastructure fault hook is test-owned.

Every state change references a newly committed event in its owning scope.
Grant, permit and queue values must decode as their existing record type, match
the key's scope/identity, and equal the referenced event's canonical payload.
Budget, reservation, intent and projection objects are internal provenance
metadata whose domain meaning is not established by this port. The kernel must
select complete dependencies, legal changes and actual charging semantics.
Writing a status field or a matching revision never grants operational authority.

Internal transaction commitments bind exact original event/payload digests,
prior transaction head, relevant state checks, before revisions, generations,
value digests and event associations. Three added tables store commits, original
change values and materialized cells. Full validation checks both histories,
requires every accepted event and change to have exactly one transaction
association, reconstructs every current cell, and denies any divergence.
Snapshot reads are bounded, consistent and validated; replay invokes no effect.
Mechanical reconstruction does not qualify domain projection reducers or event
type/transition semantics. Such reducers must still reject unsupported events.

StorePosition is a separate prefix checkpoint for transaction metadata. An old
StreamPosition binds the event prefix only. Both checkpoint types are supplied
inputs whose authenticity requires a real owner/witness; a complete consistent
local rewrite can pass local checks without that trust boundary. Power-loss,
protected writer handles, authenticated owners, kernel consume/revoke, budget
conservation/charging, outbox dispatch/settlement, installed/frozen qualification
and independent/hardware evidence remain mandatory open obligations.

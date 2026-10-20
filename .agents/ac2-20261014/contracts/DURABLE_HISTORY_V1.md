# Durable history mechanism v1

Status: IMPLEMENTED_NOT_QUALIFIED under the open unified contract. Owner CMP-03;
parent requirements REQ-06-02/03 and REQ-07-01/02/03/04/05. Source: SPEC-07,
ARCH-03, CMP-03, POL-02/07/16 and original master lines 90–96, 216–230 and S14.
Construction is WP-01 fixture implementation; WP-02's complete prerequisite and
Gate A freeze remain open. No production composition or positive authority is
enabled by this mechanism.

An explicit opt-in v2 store profile adds combined transaction mechanics; see
STORE_TRANSACTION_V2.md. V1 remains the default and is never silently migrated.

`contracts.history` declares immutable JournalEntry and JournalCommit values and
the injected HistoryPort. They are internal ports and are not an additional
admitted wire record. `store.journal.SqliteJournal` implements the real port with
SQLite. It imports contracts and its own persistence infrastructure. Existing
20-record schemas, event-head preimages and pure predicates are unchanged.

The owner selects an existing absolute local fixed NTFS root and a fixed database
leaf. Unknown scopes, links/junctions, network/removable drives, unsupported file
systems and missing stores deny. Unknown companions deny explicit creation;
existing WAL sidecars are handled by SQLite during existing-store validation.
Explicit creation uses
exclusive file creation and never overwrites existing bytes. Existing stores
undergo read-only prefix/profile verification before a writable owner connection
opens; the newly opened connection validates again. Corruption is preserved and
rejected. No key, identity, database or history is automatically regenerated.
Every full-prefix check also verifies actual WAL mode inside its transaction,
including the writer acquired after read-only startup inspection.

Each append checks bounded immutable event/payload pairs through the existing
RecordCodec and EventContract. One BEGIN IMMEDIATE transaction validates the
complete accepted prefix, compares the expected per-scope position, inserts the
whole batch and advances the stored position. Unique per-scope event identity
rejects duplicates. Each instance serializes calls; actual competing SQLite
connections share the database's writer lock and expected-position check.
Rollback handles SQLite errors that have already ended the transaction. A crash
before commit leaves no committed batch; a crash after commit retains the batch.

WAL, FULL synchronization, foreign keys, 5000ms busy timeout, NORMAL locking and
1000-page auto-checkpoint are measured on the actual connection. The loader pins
the project DLL and records its actual path, version and retained CPython wrapper.
See SQLITE_RUNTIME_V1.json and the upstream download, advisory, WAL and backup
pages captured in the acquisition evidence. FULL and process-crash tests do not
prove electrical power-loss behavior or installed qualification. Online backup,
checkpoint scheduling, disk-reserve policy and workload qualification remain open.

Validation checks SQLite physical integrity, exact schema/profile/registered
scopes, foreign keys, original stored byte digests, every successor and payload,
and the complete prefix against its stored final positions. An optional retained
checkpoint must match the actual prefix at its exact position; a later tail is
permitted. Append and replay accept optional checkpoints and check them inside
the same transaction as their commit or read. A prior standalone validation does
not bind a subsequent transaction. WAL selection uses an explicit denial that
remains active under optimized Python. Local digests and caller-provided checkpoints are not independent trust
anchors. A complete database rewrite can pass local checks when no authentic
retained anchor contradicts it. Event heads exclude signature_ref as required by
the existing preimage; head/checkpoint equality does not authenticate that field,
verify a signature or prove identity. Those owners remain open.

Replay is bounded and revalidates the full history in a consistent read
transaction. It returns original immutable wires and invokes no effect adapter,
kernel authority transition or model. It changes no logical journal rows. Real
SQLite may manage its own lock/companion metadata; replay is not a claim that
opening a database performs no filesystem activity. Projections and their
supported event-type/payload dispatch require the adopted lifecycle contract.

Fresh fixture tests exercise reopen, exact bytes, actual settings, same-head
competing connections, stale/duplicate denial, injected transaction interruption,
real before/after-commit process termination, SQLITE_FULL through a page limit,
historical tamper, retained-checkpoint rollback, unknown scopes, missing and
existing data, actual junction denial, and conflicting preloaded SQLite. The page
limit generates a real SQLite FULL result without exhausting the machine disk.
Fixtures are retained under .local-test-output/history-20. Their identities/time
are synthetic; the real library/transactions/process crashes are measured.

Still required: authenticated serialized writer/process access; one atomic
events+grants+reservations+intents+queue+projections transaction; real kernel/store
consume/revoke/resource/time ownership; supported event semantics; independent
anchors/signatures; consistent backups/recovery UI; protected OS handles and
integrated admission/effect/observation/settlement. B009–B016 and all original
cases remain NOT_RUN. Gate A remains OPEN and the full objective ACTIVE_NOT_COMPLETE.

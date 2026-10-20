# Typed task creation and durable drafts — v1

This development contract connects native task controls to the current owned
Windows service and captured atomic journal. Original twenty admitted record
schemas and existing kernel operations remain supported. These owner-internal
task commands and projections are explicitly separate from effect authority.

## Input and ownership

`task.create`, `task.save`, `task.load` and `task.list` use the existing versioned
LocalMessage envelope, receiver generation, original request bytes, native peer
lifetime, route/scope allowlist, deadlines and replay checks. The body is an
exact-field `ceta-task-command-v1` TaskCommand, not free text masquerading as an
ActionProposal. The caller chooses its task ID before dispatch; the stored
account-scoped catalog makes confirmed tasks discoverable after restart.

UTF-8 title, original instruction and current draft use strict lowercase hex.
Text is not normalized, summarized or substituted. The decoded title limit is
256 bytes; instruction and draft limits are each 65,536 bytes. A catalog holds
at most 256 task IDs per owner/scope. Exhaustion denies explicitly. The outer
envelope and response remain capped at 1 MiB. Qt `toPlainText()` defines the
captured editor text; this does not claim preservation of original keystroke or
platform newline representations before that capture. API inputs retain CRLF
and decomposed Unicode bytes. Invalid editor input remains in its view and
prevents navigation/write controls until corrected; Stop remains reachable.

The durable owner commitment is domain-separated SHA256 of the revalidated
Windows user SID bytes and composition-selected logical principal. The native
registry derives it from the same active opaque context under `_checked`; a
request supplies neither SID nor ownership. It deliberately omits session,
process, logon and token-object identities. Fresh authenticated sessions for
that owner can read/edit task content. Existing kernel permission recovery
still requires its original principal/session; task recovery grants no session
handoff, consent, scope acceptance or resource access. Same-account unrestricted
processes/admins are not claimed to be isolated by this mechanism.

## State, lineage and atomic writes

`TaskDrafts` is a deterministic kernel owner over injected ports. Task creation
records CREATED, immutable original submitted instruction, separate editable
draft/title, creator/editor sessions, exact command commitment, event lineage
and a generation-bearing objective revision. Clarified meaning, semantic scope,
exclusions, completion predicates, assumptions, questions, standing instructions,
authority, budgets and evidence interpretations remain explicitly unavailable
(`null`), rather than invented from text. They remain mandatory follow-up
obligations under REQ-09-01. CREATED→ACTIVE still requires TR-01's accepted
objective/scope and finite grant through qualified owners.

Draft, catalog and the existing exact `task_wire` revision projection share one
real SqliteJournal transaction and corresponding EventRecord/ObservationEnvelope.
Creation CAS-checks both absent task/draft cells; no existing task projection or
tombstone is overwritten. Save checks the supplied full draft StoreCell revision,
the current kernel task revision and catalog. Original instruction remains
immutable. Every meaningful save advances the draft generation and objective
revision together. A→B→A cannot restore the former objective revision or old
prepared basis. Unchanged suppression follows CAS validation and commits nothing.
All prior versions remain in store changes and associated events; no separate
mutable task database is introduced.

The ObservationEnvelope observes submitted bytes, not the truth of their claims
or human consent. It binds the complete task snapshot, actor/session, original
command cause, scope, event/predecessor and fixed observation semantics. Recorded
wall time is explicitly unqualified; observed time and expiry are unavailable.
Load verifies the actual last event/payload, owner, task/kernel projection and
coherent generation-bearing selected cells. The original context and stable
owner are checked before COMMIT, in its guard, after COMMIT, and after the final
read before disclosure. An after-COMMIT denial preserves the committed state.

## Results, uncertainty and native controls

The separate `ceta-task-result-v1` response binds the exact original envelope,
message/correlation/cause/session/generation/route/scope and command ID.
TASK_SNAPSHOT carries a validated snapshot and generation; TASK_UNCHANGED
binds the supplied CAS revision; TASK_LIST contains bounded task IDs.
TASK_ABSENT is permitted only for load: coherent zero-generation task/draft cells and
catalog absence, rechecked against the same original context, establish current
absence. Tombstones, conflicting minimal task projections and foreign content do
not become absence. This observation asserts no historical rollback. Explicit
task reconciliation can select it only for a pending task.create, retaining local
text and the uncertain original request before a new CAS creation.
All result shapes reject extra fields, invalid types, wrong route/content and noncanonical bytes.
DENIED_RECONCILE contains no snapshot and does not assert rollback. Result shape
checks do not establish storage custody, consent or positive authority.

`TaskOperatorSession` retains per-task local edits independently from confirmed
snapshots. Create/save are explicit asynchronous operations through OwnedService;
editing performs no disk or IPC wait.
The separate local-draft chooser can return to retained unconfirmed tasks without
issuing a load; the stored-task catalog labels confirmed remote entries separately.
An acknowledgment binds the captured
command and edit generation. Newer edits remain UNSAVED; a late result cannot
replace another selected task/view. Loading while locally dirty preserves that
text and exposes a remote observation. Explicit selection of the observed current
revision keeps local text for the next CAS save. A query does not silently rebase.

Task list/unrelated load cannot clear an earlier RECOVERING state. A matching load
can prove the exact captured uncertain task write by its command ID/commitment.
For a newer/conflicting task state, explicit task reconciliation chooses only
the actually observed task revision and retains the old request/current response;
the earlier write's history remains unresolved. This action cannot clear prior
kernel/effect uncertainty. Stop wins before new dispatch admission. Unconfirmed
local text and reconciliation history are retained in memory/controller artifacts,
not claimed power-loss durable. A missing/denied result may follow a commit; no
automatic write replay, refund or clean-state assertion is made.

The native TaskView provides create, save, list, open, reload current task,
explicit state selection and Stop/Esc. It shows SAVING/SAVED/UNSAVED/UNCERTAIN/CONFLICT separately from service
state and displays the immutable original instruction. Reload can query the retained
task ID even when an uncertain creation is not listed in the stored catalog.
Writing after a conflicting or absent load requires explicit current-state selection.
Closing with unsaved or uncertain text in any retained task requires the user's
explicit view-close decision. Ordinary close freezes editing once that decision is made and
waits for observed STOPPED. The existing record inspector remains available via
the same tool's `--inspector` option. Both use the explicitly selected disposable
development profile; no production entry point or normal profile is changed.

## Qualification and remaining scope

Relevant requirements include REQ-09-01, REQ-19-01, REQ-30-04 and REQ-32-01/03/04;
WP-02/05/06/16 remain dependency-bound and incomplete. Narrow development tests
do not close B010/B013/B025/B113/B116 or any original acceptance obligation.
Attachment custody, actual interpretation/clarification, task activation/lifecycle,
qualified trusted time/approvals/resources, historical uncertain-write receipts,
unconfirmed editor restart durability, visible accessibility and installed/model
qualification remain required work. Selected cell counts and replay limits do not
bound full journal verification or native driver occupancy. Positive runtime/effect
owners remain CLOSED, Gate A OPEN, 128 original cases NOT_RUN and eight formal
gates NOT_EVALUATED. Full product completion remains unproven.

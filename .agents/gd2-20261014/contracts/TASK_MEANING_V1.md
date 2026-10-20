# Durable task interpretation proposals — v1

This owner-internal extension records unaccepted interpretations through the
existing authenticated native ingress and the same captured kernel/journal.
It is a step toward REQ-09-01 and REQ-11-01/02; full compilation, accepted
objectives, finite grants and the complete product remain required work.

## Exact capture and attribution

`task.meaning_propose` and `task.meaning_load` retain the original LocalMessage
envelope and TaskCommand type. Their exact-field command body uses the explicit
`ceta-task-command-v2` profile. Earlier task commands retain their v1 bytes and
behavior. A proposal supplies the full saved task-draft cell revision and the
observed prior meaning-cell revision, or explicit absence for its first version.
Neither a logical principal supplied in content nor a proposed authority field
registers an owner or grants permission.

All ten REQ-09-01 meaning fields are separate UTF-8 hex values: clarified
meaning, scope, exclusions, completion predicates, assumptions, unresolved
questions, standing instructions, requested authority, requested budgets and
supporting evidence. Each field is bounded at 16,384 decoded bytes and the
aggregate at 65,536. Objective and scope require supplied nonblank text; empty
other fields record no proposed content. Exact spelling, negations, quotes,
CRLF, NFD Unicode and NUL are preserved by the API. The Qt editor captures
`toPlainText()`, rather than claiming byte identity for earlier keystrokes.

The kernel captures immutable original instruction, saved title/draft, full
task basis revision, objective revision, native owner commitment, principal,
session, original command commitment, causal event and meaning generation.
Each proposal has state `UNACCEPTED`. Its ObservationEnvelope has epistemic
status `ATTRIBUTED`; the journal records submitted interpretation, not semantic
truth, human acceptance, a materiality finding, standing permission or budget.
Meaning content cannot change CREATED, issue a grant, move task_wire, or enable
an effect. The ten null meaning fields of the earlier draft snapshot remain
compatible until the separate acceptance/migration contract is implemented.

## Versions, freshness and atomicity

The existing task owner revalidates the exact message, actual native context,
stable owner, coherent task/draft/catalog cells and task event before use.
Meaning proposals occupy a generation-bearing `task-meaning` projection. A
single real SQLite transaction checks task/draft/catalog plus prior meaning
CAS, then appends the proposal's event/payload and changes only that meaning
cell. Every prior version remains in journal changes. Current-context checks
run before, inside the commit guard, after COMMIT and after the final read.
A denial after COMMIT preserves the committed state for reconciliation.

The result uses a separate `ceta-task-meaning-result-v1` profile and binds the
original message/command, exact proposal revision and current full task-draft
revision. Loading absent zero-generation meaning is `TASK_MEANING_ABSENT`;
tombstones do not become absence. `TASK_MEANING_STALE` retains the proposal
when its saved task basis differs from the currently observed draft. Draft
edits do not silently rewrite an earlier interpretation or make it current.
Unaccepted proposal revisions do not change the accepted objective: TR-01's
authenticated acceptance and finite kernel grant are still necessary.

## Native interaction and uncertainty

The task view opens a separate interpretation form displaying the immutable
original and all ten fields. It retains partial local interpretations in the
same per-task session cache. Writes require a saved, unchanged task basis.
Late replies update their captured task entry; newer interpretation edits
remain unsaved. Dirty loads retain local text for explicit revision selection.
Stored proposal status is visibly unaccepted or stale. A meaning read retains
the current task revision it actually observed;
it cannot label a proposal current by comparing only to an older cached task.
If that observed task revision differs from the loaded saved draft, the dialog
requires returning to the task and reloading its saved basis before another
proposal. Loaded and proposal-basis drafts are displayed separately.
Before an explicit revision choice, a read-only observation preview shows the
latest loaded proposal, its captured draft, all ten fields and the actual
observed task revision, or explicit proposal absence. It distinguishes this
observation from the selected editing baseline and preserves local text.
Invalid edits remain in
the dialog; returning with them requires an explicit discard choice. Stop and
Esc bypass text validation and freeze editors on STOPPING/STOPPED.

The controller retains uncertain meaning writes. Unrelated task reads cannot
clear them. A bound meaning load proving the exact original command can
reconcile that proposal write, including a later stale observation. Selecting
a newer observed meaning CAS explicitly retains the prior request/response
and unresolved history. Observed absence can be selected only for a pending
initial proposal, not a replacement. Selecting a raw task basis cannot settle
meaning or effect uncertainty. Retained reconciliation history is bounded
before a new write; unknown work is not automatically replayed.

## Remaining qualification

These are typed, attributed proposal and inspection paths. Actual model
interpretation, material clarification, source/correction handling,
ContextEnvelope construction, real template/token counting and immutable
prepared requests remain part of CMP-07/WP-06. Trusted acceptance, finite grant
issuance, time/approval/resource ownership and full task lifecycle remain
required. Historical uncertainty across controller restart, unconfirmed local
edit persistence, actual native occupancy, installed/accessibility, hardware,
independent and endurance qualification are separate open obligations.
Original B025/B027/B028 and all other original acceptance statuses are not
advanced by narrow development tests. No source adoption or formal gate is
ratified by this extension.

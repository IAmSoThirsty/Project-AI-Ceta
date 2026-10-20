# CETA native request preparation view — version 1

This development UI contract covers the existing TaskOperatorSession and WP-06
request compiler. R2 candidates remain unapplied until the root applies reviewed
hashes. This document does not qualify behavior, owner composition, model
execution, task acceptance, dispatch or any record schema.

## Composition and task custody

TaskView's Request preparation button opens PreparationView(session, parent)
with the same session. Existing draft/title editing, save/load/CAS, navigation,
Stop and main-window close retain their owners. The dialog captures one task ID.
An observed selection mismatch is latched until Return/reopen, including an
observed A -> B -> A. Captured result and observation stay visible; preparation
and revalidation are disabled. An entirely unobserved A -> B -> A between
callbacks has no public selection-generation witness and is not claimed covered.

Two additive read-only session observations support controls: context_available
is compiler is not None; context_busy is global _pending is not None or
_context_job is not None. The view uses public session observations only and the
existing begin methods retain their guards.

All nine PROFILES are available. Requested output tokens are1..1048576, with
initial value512. Prepare invokes begin_context_preview; freshness check invokes
begin_context_revalidation. Both require the captured selection, READY service,
no global pending work, a saved created task with revision, no dirty local task
and no unselected remote revision. Missing compiler disables preparation and is
visible as "Compiler unavailable in this build". The normal launcher supplies
no compiler; there is no fixture fallback. Production port composition and
exceptional QApplication-exit worker ownership remain separate unfinished work.

## Retained result, latest attempt and coherence

The retained CompilationResult displays its own kind, task CAS, objective
revision/generation, prepared commitment, actual input count and reason.
Retained result basis is also an inspection item. Latest local status/error,
dialog error and latest exposed native task-load request/response/revision are
separate items. A failed or uncertain attempt may leave an older result and an
older native observation. There is no public attempt-ID/time join proving that
the exposed observation came from the latest attempt.

PREVIEW is local status. It establishes no fresh state/clock validation,
semantic fidelity, consent, task acceptance or positive authority. Successful
revalidation reuses the same immutable result and exposes no separate public
owner/clock success receipt. Returning to PREVIEW alone does not establish
fresh revalidation or renew a deadline. Detailed limits are inspectable in
Preparation notes and Latest attempt details; labels give direct user actions.

CompilationResult.__post_init__ retains existing PREVIEW task/payload checks
and additionally requires selection == prepared.selection, interpretation ==
prepared.interpretation, sources == prepared.selection.sources, omissions ==
prepared.omissions and input_tokens == len(prepared.tokenization.token_ids).
Mismatch raises COMPILER_RESULT_PREVIEW_COHERENCE. These are value equalities,
including an actually zero-length token tuple/count, rather than truthiness.
The existing production producer supplies these values. No PreparedRequest
redesign, schema, public signature or dispatch permission is introduced;
non-PREVIEW result rules remain unchanged.

## Meaning and clarification

All sixteen FIELD_NAMES are listed. A missing optional field is Not supplied,
without invented status or attribution. An emitted UNRESOLVED/None retains its
actual status and says Unavailable (emitted None). Source IDs, mandatory flags,
status and exact value bytes remain inspectable.

Each supplied value row shows a readable snippet of at most160 initial bytes,
with byte start/exclusive-end/full count and an explicit more-bytes notice when
truncated. Clicking any field row selects its complete Meaning value: <name>
inspector item. Missing and emitted None items remain explicitly unavailable.

A clarification result shows its actual question as a readable preview of at
most1024 initial bytes. The label discloses bounds and full count. Clarification
question and Question: <index> retain complete exact bytes; reasons, material
flags and dependent task/source references remain inspectable. The question
preview represents the retained result, separately from latest local attempt.

Clarification directs Return to task, edit, save at its current revision, then
prepare again. This dialog has no answer editor, automatic adoption, accepted
commitment, IIMP correction persistence or task acceptance path.

## Exact pages and readable projections

Labels, tables and read-only editors use plain text; untrusted content does not
become HTML. ByteInspector retains original bytes. Each1024-byte page uses
16-byte rows with exact grammar:

absolute hexadecimal offset | space-separated hex bytes | escaped ASCII
byte-literal content (Python repr(chunk)[2:-1]).

Offsets use eight lowercase hex digits and are absolute. Page numbering is
1-based and every page shows start, exclusive end, full count and page/total.
CRLF, NUL, NFD and non-UTF8 remain inspectable in exact hex rows. Token pages
retain the128-ID bound and grammar:
absolute eight-digit decimal index | actual token ID.

A separate read-only readable_editor displays only the current byte page,
at most1024 bytes. It decodes UTF-8 with backslashreplace, without Unicode
normalization. NUL, tab, LF and CR are visible as literal \x00, \t, \n and \r.
Other ASCII controls and DEL use \xHH. Other Unicode Cc/Cf/Zl/Zp characters use
\uHHHH or \UHHHHHHHH. Ordinary code points, including decomposed sequences, are
retained. The label identifies page bounds and this readable projection.

A page boundary can split UTF-8. Invalid bytes and source text containing
escapes can look alike in this projection; the hex witness resolves them.
Readable text is not exactness proof or persisted as source. Tokens and
unavailable entries do not undergo byte decoding. Empty actual bytes remain
distinct from unavailable.

Immutable descriptors are rebuilt only on changed result/observation/attempt.
Unchanged item identity, key and page preserve both inspection documents,
cursor, selection and scroll. No full8MiB payload/source conversion or
1Mi-token list rendering occurs every50ms. Current byte/token pages, bounded
meaning snippets and bounded question preview are the text conversion surfaces.

Inspection includes captured original/saved input; retained original/latest/
title/snapshot; field values/attribution; material questions/reasons/task/source
refs; six source partitions and emitted source/version/mandatory/audit/coding/
material markers; selection/read-set/model/template/tokenizer/runtime/
reservation/deadline pins; quotations/omissions; actual model parts/payload;
actual tokenization/special-token flags where available; prepared clock/binding;
ContextEnvelope original/canonical bytes; and separate native observation.

Token overflow retains available payload/count. Assembly-byte overflow can
leave them unavailable, which remains explicit rather than becoming empty
bytes or zero. Tokenization/IDs are not fabricated from an input count.
Metadata projections remain distinct from exact original byte entries.

## Stop, modal lifetime and shared workers

Visible Stop and Esc invoke shared session.stop immediately, before profile,
number, selection or input validation. Neither clears worker/native custody.
Session cancellation, late results and observed worker termination remain
session responsibilities.

PreparationView.done retires its own timer on Return/close. TaskView's
_preparation wraps its read-only modal exec in try/finally: stop the child's
timer, schedule deleteLater, then refresh the parent on modal exit.

The editable meaning dialog has a separate document-custody rule. All Return,
close, reject, accept and direct done paths obtain the same explicit discard
decision for rejected text, defaulting to No. TaskView schedules its deletion
only after an authorized Return and completion of modal exec. An exceptional
exec or failed cleanup retains the actual dialog/documents by their captured
task ID, keeps their timer and task binding, and exposes them through Recover
interpretation draft. A valid proposal save and a deliberate invalid-text
discard remain distinct choices. Neither promotes a proposal to accepted intent.

Parent close considers these retained documents even when the shared session
contains no valid unsaved meaning. Stop still cancels immediately without text
validation, and rejected text remains inspectable until explicit disposal.
Recovery cannot replace rejected raw-task widget text or move interpretation
edits into another selected task. Authorized normal disposal is checked with
actual DeferredDelete destruction. These in-memory documents are not crash-
durable storage or proof of recovered text after interpreter/process exit.

Parent/session retain ongoing workers independently of dialog lifetime; no
Stop, observed worker exit, or effect reconciliation is inferred from Return.

## Qualification boundary

SPEC-09, SPEC-11, original master09/11/B4/C2/native inspectability32, POL-09 and
IIMP comparison/uncertainty/correction integration remain the obligations.
This UI implements inspection and the existing edit/save workflow. Standing
grants, obligations, authorized retrieval, production semantics, durable
correction/recovery and model/time/reservation/protected-resource owner
qualification are not established by this candidate.

The root must inspect exact candidates and independent tests, apply approved
hashes and execute focused Qt, task/meaning/Stop regressions and any separately
authorized disposable native intake. Writer syntax/AST checks are not execution
evidence. Original675-test evidence remains historical and does not cover R2.
Original128 cases stay NOT_RUN, eight formal gates NOT_EVALUATED, Gate A OPEN,
positive owners CLOSED, adoption UNRATIFIED and full goal ACTIVE.

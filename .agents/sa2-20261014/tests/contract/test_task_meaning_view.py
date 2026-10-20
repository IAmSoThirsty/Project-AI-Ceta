"""Manual interpretation custody through the real application and Qt views.

These tests use TaskOperatorSession, TaskDrafts, typed commands/results and a
real SQLite journal. The delivery controller and identity contexts are explicit
fixtures. They do not establish native authentication, process termination,
model interpretation, trusted acceptance, grants or original acceptance-case
completion. Exact CRLF/NFD/NUL bytes are checked at the application boundary;
Qt checks the text its document actually captures.

The fixture classes are not TestCases, and this module imports no other test
module. New application imports are delayed until helpers/tests execute.
"""
from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
SCOPE = "project:task-meaning-view-fixture"
SESSION = "session:task-meaning-view-fixture"
FIELDS = ("clarified_meaning", "scope", "exclusions", "completion_predicates",
          "assumptions", "unresolved_questions", "standing_instructions",
          "authority", "budgets", "evidence")


def supplied_meaning(tag="manual"):
    """Deliberately supplied prose, including requests that grant no authority."""
    return dict(zip(FIELDS, (
        tag + ": inspect the request; do not execute it.",
        tag + ": only the named task.",
        tag + ": exclude deletion and unrelated repositories.",
        tag + ": an inspected proposal is stored, still unaccepted.",
        tag + ": assumptions are supplied, not verified.",
        tag + ": which source takes precedence?",
        tag + ": keep quoted negations and Cafe\u0301.",
        tag + ": requested authority is not a grant.",
        tag + ": requested limit is 2; no budget is issued.",
        tag + ": \"do not delete\"\nEvidence is attributed.")))


class _OpaqueOwners:
    """Exact fixture context/message equality, explicitly no OS authentication."""
    def __init__(self):
        self.context, self.message = None, None

    def capture(self, message):
        self.context, self.message = object(), message
        return self.context

    def require_message(self, context, message):
        from ceta.contracts.kernel_transactions import require
        require(context is self.context and message == self.message,
                "FIXTURE_MEANING_MESSAGE_DENIED")

    def authenticate(self, context):
        from ceta.contracts.kernel_transactions import PeerIdentity, require
        require(context is self.context and self.message is not None,
                "FIXTURE_MEANING_CONTEXT_DENIED")
        return PeerIdentity("operator:task-meaning-view-fixture",
                            self.message.sender_session)

    def task_owner_binding(self, context):
        self.authenticate(context)
        return "sha256:" + "7" * 64


class _MeaningStore:
    def __init__(self):
        from ceta.contracts.wire import RecordCodec, strict_loads
        from ceta.contracts.store_transactions import STORE_PROFILE
        from ceta.store.journal import SqliteJournal
        from ceta.kernel.task_drafts import TaskDrafts
        self.root = ROOT / ".agents/fixtures/task-meaning-view-29" / uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=False)
        self.codec = RecordCodec(strict_loads(
            (ROOT / "contracts/schemas/records.schema.json").read_bytes()))
        self.owners = _OpaqueOwners()
        self.store = SqliteJournal(self.root, self.codec, (SCOPE,),
                                  create=True, profile=STORE_PROFILE)
        self.tasks = TaskDrafts(self.store, self.codec, self.owners)

    def message(self, wire, operation, *, session=SESSION, attempt=None):
        from ceta.contracts.local_ipc import encode_message, decode_message
        attempt = attempt or uuid.uuid4().hex
        return decode_message(encode_message(wire, self.codec,
            message_id="message:" + attempt, correlation_ref="attempt:" + attempt,
            sender_session=session, receiver_generation="f" * 64,
            operation=operation, issued_at_ms=1000, expires_at_ms=2000), self.codec)

    def execute(self, message):
        return self.tasks(message, self.owners.capture(message))

    def response(self, message, result):
        from ceta.contracts.local_results import encode_response, decode_response
        return decode_response(encode_response(message, result, self.codec),
                               message, self.codec)

    def draft_cell(self, task_id):
        from ceta.contracts.task_drafts import draft_key
        return self.store.snapshot((draft_key(SCOPE, task_id),))[0]

    def kernel_cell(self, task_id):
        from ceta.contracts.kernel_transactions import task_key
        return self.store.snapshot((task_key(SCOPE, task_id),))[0]

    def meaning_cell(self, task_id):
        from ceta.contracts.task_meaning import meaning_key
        return self.store.snapshot((meaning_key(SCOPE, task_id),))[0]

    def snapshot(self, task_id):
        from ceta.contracts.task_drafts import decode_snapshot
        return decode_snapshot(self.draft_cell(task_id).value_wire)

    def proposal(self, task_id):
        from ceta.contracts.task_meaning import decode_proposal
        return decode_proposal(self.meaning_cell(task_id).value_wire)

    def external_meaning(self, task_id, values):
        from ceta.contracts.task_drafts import command_wire
        from ceta.contracts.task_meaning import meaning_from_text
        cell = self.meaning_cell(task_id)
        prior = None if cell.generation == 0 else cell.revision
        wire = command_wire("meaning_propose", SCOPE,
            "task-command:" + uuid.uuid4().hex, task_id=task_id,
            expected_revision=self.draft_cell(task_id).revision,
            meaning_expected_revision=prior, meaning=meaning_from_text(values))
        return self.execute(self.message(wire, "task.meaning_propose",
                                         session="session:external-meaning-fixture"))

    def external_draft(self, task_id, draft):
        from ceta.contracts.task_drafts import command_wire, text_value
        wire = command_wire("save", SCOPE, "task-command:" + uuid.uuid4().hex,
            task_id=task_id, expected_revision=self.draft_cell(task_id).revision,
            title=text_value(self.snapshot(task_id)["title_hex"]), draft=draft)
        return self.execute(self.message(wire, "task.save"))

    def reopen(self):
        from ceta.contracts.store_transactions import STORE_PROFILE
        from ceta.store.journal import SqliteJournal
        from ceta.kernel.task_drafts import TaskDrafts
        self.store.close()
        self.store = SqliteJournal(self.root, self.codec, (SCOPE,),
                                  profile=STORE_PROFILE)
        self.owners = _OpaqueOwners()
        self.tasks = TaskDrafts(self.store, self.codec, self.owners)

    def close(self):
        self.store.close()


class _ControlledDelivery:
    """Held delivery over real storage; Stop state is a controlled observation."""
    def __init__(self, fixture, *, session=SESSION):
        self.fixture, self.session = fixture, session
        self.state, self.detail = "READY", "Controlled delivery; authority closed."
        self.pending, self.call = None, None
        self.sent, self.task_choices, self.meaning_choices = [], [], []
        self.observed_task, self.observed_meaning = None, None
        self.stop_calls = 0

    def begin_call(self, wire, operation):
        from ceta.contracts.kernel_transactions import require
        require(self.pending is None and self.state in {"READY", "RECOVERING"},
                "FIXTURE_MEANING_CALL_PENDING_OR_STOPPED")
        attempt = uuid.uuid4().hex
        message = self.fixture.message(wire, operation, session=self.session,
                                       attempt=attempt)
        self.pending = {"attempt": attempt, "request": message}
        self.sent.append(message)
        self.call = None
        self.state, self.detail = "ACTIVE", "Controlled delivery held."
        return attempt

    def complete(self):
        from ceta.contracts.task_drafts import validate_result
        from ceta.contracts.wire import ContractError
        if self.pending is None:
            raise AssertionError("No controlled meaning request to complete")
        pending, message = self.pending, self.pending["request"]
        try:
            result = self.fixture.execute(message)
        except ContractError as failure:
            result = failure
        response = self.fixture.response(message, result)
        self.call = {"attempt": pending["attempt"], "kind": response.kind,
                     "response": response}
        self.pending = None
        if response.task_result is not None:
            revision = validate_result(response.task_result, message.record,
                                       message.operation)
            if message.operation == "task.load":
                self.observed_task = (message.record.as_dict()["task_id"], revision)
            elif message.operation == "task.meaning_load":
                self.observed_meaning = (message.record.as_dict()["task_id"],
                    revision, response.task_result.current_task_revision)
        if self.state not in {"STOPPING", "STOPPED"}:
            self.state = "RECOVERING" if response.kind == "DENIED_RECONCILE" else "READY"
        self.detail = "Controlled bound response observed; authority closed."
        return response

    def acknowledge_task_reconciliation(self, task_id, revision):
        from ceta.contracts.kernel_transactions import require
        require(self.pending is None and self.observed_task == (task_id, revision),
                "FIXTURE_TASK_OBSERVATION_REQUIRED")
        self.task_choices.append((task_id, revision))
        self.state = "READY"

    def acknowledge_meaning_reconciliation(self, task_id, revision, task_revision):
        from ceta.contracts.kernel_transactions import require
        choice = (task_id, revision, task_revision)
        require(self.pending is None and self.observed_meaning == choice,
                "FIXTURE_MEANING_OBSERVATION_REQUIRED")
        self.meaning_choices.append(choice)
        self.state = "READY"

    def request_stop(self):
        self.stop_calls += 1
        self.state, self.detail = "STOPPING", "Controlled Stop; exit not observed."
        return self.poll()

    def finish_stop(self):
        self.state, self.detail = "STOPPED", "Fixture supplied a Stop observation."

    def poll(self):
        return {"state": self.state, "detail": self.detail, "authority": "CLOSED",
                "call": self.call, "pending_attempt":
                None if self.pending is None else self.pending["attempt"]}


class _MeaningHelpers:
    """A helper mixin only; it defines no discoverable test method."""
    def session(self, *, fixture=None, session_id=SESSION):
        from ceta.application.task_operator import TaskOperatorSession
        if fixture is None:
            fixture = _MeaningStore()
            self.fixtures.append(fixture)
        service = _ControlledDelivery(fixture, session=session_id)
        session = TaskOperatorSession(service, SCOPE)
        session.poll()
        return session, service, fixture

    def create(self, session, service, *, draft="Original instruction: do not delete."):
        session.set_title("Meaning fixture task")
        session.set_draft(draft)
        session.create()
        self.assertEqual(service.complete().kind, "TASK_SNAPSHOT")
        session.poll()
        self.assertFalse(session.dirty)
        return session.task_id

    def record(self, session, service, *, values=None):
        if values is not None:
            session.set_meaning_fields(values)
        session.propose_meaning()
        response = service.complete()
        self.assertEqual(response.kind, "TASK_MEANING_PROPOSAL")
        session.poll()
        return response

    def load_meaning(self, session, service):
        session.load_meaning()
        response = service.complete()
        session.poll()
        return response

    def fails(self, code, operation):
        from ceta.contracts.wire import ContractError
        with self.assertRaises(ContractError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)


class TaskMeaningSessionTests(_MeaningHelpers, unittest.TestCase):
    def setUp(self):
        self.fixtures = []

    def tearDown(self):
        for fixture in reversed(self.fixtures):
            fixture.close()

    def test_manual_ten_field_proposal_preserves_bytes_and_does_not_accept_task(self):
        from ceta.contracts.task_meaning import MEANING_FIELDS
        session, service, fixture = self.session()
        original = 'Do not delete.\r\nCafe\u0301: "quoted scope".\x00No inference.\r\n'
        task_id = self.create(session, service, draft=original)
        before_draft, before_kernel = fixture.draft_cell(task_id), fixture.kernel_cell(task_id)
        values = {name: name + ": Cafe\u0301\r\n\"do not\"\x00" for name in FIELDS}
        self.assertEqual(tuple(MEANING_FIELDS), FIELDS)
        response = self.record(session, service, values=values)
        proposal = fixture.proposal(task_id)
        self.assertEqual(proposal["state"], "UNACCEPTED")
        self.assertEqual(proposal["basis_revision"], before_draft.revision)
        for name in FIELDS:
            with self.subTest(field=name):
                self.assertEqual(bytes.fromhex(proposal["meaning"][name]),
                                 values[name].encode("utf8"))
        self.assertEqual(bytes.fromhex(proposal["instruction_hex"]), original.encode("utf8"))
        self.assertEqual(bytes.fromhex(proposal["draft_hex"]), original.encode("utf8"))
        self.assertEqual(session.original_instruction, original)
        self.assertEqual(session.saved_draft, original)
        self.assertEqual(fixture.draft_cell(task_id), before_draft)
        self.assertEqual(fixture.kernel_cell(task_id), before_kernel)
        self.assertEqual(fixture.snapshot(task_id)["state"], "CREATED")
        self.assertEqual(fixture.snapshot(task_id)["meaning"], dict.fromkeys(FIELDS))
        self.assertEqual(response.task_result.current_task_revision, session.revision)
        self.assertEqual(session.meaning_status, "PROPOSED_UNACCEPTED")
        self.assertFalse(session.has_unconfirmed)
        self.assertTrue(all(message.operation in {"task.create", "task.meaning_propose"}
                            for message in service.sent))

    def test_field_byte_limits_total_boundary_and_invalid_encoding_are_atomic(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        boundary = dict.fromkeys(FIELDS, "")
        for name in FIELDS[:4]:
            boundary[name] = "\u00e9" * 8192
        self.record(session, service, values=boundary)
        self.assertEqual(sum(len(bytes.fromhex(v)) for v in
                             fixture.proposal(task_id)["meaning"].values()), 65536)
        generation = session._entry()["meaning_edit_generation"]
        sent_count = len(service.sent)
        invalid_forms = (
            ("TASK_TEXT_SIZE", dict(boundary, evidence="\u00e9" * 8193)),
            ("MEANING_TOTAL_SIZE", dict(boundary, assumptions="x")),
            ("TASK_TEXT_ENCODING", dict(boundary, evidence="\ud800")),
        )
        for code, invalid in invalid_forms:
            with self.subTest(code=code):
                self.fails(code, lambda: session.set_meaning_fields(invalid))
                self.assertEqual(session.meaning_text, boundary)
                self.assertEqual(session._entry()["meaning_edit_generation"], generation)
                self.assertEqual(len(service.sent), sent_count)
                self.assertEqual(fixture.meaning_cell(task_id).generation, 1)

    def test_partial_meaning_is_retained_but_missing_objective_scope_cannot_dispatch(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        partial = dict.fromkeys(FIELDS, "")
        partial["unresolved_questions"] = "What objective and scope were intended?"
        session.set_meaning_fields(partial)
        sent_count = len(service.sent)
        self.fails("MEANING_OBJECTIVE_SCOPE_REQUIRED", session.propose_meaning)
        self.assertEqual(session.meaning_text, partial)
        self.assertEqual(len(service.sent), sent_count)
        self.assertEqual(fixture.meaning_cell(task_id).generation, 0)
        session.set_meaning_field("clarified_meaning", "Supplied objective")
        self.fails("MEANING_OBJECTIVE_SCOPE_REQUIRED", session.propose_meaning)
        session.set_meaning_field("scope", "Supplied scope")
        session.set_draft("Unsaved draft; original remains separate.")
        self.fails("MEANING_SAVED_TASK_REQUIRED", session.propose_meaning)
        self.assertEqual(session.saved_draft, session.original_instruction)
        self.assertEqual(len(service.sent), sent_count)
        self.assertTrue(session.has_unconfirmed)

    def test_dirty_load_retains_text_and_requires_explicit_observed_meaning_cas(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        self.record(session, service, values=supplied_meaning("first"))
        old_revision = session.meaning_revision
        local = dict(session.meaning_text, exclusions="Local exclusion; do not replace.")
        session.set_meaning_fields(local)
        fixture.external_meaning(task_id, supplied_meaning("other session"))
        current = fixture.meaning_cell(task_id).revision
        response = self.load_meaning(session, service)
        self.assertEqual(response.kind, "TASK_MEANING_PROPOSAL")
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(session.meaning_revision, old_revision)
        self.assertTrue(session.has_meaning_remote)
        self.assertEqual(service.meaning_choices, [])
        self.fails("MEANING_REMOTE_SELECTION_REQUIRED", session.propose_meaning)
        session.adopt_current_meaning_revision()
        self.assertEqual(service.meaning_choices, [(task_id, current, session.revision)])
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(session.meaning_revision, current)
        session.propose_meaning()
        self.assertEqual(service.sent[-1].record.as_dict()["meaning_expected_revision"], current)
        service.complete()
        session.poll()
        self.assertEqual(fixture.meaning_cell(task_id).generation, 3)
        self.assertEqual(bytes.fromhex(fixture.proposal(task_id)["meaning"]["exclusions"]),
                         local["exclusions"].encode("utf8"))

    def test_observed_absence_is_an_explicit_first_proposal_choice(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        values = supplied_meaning("local before absence")
        session.set_meaning_fields(values)
        self.assertEqual(self.load_meaning(session, service).kind, "TASK_MEANING_ABSENT")
        self.assertTrue(session.has_meaning_remote)
        self.assertEqual(session.meaning_text, values)
        self.fails("MEANING_REMOTE_SELECTION_REQUIRED", session.propose_meaning)
        session.adopt_current_meaning_revision()
        self.assertEqual(service.meaning_choices, [(task_id, None, session.revision)])
        self.record(session, service)
        self.assertEqual(fixture.meaning_cell(task_id).generation, 1)

    def test_late_proposal_acknowledges_capture_without_erasing_newer_edits(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        captured = supplied_meaning("captured")
        session.set_meaning_fields(captured)
        session.propose_meaning()
        newer = dict(captured, scope="New unsaved scope", evidence="New unsaved evidence")
        session.set_meaning_fields(newer)
        self.assertTrue(session.has_unconfirmed)
        service.complete()
        session.poll()
        acknowledged = fixture.meaning_cell(task_id).revision
        self.assertEqual(session.meaning_text, newer)
        self.assertEqual(session.meaning_revision, acknowledged)
        self.assertEqual(session.meaning_status, "UNSAVED")
        self.assertEqual(bytes.fromhex(fixture.proposal(task_id)["meaning"]["scope"]),
                         captured["scope"].encode("utf8"))
        session.poll()
        self.assertEqual(fixture.meaning_cell(task_id).generation, 1)
        session.propose_meaning()
        self.assertEqual(service.sent[-1].record.as_dict()["meaning_expected_revision"], acknowledged)
        service.complete()
        session.poll()
        self.assertEqual(fixture.meaning_cell(task_id).generation, 2)
        self.assertEqual(session.meaning_text, newer)
        self.assertFalse(session.meaning_dirty)

    def test_late_result_updates_captured_task_without_mutating_selected_task(self):
        session, service, fixture = self.session()
        first = self.create(session, service, draft="Original task A.")
        session.new_task()
        second = self.create(session, service, draft="Original task B.")
        second_values = supplied_meaning("B local")
        session.set_meaning_fields(second_values)
        session.select_task(first)
        first_values = supplied_meaning("A captured")
        session.set_meaning_fields(first_values)
        session.propose_meaning()
        session.set_meaning_field("evidence", "A newer evidence")
        session.select_task(second)
        service.complete()
        session.poll()
        self.assertEqual(session.task_id, second)
        self.assertEqual(session.meaning_text, second_values)
        self.assertIsNone(session.meaning_proposal)
        self.assertEqual(session.result_text, "")
        self.assertEqual(fixture.meaning_cell(second).generation, 0)
        session.select_task(first)
        self.assertEqual(session.meaning_revision, fixture.meaning_cell(first).revision)
        self.assertEqual(session.meaning_text["evidence"], "A newer evidence")
        self.assertEqual(session.meaning_status, "UNSAVED")

    def test_edit_during_clean_load_requires_revision_choice_and_keeps_text(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        self.record(session, service, values=supplied_meaning("stored"))
        old_revision = session.meaning_revision
        fixture.external_meaning(task_id, supplied_meaning("new stored"))
        session.load_meaning()
        session.set_meaning_field("assumptions", "Edited while load was held.")
        local = session.meaning_text
        service.complete()
        session.poll()
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(session.meaning_revision, old_revision)
        self.assertTrue(session.has_meaning_remote)
        self.assertEqual(service.meaning_choices, [])

    def test_saved_local_and_stale_proposal_drafts_remain_distinct(self):
        session, service, fixture = self.session()
        original = "Original instruction.\r\nNo deletion."
        task_id = self.create(session, service, draft=original)
        self.record(session, service, values=supplied_meaning("old basis"))
        old_proposal = fixture.meaning_cell(task_id)
        session.set_draft("New unsaved draft.")
        self.assertEqual(session.saved_draft, original)
        self.assertEqual(session.meaning_status, "LOCAL_DRAFT_CHANGED")
        self.fails("MEANING_SAVED_TASK_REQUIRED", session.propose_meaning)
        session.save()
        service.complete()
        session.poll()
        self.assertEqual(session.saved_draft, "New unsaved draft.")
        self.assertEqual(session.original_instruction, original)
        self.assertEqual(session.meaning_status, "STALE")
        self.assertEqual(self.load_meaning(session, service).kind, "TASK_MEANING_STALE")
        self.assertEqual(fixture.meaning_cell(task_id), old_proposal)
        self.assertEqual(bytes.fromhex(session.meaning_proposal["draft_hex"]),
                         original.encode("utf8"))
        new_basis = session.revision
        self.record(session, service)
        self.assertEqual(session.meaning_proposal["basis_revision"], new_basis)
        self.assertEqual(bytes.fromhex(session.meaning_proposal["draft_hex"]), b"New unsaved draft.")
        self.assertEqual(fixture.snapshot(task_id)["state"], "CREATED")

    def test_changed_remote_task_basis_requires_task_read_before_meaning_adoption(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        self.record(session, service, values=supplied_meaning("old"))
        session.set_meaning_field("scope", "Retain this local scope.")
        local = session.meaning_text
        before_meaning = fixture.meaning_cell(task_id)
        fixture.external_draft(task_id, "Externally saved current draft.")
        session.propose_meaning()
        response = service.complete()
        session.poll()
        self.assertEqual(response.kind, "DENIED_RECONCILE")
        self.assertEqual(response.error_code, "MEANING_TASK_REVISION_CONFLICT")
        self.assertEqual(fixture.meaning_cell(task_id), before_meaning)
        self.assertEqual(session.meaning_status, "CONFLICT")
        self.assertEqual(session.meaning_text, local)
        self.load_meaning(session, service)
        self.fails("MEANING_TASK_BASIS_LOAD_REQUIRED", session.adopt_current_meaning_revision)
        self.assertEqual(service.meaning_choices, [])
        session.load(task_id)
        service.complete()
        session.poll()
        self.assertEqual(session.saved_draft, "Externally saved current draft.")
        session.adopt_current_meaning_revision()
        self.assertEqual(session.meaning_text, local)
        self.record(session, service)
        self.assertEqual(session.meaning_proposal["basis_revision"], session.revision)
        self.assertEqual(session.saved_draft, "Externally saved current draft.")

    def test_meaning_only_load_observes_stale_basis_without_false_current_status(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service, draft="Loaded task basis A.")
        self.record(session, service, values=supplied_meaning("proposal on A"))
        cached_revision = session.revision
        fixture.external_draft(task_id, "Current stored task basis B.")
        current_revision = fixture.draft_cell(task_id).revision
        response = self.load_meaning(session, service)
        self.assertEqual(response.kind, "TASK_MEANING_STALE")
        self.assertEqual(response.task_result.current_task_revision, current_revision)
        self.assertEqual(session.revision, cached_revision)
        self.assertEqual(session.saved_draft, "Loaded task basis A.")
        self.assertEqual(session.meaning_status, "STALE")
        self.assertFalse(session.meaning_basis_current)
        count = len(service.sent)
        self.fails("MEANING_TASK_BASIS_LOAD_REQUIRED", session.propose_meaning)
        self.assertEqual(len(service.sent), count)

    def test_current_meaning_with_older_raw_cache_requires_task_refresh_before_write(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service, draft="Loaded task basis A.")
        self.record(session, service, values=supplied_meaning("proposal on A"))
        cached_revision = session.revision
        fixture.external_draft(task_id, "Current stored task basis B.")
        newer = supplied_meaning("proposal on B")
        fixture.external_meaning(task_id, newer)
        response = self.load_meaning(session, service)
        self.assertEqual(response.kind, "TASK_MEANING_PROPOSAL")
        self.assertEqual(session.meaning_text, newer)
        self.assertEqual(session.revision, cached_revision)
        self.assertEqual(session.meaning_status, "TASK_REFRESH_REQUIRED")
        self.assertFalse(session.meaning_basis_current)
        count = len(service.sent)
        self.fails("MEANING_TASK_BASIS_LOAD_REQUIRED", session.propose_meaning)
        self.assertEqual(len(service.sent), count)
        session.load(task_id)
        service.complete()
        session.poll()
        self.assertEqual(session.saved_draft, "Current stored task basis B.")
        self.assertTrue(session.meaning_basis_current)
        self.assertEqual(session.meaning_status, "PROPOSED_UNACCEPTED")
        self.assertEqual(session.meaning_text, newer)

    def test_meaning_only_placeholder_and_hidden_edits_count_as_unconfirmed(self):
        session, _, _ = self.session()
        first = session.task_id
        session.set_meaning_field("unresolved_questions", "Retain this question.")
        second = session.new_task()
        self.assertNotEqual(first, second)
        self.assertIn(first, session.local_task_ids)
        self.assertFalse(session.dirty)
        self.assertFalse(session.meaning_dirty)
        self.assertTrue(session.has_unconfirmed)
        session.select_task(first)
        self.assertEqual(session.meaning_text["unresolved_questions"], "Retain this question.")

    def test_stored_proposal_reopens_in_fresh_application_session_without_acceptance(self):
        session, service, fixture = self.session()
        original = "Original\r\nCafe\u0301\x00Do not delete."
        task_id = self.create(session, service, draft=original)
        values = supplied_meaning("durable")
        values["evidence"] = "NFD Cafe\u0301\r\nNUL\x00Quotation: \"do not\""
        self.record(session, service, values=values)
        stored_wire = fixture.meaning_cell(task_id).value_wire
        fixture.reopen()
        reopened, delivery, _ = self.session(fixture=fixture,
                                              session_id="session:meaning-reopened-fixture")
        reopened.load(task_id)
        delivery.complete()
        reopened.poll()
        self.load_meaning(reopened, delivery)
        self.assertEqual(reopened.original_instruction, original)
        self.assertEqual(reopened.saved_draft, original)
        self.assertEqual(reopened.meaning_text, values)
        self.assertEqual(fixture.meaning_cell(task_id).value_wire, stored_wire)
        self.assertEqual(reopened.meaning_status, "PROPOSED_UNACCEPTED")
        self.assertFalse(reopened.has_unconfirmed)
        self.assertEqual(fixture.snapshot(task_id)["state"], "CREATED")


    def test_dirty_load_exposes_latest_meaning_observation_without_selecting_it(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service, draft="Original and selected basis A.")
        self.record(session, service, values=supplied_meaning("selected A"))
        selected, selected_revision = session.meaning_proposal, session.meaning_revision
        cached_task_revision = session.revision
        local = supplied_meaning("retained local edits")
        session.set_meaning_fields(local)
        fixture.external_draft(task_id, "Observed proposal basis B.")
        latest = supplied_meaning("latest external proposal")
        fixture.external_meaning(task_id, latest)
        proposal = fixture.proposal(task_id)
        revision = fixture.meaning_cell(task_id).revision
        current_task = fixture.draft_cell(task_id).revision
        self.assertEqual(self.load_meaning(session, service).kind, "TASK_MEANING_PROPOSAL")
        self.assertEqual(session.meaning_observation, (proposal, revision, current_task))
        self.assertEqual(session.meaning_proposal, selected)
        self.assertEqual(session.meaning_revision, selected_revision)
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(session.revision, cached_task_revision)
        self.assertEqual(service.meaning_choices, [])
        fixture.external_draft(task_id, "Still newer saved task basis C.")
        changed_task = fixture.draft_cell(task_id).revision
        self.assertEqual(self.load_meaning(session, service).kind, "TASK_MEANING_STALE")
        self.assertEqual(session.meaning_observation, (proposal, revision, changed_task))
        self.assertEqual(session.meaning_proposal, selected)
        self.assertEqual(session.meaning_revision, selected_revision)
        self.assertEqual(session.meaning_text, local)
        self.fails("MEANING_TASK_BASIS_LOAD_REQUIRED", session.adopt_current_meaning_revision)
        session.load(task_id)
        service.complete()
        session.poll()
        session.adopt_current_meaning_revision()
        self.assertIsNone(session.meaning_observation)
        self.assertEqual(service.meaning_choices, [(task_id, revision, changed_task)])
        self.assertEqual(session.meaning_proposal, proposal)
        self.assertEqual(session.meaning_revision, revision)
        self.assertEqual(session.meaning_text, local)
        self.assertTrue(session.meaning_dirty)
        self.assertEqual(fixture.meaning_cell(task_id).generation, 2)

    def test_absent_meaning_observation_is_visible_until_explicit_revision_choice(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        local = supplied_meaning("local before explicit absence")
        session.set_meaning_fields(local)
        current_task = session.revision
        self.assertEqual(self.load_meaning(session, service).kind, "TASK_MEANING_ABSENT")
        self.assertEqual(session.meaning_observation, (None, None, current_task))
        self.assertIsNone(session.meaning_proposal)
        self.assertIsNone(session.meaning_revision)
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(service.meaning_choices, [])
        session.adopt_current_meaning_revision()
        self.assertIsNone(session.meaning_observation)
        self.assertEqual(service.meaning_choices, [(task_id, None, current_task)])
        self.assertEqual(session.meaning_text, local)
        self.assertTrue(session.meaning_dirty)
        self.assertEqual(fixture.meaning_cell(task_id).generation, 0)


class TaskMeaningViewTests(_MeaningHelpers, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        print("TaskMeaningViewTests Qt platform: " + cls.app.platformName())

    def setUp(self):
        self.fixtures, self.windows, self.services = [], [], []

    def tearDown(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QDialog, QMessageBox
        for service in self.services:
            service.finish_stop()
        for window in reversed(self.windows):
            window._session.poll()
            window.poll_timer.stop()
            with patch.object(QMessageBox, "question",
                              return_value=QMessageBox.StandardButton.Yes):
                if isinstance(window, QDialog):
                    window.done(QDialog.DialogCode.Rejected)
                else:
                    for child in tuple(window._meaning_views.values()):
                        child.reject()
                    with patch.object(QMessageBox, "question",
                                      return_value=QMessageBox.StandardButton.Close):
                        window.close()
            window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        for fixture in reversed(self.fixtures):
            fixture.close()

    def view(self, *, session=None, service=None):
        from ceta.desktop.meaning_view import MeaningView
        if session is None:
            session, service, fixture = self.session()
            self.create(session, service)
        else:
            fixture = service.fixture
        if service not in self.services:
            self.services.append(service)
        view = MeaningView(session)
        self.windows.append(view)
        view.poll_timer.stop()
        view.show()
        self.app.processEvents()
        return view, session, service, fixture

    def task_window(self, session, service):
        from ceta.desktop.task_view import TaskView
        if service not in self.services:
            self.services.append(service)
        window = TaskView(session)
        self.windows.append(window)
        window.poll_timer.stop()
        window.show()
        self.app.processEvents()
        return window

    def click(self, widget):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def poll(self, view):
        view.poll_timer.timeout.emit()
        self.app.processEvents()

    def fill(self, view, values):
        # One form change delivers all ten current document values atomically.
        for name, value in values.items():
            editor = view.editors[name]
            blocked = editor.blockSignals(True)
            try:
                editor.setPlainText(value)
            finally:
                editor.blockSignals(blocked)
        view.editors["evidence"].textChanged.emit()
        self.app.processEvents()

    def complete_editor_custody(self, session, service, *views):
        """Execute only explicitly held recovery writes over the real journal."""
        fixture = service.fixture
        before = {task_id: (fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                  fixture.meaning_cell(task_id)) for task_id in session.local_task_ids
                  if fixture.draft_cell(task_id).generation > 0}
        results = []
        # A reference capture may use the protocol maximum of 128 bounded
        # chunks; every response remains an independently authenticated
        # staging/retained result.
        for _ in range(132):
            if session._pending is None:
                session.poll()
            if session._pending is None:
                break
            self.assertIsNotNone(service.pending)
            request = service.pending["request"]
            self.assertIn(request.operation, {"task.editor_retain", "task.editor_discard"},
                          "A recovery helper must not silently finish another operation")
            response = service.complete()
            expected = ({"TASK_EDITOR_STAGING", "TASK_EDITOR_RETAINED"}
                        if request.operation == "task.editor_retain" else {"TASK_EDITOR_DISCARDED"})
            self.assertIn(response.kind, expected)
            results.append((request, response))
            session.poll()
            for view in views:
                view._poll()
            for task_id, cells in before.items():
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                                  fixture.meaning_cell(task_id)), cells)
        else:
            self.fail("Recovery captures did not settle within the bounded fixture loop")
        self.assertIsNone(session._pending)
        self.assertIsNone(service.pending)
        return results

    def assert_raw_editor_recovery(self, view, session, fixture):
        from ceta.contracts.editor_recovery import decode_editor_snapshot, recovery_key
        from ceta.contracts.wire import canonical_bytes
        task_id = view._task_id
        cell = fixture.store.snapshot((recovery_key(SCOPE, task_id),))[0]
        value = decode_editor_snapshot(cell.value_wire)
        self.assertEqual(value["state"], "RETAINED")
        self.assertEqual(canonical_bytes(session.editor_recovery_snapshot(task_id)), cell.value_wire)
        self.assertEqual(value["payload"]["basis_revision"], fixture.draft_cell(task_id).revision)
        for name, editor in view.editors.items():
            cursor, document = editor.textCursor(), editor.document()
            observed = value["payload"]["documents"][name]
            self.assertEqual(observed["utf16le_hex"], document.toRawText().encode("utf-16-le", errors="surrogatepass").hex())
            self.assertEqual(observed["document_revision"], document.revision())
            self.assertEqual((observed["cursor_position"], observed["anchor_position"]),
                             (cursor.position(), cursor.anchor()))
            self.assertTrue(observed["document_id"].startswith("editor-document:"))
        self.assertIn(cell.value_wire, [row[0] for row in fixture.store._connection.execute(
            "SELECT value_wire FROM store_changes ORDER BY commit_sequence,change_index")])
        return cell.value_wire

    def interrupted_interpretation(self, window, values, *, error=RuntimeError, poll_interval_ms=None):
        """Inject only the modal failure; keep the real Qt documents/timer."""
        from ceta.desktop.meaning_view import MeaningView
        captured = {}

        def fail_after_edit(view):
            captured["view"] = view
            captured["timer_before"] = view.poll_timer.isActive()
            if poll_interval_ms is not None:
                # Keep a real active Qt timer while controlling when this one
                # queue-only Stop fixture may submit its first recovery write.
                view.poll_timer.setInterval(poll_interval_ms)
            self.fill(view, values)
            raise error("controlled interpretation exec failure")

        with patch.object(MeaningView, "exec", new=fail_after_edit):
            if issubclass(error, Exception):
                window._meaning()
            else:
                with self.assertRaises(error): window._meaning()
        self.assertTrue(captured["timer_before"])
        self.assertEqual(captured["view"]._text_error, "TASK_TEXT_SIZE")
        return captured["view"]

    def flush_deferred_deletes(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_form_exposes_original_saved_basis_and_all_ten_separate_fields(self):
        view, session, service, fixture = self.view()
        original = session.original_instruction
        session.set_draft("A newer local draft has not been saved.")
        self.poll(view)
        self.assertEqual(tuple(view.editors), FIELDS)
        self.assertTrue(view.original_editor.isReadOnly())
        self.assertTrue(view.basis_editor.isReadOnly())
        self.assertTrue(view.proposal_basis_editor.isReadOnly())
        self.assertEqual(view.original_editor.toPlainText(), original)
        self.assertEqual(view.basis_editor.toPlainText(), original)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), "")
        self.assertEqual(session.draft, "A newer local draft has not been saved.")
        self.assertFalse(view.propose_button.isEnabled())
        self.assertTrue(view.stop_button.isEnabled())
        self.assertIn("proposal", view.propose_button.text().lower())
        self.assertEqual(fixture.meaning_cell(session.task_id).generation, 0)
        self.assertEqual(len(service.sent), 1)

    def test_record_button_persists_supplied_form_text_as_unaccepted(self):
        view, session, service, fixture = self.view()
        values = supplied_meaning("Qt supplied")
        self.fill(view, values)
        captured = {name: editor.toPlainText() for name, editor in view.editors.items()}
        self.assertEqual(session.meaning_text, captured)
        self.click(view.propose_button)
        self.assertEqual(service.sent[-1].operation, "task.meaning_propose")
        self.assertFalse(view.propose_button.isEnabled())
        self.assertTrue(view.stop_button.isEnabled())
        service.complete()
        self.poll(view)
        self.assertEqual(view.status_label.text(), "PROPOSED_UNACCEPTED")
        self.assertEqual(view.proposal_basis_editor.toPlainText(), session.saved_draft)
        for name in FIELDS:
            with self.subTest(field=name):
                self.assertEqual(bytes.fromhex(fixture.proposal(session.task_id)["meaning"][name]),
                                 captured[name].encode("utf8"))
        self.assertEqual(fixture.snapshot(session.task_id)["state"], "CREATED")
        self.assertEqual(fixture.snapshot(session.task_id)["meaning"], dict.fromkeys(FIELDS))

    def test_invalid_last_field_preserves_whole_prior_form_until_atomic_repair(self):
        view, session, service, fixture = self.view()
        task_id = session.task_id
        original_cells = (fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id))
        retained = supplied_meaning("last retained")
        self.fill(view, retained)
        prior_generation = session._entry()["meaning_edit_generation"]
        changed = supplied_meaning("new visible form")
        changed["evidence"] = "\u00e9" * 8193
        self.fill(view, changed)
        self.assertEqual(session.meaning_text, retained)
        self.assertEqual(session._entry()["meaning_edit_generation"], prior_generation)
        self.assertEqual(view.editors["scope"].toPlainText(), changed["scope"])
        self.assertEqual(view.editors["evidence"].toPlainText(), changed["evidence"])
        self.assertIn("TASK_TEXT_SIZE", view.detail_label.text())
        self.assertFalse(view.propose_button.isEnabled())
        self.assertFalse(view.load_button.isEnabled())
        self.poll(view)
        self.assertEqual(view.editors["evidence"].toPlainText(), changed["evidence"])
        self.assertEqual([message.operation for message in service.sent], ["task.create", "task.editor_retain"])
        self.assertEqual(session.editor_recovery_status(), "SAVING")
        self.assertIsNone(session.editor_recovery_snapshot())
        self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)), original_cells)
        changed["evidence"] = "Repaired evidence."
        view.editors["evidence"].setPlainText(changed["evidence"])
        self.app.processEvents()
        self.assertEqual(session.meaning_text, changed)
        self.assertFalse(view.propose_button.isEnabled(), "The held raw recovery write still owns the single writer")
        results = self.complete_editor_custody(session, service, view)
        self.assertEqual([request.operation for request, _ in results], ["task.editor_retain", "task.editor_retain"])
        self.assertEqual([message.operation for message in service.sent],
                         ["task.create", "task.editor_retain", "task.editor_retain"])
        self.assertEqual(session.editor_recovery_status(), "RETAINED")
        self.assert_raw_editor_recovery(view, session, fixture)
        self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)), original_cells)
        self.assertTrue(view.propose_button.isEnabled())
        self.assertTrue(view.load_button.isEnabled())

    def test_older_editor_result_keeps_newer_oversize_custody_and_stages_it_durably(self):
        from ceta.contracts.editor_recovery import EDITOR_REFERENCE_PROFILE, decode_editor_payload
        from ceta.contracts.wire import canonical_bytes
        for held_operation in ("task.editor_retain", "task.editor_load"):
            with self.subTest(held_operation=held_operation):
                view, session, service, fixture = self.view()
                task_id = session.task_id
                accepted_cells = (fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                                  fixture.meaning_cell(task_id))
                baseline = dict(supplied_meaning("bounded rejected"), evidence="x" * 16385)
                self.fill(view, baseline)
                self.poll(view)
                self.assertEqual(session.editor_recovery_status(), "SAVING")
                bounded_payload = session.editor_local_payload()
                if held_operation == "task.editor_load":
                    self.complete_editor_custody(session, service, view)
                    self.assert_raw_editor_recovery(view, session, fixture)
                    session.load_editor_recovery()
                self.assertEqual(service.pending["request"].operation, held_operation)
                pending = session._pending
                prior_position = fixture.store.store_position()
                view.editors["evidence"].setPlainText("NEWEST RAW \u00a0\U0001f642\u2028\u2029" + "z" * 65537)
                actual = view.editors["evidence"].document().toRawText().encode("utf-16-le", errors="surrogatepass")
                self.assertGreater(len(actual), 131072)
                local = session.editor_local_documents()
                self.assertEqual(local["documents"]["evidence"]["utf16le_bytes"], actual)
                self.assertGreater(session._entry()["editor_capture_generation"], pending["editor_capture_generation"])
                newer_payload = decode_editor_payload(session.editor_local_payload())
                self.assertEqual(newer_payload["profile"], EDITOR_REFERENCE_PROFILE)
                self.assertNotEqual(session.editor_local_payload(), bounded_payload)
                self.assertIsNone(session.editor_recovery_error())
                response = service.complete()
                self.assertEqual(response.kind, "TASK_EDITOR_RETAINED")
                self.poll(view)
                older = session.editor_recovery_snapshot()
                self.assertEqual(older["state"], "RETAINED")
                self.assertEqual(canonical_bytes(older["payload"]), bounded_payload)
                self.assertEqual(session.editor_local_documents()["documents"]["evidence"]["utf16le_bytes"], actual)
                self.assertEqual(view.editors["evidence"].document().toRawText().encode("utf-16-le", errors="surrogatepass"), actual)
                self.assertFalse(view.propose_button.isEnabled()); self.assertFalse(view.return_authorized)
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)), accepted_cells)
                self.assertEqual(fixture.store.store_position().next_commit,
                    prior_position.next_commit + (1 if held_operation == "task.editor_retain" else 0))
                # A retain reply can continue the newer upload immediately. A
                # read reply exposes the old recovery first, so an explicit
                # retry is required before the newer capture is staged.
                if held_operation == "task.editor_load":
                    self.assertEqual(session.editor_recovery_status(), "CONFLICT")
                    self.assertEqual(session.editor_recovery_error(), "EDITOR_LOCAL_AND_STORED_DIFFER")
                    session.retry_editor_recovery()
                self.assertEqual(service.pending["request"].operation, "task.editor_retain")
                results = self.complete_editor_custody(session, service, view)
                self.assertTrue(results)
                self.assertTrue(all(request.operation == "task.editor_retain" for request, _ in results))
                self.assertTrue(all(request.record.as_dict()["editor_chunk_hex"] is not None
                                    for request, _ in results))
                retained = session.editor_recovery_snapshot()
                self.assertEqual(retained["state"], "RETAINED")
                self.assertEqual(retained["payload"]["profile"], EDITOR_REFERENCE_PROFILE)
                self.assertEqual(retained["payload"]["capture_commitment"], newer_payload["capture_commitment"])
                self.assertEqual(session.editor_recovery_status(), "RETAINED")
                self.assertEqual(session.editor_local_documents()["documents"]["evidence"]["utf16le_bytes"], actual)
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)),
                                 accepted_cells)

    def test_aggregate_size_error_retains_documents_without_partial_session_write(self):
        view, session, service, _ = self.view()
        retained = supplied_meaning("retained before total overflow")
        self.fill(view, retained)
        oversized = dict.fromkeys(FIELDS, "")
        for name in FIELDS[:4]:
            oversized[name] = "x" * 16384
        oversized["evidence"] = "x"
        self.fill(view, oversized)
        self.assertEqual(session.meaning_text, retained)
        self.assertIn("MEANING_TOTAL_SIZE", view.detail_label.text())
        self.assertEqual(view.editors["evidence"].toPlainText(), "x")
        self.assertEqual(view.editors["scope"].toPlainText(), "x" * 16384)
        self.assertFalse(view.propose_button.isEnabled())
        self.assertTrue(view.stop_button.isEnabled())
        self.assertEqual(len(service.sent), 1)

    def test_dirty_stored_load_enables_explicit_cas_choice_without_replacing_local_text(self):
        view, session, service, fixture = self.view()
        task_id = session.task_id
        self.record(session, service, values=supplied_meaning("initial"))
        self.poll(view)
        local = dict(session.meaning_text, exclusions="Local Qt exclusion.")
        self.fill(view, local)
        old_revision = session.meaning_revision
        fixture.external_meaning(task_id, supplied_meaning("external"))
        observed = fixture.meaning_cell(task_id).revision
        self.click(view.load_button)
        service.complete()
        self.poll(view)
        self.assertEqual(session.meaning_revision, old_revision)
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(view.editors["exclusions"].toPlainText(), local["exclusions"])
        self.assertFalse(view.propose_button.isEnabled())
        self.assertTrue(view.adopt_button.isEnabled())
        self.assertEqual(service.meaning_choices, [])
        count = len(service.sent)
        self.click(view.propose_button)
        self.assertEqual(len(service.sent), count)
        self.click(view.adopt_button)
        self.assertEqual(service.meaning_choices, [(task_id, observed, session.revision)])
        self.assertEqual(session.meaning_text, local)
        self.assertTrue(view.propose_button.isEnabled())
        self.click(view.propose_button)
        self.assertEqual(service.sent[-1].record.as_dict()["meaning_expected_revision"], observed)
        service.complete()
        self.poll(view)
        self.assertEqual(fixture.meaning_cell(task_id).generation, 3)

    def test_newer_widget_edit_survives_held_proposal_result(self):
        view, session, service, fixture = self.view()
        captured = supplied_meaning("clicked capture")
        self.fill(view, captured)
        self.click(view.propose_button)
        view.editors["scope"].setPlainText("Newer widget scope while delivery held.")
        self.app.processEvents()
        service.complete()
        self.poll(view)
        self.assertEqual(view.editors["scope"].toPlainText(), "Newer widget scope while delivery held.")
        self.assertEqual(session.meaning_text["scope"], "Newer widget scope while delivery held.")
        self.assertEqual(view.status_label.text(), "UNSAVED")
        self.assertEqual(bytes.fromhex(fixture.proposal(session.task_id)["meaning"]["scope"]),
                         captured["scope"].encode("utf8"))
        self.assertTrue(session.has_unconfirmed)

    def test_stale_view_compares_original_current_saved_and_old_proposal_basis(self):
        view, session, service, fixture = self.view()
        original = session.original_instruction
        self.record(session, service, values=supplied_meaning("old source"))
        self.poll(view)
        session.set_draft("Unsaved changed source.")
        self.poll(view)
        self.assertEqual(view.basis_editor.toPlainText(), original)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), original)
        self.assertEqual(view.status_label.text(), "LOCAL_DRAFT_CHANGED")
        self.assertFalse(view.propose_button.isEnabled())
        session.save()
        service.complete()
        self.poll(view)
        self.assertEqual(view.original_editor.toPlainText(), original)
        self.assertEqual(view.basis_editor.toPlainText(), "Unsaved changed source.")
        self.assertEqual(view.proposal_basis_editor.toPlainText(), original)
        self.assertEqual(view.status_label.text(), "STALE")
        self.click(view.load_button)
        self.assertEqual(service.complete().kind, "TASK_MEANING_STALE")
        self.poll(view)
        self.assertEqual(view.status_label.text(), "STALE")
        self.assertEqual(fixture.snapshot(session.task_id)["state"], "CREATED")
        self.assertTrue(view.original_editor.isReadOnly())
        self.assertTrue(view.basis_editor.isReadOnly())
        self.assertTrue(view.proposal_basis_editor.isReadOnly())

    def test_selection_change_blocks_old_dialog_edits_and_correlates_late_result(self):
        session, service, fixture = self.session()
        first = self.create(session, service, draft="Original A.")
        session.new_task()
        second = self.create(session, service, draft="Original B.")
        second_values = supplied_meaning("B retained")
        session.set_meaning_fields(second_values)
        session.select_task(first)
        view, _, _, _ = self.view(session=session, service=service)
        first_values = supplied_meaning("A captured")
        self.fill(view, first_values)
        self.click(view.propose_button)
        view.editors["scope"].setPlainText("A newer local scope.")
        session.select_task(second)
        self.poll(view)
        self.assertTrue(all(editor.isReadOnly() for editor in view.editors.values()))
        self.assertFalse(view.propose_button.isEnabled())
        self.assertFalse(view.load_button.isEnabled())
        self.assertFalse(view.adopt_button.isEnabled())
        self.assertIn("Task selection changed", view.status_label.text())
        view.editors["evidence"].setPlainText("Programmatic stale-dialog signal.")
        self.app.processEvents()
        self.assertEqual(session.meaning_text, second_values)
        service.complete()
        self.poll(view)
        self.assertEqual(session.task_id, second)
        self.assertEqual(session.meaning_text, second_values)
        self.assertEqual(session.result_text, "")
        self.assertEqual(fixture.meaning_cell(second).generation, 0)
        session.select_task(first)
        self.poll(view)
        self.assertEqual(view.editors["scope"].toPlainText(), "A newer local scope.")
        self.assertEqual(view.editors["evidence"].toPlainText(), first_values["evidence"])
        self.assertEqual(session.meaning_revision, fixture.meaning_cell(first).revision)

    def test_meaning_only_reload_discloses_task_mismatch_and_disables_proposal(self):
        view, session, service, fixture = self.view()
        original = session.original_instruction
        self.record(session, service, values=supplied_meaning("initial basis"))
        self.poll(view)
        fixture.external_draft(session.task_id, "New external saved basis.")
        self.click(view.load_button)
        self.assertEqual(service.complete().kind, "TASK_MEANING_STALE")
        self.poll(view)
        self.assertEqual(view.status_label.text(), "STALE")
        self.assertEqual(view.basis_editor.toPlainText(), original)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), original)
        self.assertIn("reload", view.detail_label.text().lower())
        self.assertFalse(view.propose_button.isEnabled())
        self.assertFalse(session.meaning_basis_current)
        fixture.external_meaning(session.task_id, supplied_meaning("external new basis"))
        self.click(view.load_button)
        self.assertEqual(service.complete().kind, "TASK_MEANING_PROPOSAL")
        self.poll(view)
        self.assertEqual(view.status_label.text(), "TASK_REFRESH_REQUIRED")
        self.assertEqual(view.basis_editor.toPlainText(), original)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), "New external saved basis.")
        self.assertFalse(view.propose_button.isEnabled())
        self.assertTrue(view.stop_button.isEnabled())
        session.load(session.task_id)
        service.complete()
        self.poll(view)
        self.assertEqual(view.basis_editor.toPlainText(), "New external saved basis.")
        self.assertEqual(view.status_label.text(), "PROPOSED_UNACCEPTED")
        self.assertTrue(view.propose_button.isEnabled())

    def test_all_ten_editor_insertions_keep_cursor_and_keyboard_undo(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        view, session, service, _ = self.view()
        values = supplied_meaning("editable")
        self.fill(view, values)
        for name in FIELDS:
            with self.subTest(field=name):
                editor = view.editors[name]
                before = editor.toPlainText()
                cursor = editor.textCursor()
                cursor.setPosition(3)
                editor.setTextCursor(cursor)
                editor.setFocus()
                self.app.processEvents()
                editor.insertPlainText(" XY")
                self.app.processEvents()
                self.assertEqual(editor.toPlainText(), before[:3] + " XY" + before[3:])
                self.assertEqual(session.meaning_text[name], editor.toPlainText())
                self.assertEqual(editor.textCursor().position(), 6)
                self.assertTrue(editor.document().isUndoAvailable())
                self.poll(view)
                self.assertEqual(editor.textCursor().position(), 6)
                QTest.keyClick(editor, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
                self.app.processEvents()
                self.assertEqual(editor.toPlainText(), before)
                self.assertEqual(session.meaning_text[name], before)
        self.assertEqual(session.meaning_text, values)
        self.assertEqual(len(service.sent), 1)

    def test_raw_title_and_draft_key_edits_keep_cursor_and_keyboard_undo(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        session, service, _ = self.session()
        self.create(session, service)
        window = self.task_window(session, service)
        title, draft = session.title, session.draft
        window.title_editor.setCursorPosition(3)
        window.title_editor.setFocus()
        self.app.processEvents()
        QTest.keyClicks(window.title_editor, " XY")
        self.app.processEvents()
        self.assertEqual(window.title_editor.text(), title[:3] + " XY" + title[3:])
        self.assertEqual(window.title_editor.cursorPosition(), 6)
        self.assertEqual(session.title, window.title_editor.text())
        self.poll(window)
        self.assertEqual(window.title_editor.cursorPosition(), 6)
        QTest.keyClick(window.title_editor, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertEqual(window.title_editor.text(), title)
        self.assertEqual(session.title, title)
        cursor = window.draft_editor.textCursor()
        cursor.setPosition(3)
        window.draft_editor.setTextCursor(cursor)
        window.draft_editor.setFocus()
        self.app.processEvents()
        QTest.keyClicks(window.draft_editor, " XY")
        self.app.processEvents()
        self.assertEqual(window.draft_editor.toPlainText(), draft[:3] + " XY" + draft[3:])
        self.assertEqual(window.draft_editor.textCursor().position(), 6)
        self.assertEqual(session.draft, window.draft_editor.toPlainText())
        self.assertTrue(window.draft_editor.document().isUndoAvailable())
        self.poll(window)
        self.assertEqual(window.draft_editor.textCursor().position(), 6)
        QTest.keyClick(window.draft_editor, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertEqual(window.draft_editor.toPlainText(), draft)
        self.assertEqual(session.draft, draft)
        # Both prior polls observed dirty text, so metadata must not reserve
        # the shared service. Undo now clears that exact local-work guard.
        self.assertEqual([message.operation for message in service.sent], ["task.create"])
        self.assertFalse(session.has_unconfirmed)
        title_cursor = window.title_editor.cursorPosition()
        draft_cursor = window.draft_editor.textCursor().position()
        self.poll(window)
        self.poll(window)
        self.assertEqual(window.title_editor.cursorPosition(), title_cursor)
        self.assertEqual(window.draft_editor.textCursor().position(), draft_cursor)
        self.assertEqual((session.title, session.draft), (title, draft))
        # Idle metadata discovery still occurs without publishing raw text
        # or task changes; this is not suppression of the original oracle.
        self.assertEqual([message.operation for message in service.sent],
                         ["task.create", "task.editor_load"])

    def test_readonly_source_and_result_selections_survive_unchanged_polling(self):
        from PySide6.QtGui import QTextCursor
        view, session, service, _ = self.view()
        self.record(session, service, values=supplied_meaning("selection"))
        self.poll(view)
        window = self.task_window(session, service)
        widgets = (view.original_editor, view.basis_editor,
                   view.proposal_basis_editor, window.original_editor,
                   window.result_editor)
        selections = []
        for editor in widgets:
            cursor = editor.textCursor()
            cursor.setPosition(1)
            cursor.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
            editor.setTextCursor(cursor)
            selections.append((cursor.anchor(), cursor.position(), cursor.selectedText()))
        self.poll(view)
        self.poll(window)
        for editor, expected in zip(widgets, selections):
            cursor = editor.textCursor()
            self.assertTrue(editor.isReadOnly())
            self.assertEqual((cursor.anchor(), cursor.position(), cursor.selectedText()), expected)

    def test_visible_stop_bypasses_invalid_form_and_freezes_without_exit_claim(self):
        view, session, service, _ = self.view()
        retained = supplied_meaning("valid before Stop")
        self.fill(view, retained)
        view.editors["evidence"].setPlainText("x" * 16385)
        self.app.processEvents()
        self.assertFalse(view.propose_button.isEnabled())
        self.click(view.stop_button)
        self.assertEqual(service.stop_calls, 1)
        self.assertEqual(service.state, "STOPPING")
        self.assertEqual(session.status, "STOPPING")
        self.assertEqual(session.meaning_text, retained)
        self.assertTrue(all(editor.isReadOnly() for editor in view.editors.values()))
        self.assertEqual(view.editors["evidence"].toPlainText(), "x" * 16385)
        self.assertTrue(view.isVisible())
        self.assertEqual(len(service.sent), 1)

    def test_escape_from_invalid_editor_requests_stop_without_rejecting_dialog(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        view, session, service, _ = self.view()
        self.fill(view, supplied_meaning("before Escape"))
        view.editors["clarified_meaning"].setPlainText("x" * 16385)
        self.app.processEvents()
        view.editors["clarified_meaning"].setFocus()
        self.app.processEvents()
        QTest.keyClick(view.editors["clarified_meaning"], Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertEqual(service.stop_calls, 1)
        self.assertEqual(session.status, "STOPPING")
        self.assertTrue(view.isVisible())
        self.assertTrue(view.editors["clarified_meaning"].isReadOnly())
        self.assertEqual(view.editors["clarified_meaning"].toPlainText(), "x" * 16385)
        self.assertEqual(len(service.sent), 1)

    def test_window_close_invalid_discard_defaults_no_then_retires_timer_on_yes(self):
        from PySide6.QtWidgets import QMessageBox
        view, session, service, _ = self.view()
        retained = supplied_meaning("retained before close")
        self.fill(view, retained)
        view.editors["evidence"].setPlainText("x" * 16385)
        self.app.processEvents()
        view.poll_timer.start()
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.No) as prompt:
            self.assertFalse(view.close())
        prompt.assert_called_once()
        self.assertEqual(prompt.call_args.args[-1], QMessageBox.StandardButton.No)
        self.assertTrue(view.isVisible())
        self.assertTrue(view.poll_timer.isActive())
        self.assertEqual(view.editors["evidence"].toPlainText(), "x" * 16385)
        self.assertEqual(session.meaning_text, retained)
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Yes) as prompt:
            self.assertFalse(view.close())
        prompt.assert_called_once()
        self.assertTrue(view.isVisible())
        self.assertTrue(view.poll_timer.isActive())
        self.assertFalse(view.return_authorized)
        self.assertEqual(session.editor_recovery_status(), "SAVING")
        results = self.complete_editor_custody(session, service, view)
        self.assertEqual([request.operation for request, _ in results],
                         ["task.editor_retain", "task.editor_discard"])
        self.assertFalse(view.isVisible())
        self.assertFalse(view.poll_timer.isActive())
        self.assertTrue(view.return_authorized)
        self.assertEqual(session.meaning_text, retained)
        self.assertEqual(service.stop_calls, 0)

    def test_return_button_invalid_discard_cancel_preserves_then_yes_closes(self):
        from PySide6.QtWidgets import QMessageBox
        view, session, service, _ = self.view()
        retained = supplied_meaning("retained before Return")
        self.fill(view, retained)
        view.editors["evidence"].setPlainText("x" * 16385)
        self.app.processEvents()
        view.poll_timer.start()
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.No) as prompt:
            self.click(view.close_button)
        prompt.assert_called_once()
        self.assertEqual(prompt.call_args.args[-1], QMessageBox.StandardButton.No)
        self.assertTrue(view.isVisible())
        self.assertTrue(view.poll_timer.isActive())
        self.assertEqual(session.meaning_text, retained)
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Yes) as prompt:
            self.click(view.close_button)
        prompt.assert_called_once()
        self.assertTrue(view.isVisible())
        self.assertTrue(view.poll_timer.isActive())
        self.assertFalse(view.return_authorized)
        results = self.complete_editor_custody(session, service, view)
        self.assertEqual([request.operation for request, _ in results],
                         ["task.editor_retain", "task.editor_discard"])
        self.assertFalse(view.isVisible())
        self.assertFalse(view.poll_timer.isActive())
        self.assertTrue(view.return_authorized)
        self.assertEqual(session.meaning_text, retained)
        self.assertEqual(service.stop_calls, 0)

    def test_valid_return_requires_durable_custody_before_explicit_discard(self):
        from PySide6.QtWidgets import QMessageBox
        view, session, service, _ = self.view()
        values = supplied_meaning("unconfirmed cache")
        self.fill(view, values)
        view.poll_timer.start()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes) as prompt:
            self.click(view.close_button)
        prompt.assert_called_once()
        self.assertTrue(view.isVisible())
        self.assertTrue(view.poll_timer.isActive())
        self.assertFalse(view.return_authorized)
        results = self.complete_editor_custody(session, service, view)
        self.assertEqual([request.operation for request, _ in results],
                         ["task.editor_retain", "task.editor_discard"])
        self.assertFalse(view.isVisible())
        self.assertFalse(view.poll_timer.isActive())
        self.assertTrue(view.return_authorized)
        self.assertEqual(session.meaning_text, values)
        self.assertTrue(session.has_unconfirmed)
        self.assertEqual(session.editor_recovery_snapshot()["state"], "DISCARDED")
        self.assertEqual(service.stop_calls, 0)

    def test_capture_runtime_error_retains_exact_widget_bytes_for_retry(self):
        """A serialization fault must leave a non-Qt custody copy for retry."""
        view, session, service, fixture = self.view()
        task_id = session.task_id
        before = (fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                  fixture.meaning_cell(task_id), fixture.store.store_position())
        first = supplied_meaning("capture RuntimeError")
        with patch("ceta.desktop.meaning_view.editor_payload_wire",
                   side_effect=RuntimeError("controlled capture serialization failure")):
            self.fill(view, first)
        expected = {name: editor.document().toRawText().encode(
            "utf-16-le", errors="surrogatepass") for name, editor in view.editors.items()}
        local = session.editor_local_documents(task_id)
        self.assertIsNotNone(local)
        self.assertEqual({name: facts["utf16le_bytes"] for name, facts in local["documents"].items()},
                         expected)
        self.assertEqual(session.editor_recovery_status(task_id), "CONFLICT")
        self.assertEqual(session.editor_recovery_error(task_id), "EDITOR_CAPTURE_RUNTIME_FAILURE")
        self.assertTrue(view.isVisible())
        self.assertIn("Full documents remain in this window", view.detail_label.text())
        self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                          fixture.meaning_cell(task_id), fixture.store.store_position()), before)
        self.assertEqual([message.operation for message in service.sent], ["task.create"])

        retry = dict(first, evidence=first["evidence"] + " Retry after capture fault.")
        self.fill(view, retry)
        session.prioritize_editor_custody(task_id)
        results = self.complete_editor_custody(session, service, view)
        self.assertEqual([request.operation for request, _ in results], ["task.editor_retain"])
        self.assertIsNone(session.editor_recovery_error(task_id))
        self.assert_raw_editor_recovery(view, session, fixture)
        self.assertEqual(session.meaning_text, retry)
        self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                          fixture.meaning_cell(task_id)), before[:3])
    def test_exec_exception_retains_exact_rejected_native_document_after_deferred_delete(self):
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QMessageBox
        from shiboken6 import isValid
        for error in (RuntimeError, KeyboardInterrupt):
            with self.subTest(error=error.__name__):
                session, service, fixture = self.session()
                task_id = self.create(session, service)
                retained = supplied_meaning("last valid " + error.__name__)
                self.record(session, service, values=retained)
                window = self.task_window(session, service)
                before = (fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                          fixture.meaning_cell(task_id), fixture.store.store_position())
                generation = session._entry()["meaning_edit_generation"]
                rejected = supplied_meaning("visible rejected " + error.__name__)
                rejected["clarified_meaning"] = "x" * 16385
                with patch.object(QMessageBox, "question") as prompt:
                    child = self.interrupted_interpretation(window, rejected, error=error)
                    destroyed = []
                    child.destroyed.connect(lambda _obj=None: destroyed.append(True))
                    self.flush_deferred_deletes()
                prompt.assert_not_called()
                self.assertTrue(isValid(child)); self.assertFalse(destroyed)
                self.assertIs(window._meaning_views[task_id], child)
                self.assertTrue(child.isVisible()); self.assertFalse(child.isModal())
                self.assertFalse(child.return_authorized)
                self.assertTrue(child.poll_timer.isActive())
                self.assertTrue(window.meaning_recovery_button.isEnabled())
                self.assertEqual(window.meaning_recovery_picker.currentText(), task_id)
                self.assertEqual({name: editor.toPlainText() for name, editor in child.editors.items()}, rejected)
                self.assertEqual(len(child.editors["clarified_meaning"].toPlainText().encode("utf8")), 16385)
                ticks = []
                child.poll_timer.timeout.connect(lambda: ticks.append(True))
                child.poll_timer.setInterval(1); QTest.qWait(20)
                self.assertTrue(ticks, "The retained dialog's actual Qt timer did not run")
                self.assertEqual(session.meaning_text, retained)
                self.assertEqual(session._entry()["meaning_edit_generation"], generation)
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                                  fixture.meaning_cell(task_id), fixture.store.store_position()), before)
                self.assertEqual(service.stop_calls, 0)
                self.assertEqual([message.operation for message in service.sent],
                                 ["task.create", "task.meaning_propose", "task.editor_retain"])
                self.assertEqual(session.editor_recovery_status(), "SAVING")
                self.assertIsNone(session.editor_recovery_snapshot())
                # Repeated opening reuses the owned document rather than
                # replacing it with the session's earlier valid form.
                with patch.object(type(child), "exec") as another_exec:
                    window._meaning()
                another_exec.assert_not_called()
                self.assertIs(window._meaning_views[task_id], child)
                self.assertEqual(child.editors["clarified_meaning"].toPlainText(), rejected["clarified_meaning"])
                results = self.complete_editor_custody(session, service, child)
                self.assertEqual([request.operation for request, _ in results], ["task.editor_retain"])
                retained_wire = self.assert_raw_editor_recovery(child, session, fixture)
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)), before[:3])
                self.assertEqual(fixture.store.store_position().next_commit, before[3].next_commit + 1)
                with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                    child.reject()
                self.assertFalse(child.return_authorized)
                self.assertTrue(isValid(child)); self.assertTrue(child.isVisible())
                self.assertEqual(session.editor_recovery_status(), "DISCARDING")
                results = self.complete_editor_custody(session, service, child)
                self.assertEqual([request.operation for request, _ in results], ["task.editor_discard"])
                self.assertEqual(session.editor_recovery_snapshot()["state"], "DISCARDED")
                child.reject()
                self.flush_deferred_deletes()
                self.assertFalse(isValid(child)); self.assertTrue(destroyed)
                self.assertFalse(window._meaning_views)
                self.assertEqual(session.meaning_text, retained)
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)), before[:3])
                self.assertIn(retained_wire, [row[0] for row in fixture.store._connection.execute("SELECT value_wire FROM store_changes")])
                self.assertEqual([message.operation for message in service.sent],
                    ["task.create", "task.meaning_propose", "task.editor_retain", "task.editor_discard"])

    def test_two_retained_tasks_recover_exact_forms_then_record_valid_or_discard_explicitly(self):
        from PySide6.QtWidgets import QMessageBox
        from shiboken6 import isValid
        from ceta.desktop.meaning_view import MeaningView
        session, service, fixture = self.session()
        first = self.create(session, service, draft="First task original input.")
        first_valid = supplied_meaning("first stored")
        self.record(session, service, values=first_valid)
        window = self.task_window(session, service)
        first_rejected = supplied_meaning("first rejected whole form")
        first_rejected["clarified_meaning"] = "A" * 16385
        first_view = self.interrupted_interpretation(window, first_rejected)
        self.complete_editor_custody(session, service, first_view)
        first_raw = self.assert_raw_editor_recovery(first_view, session, fixture)
        session.new_task()
        second = self.create(session, service, draft="Second task original input.")
        second_valid = supplied_meaning("second stored")
        self.record(session, service, values=second_valid)
        window._refresh()
        second_rejected = supplied_meaning("second rejected whole form")
        second_rejected["evidence"] = "B" * 16385
        second_view = self.interrupted_interpretation(window, second_rejected)
        self.complete_editor_custody(session, service, second_view)
        second_raw = self.assert_raw_editor_recovery(second_view, session, fixture)
        self.assertEqual([message.operation for message in service.sent],
            ["task.create", "task.meaning_propose", "task.editor_retain",
             "task.create", "task.meaning_propose", "task.editor_retain"])
        before = {task_id: (fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                            fixture.meaning_cell(task_id)) for task_id in (first, second)}
        before_position = fixture.store.store_position()
        self.flush_deferred_deletes()
        self.assertTrue(isValid(first_view)); self.assertTrue(isValid(second_view))
        self.assertEqual(set(window._meaning_views), {first, second})
        self.assertEqual(set(window.findChildren(MeaningView)), {first_view, second_view})
        for task_id, child, values in ((first, first_view, first_rejected), (second, second_view, second_rejected),
                                       (first, first_view, first_rejected)):
            window.meaning_recovery_picker.setCurrentIndex(window.meaning_recovery_picker.findText(task_id))
            self.click(window.meaning_recovery_button)
            self.assertEqual(session.task_id, task_id)
            self.assertTrue(child.isVisible()); self.assertTrue(child.poll_timer.isActive())
            self.assertEqual({name: editor.toPlainText() for name, editor in child.editors.items()}, values)
            other = second_view if task_id == first else first_view
            self.assertTrue(all(editor.isReadOnly() for editor in other.editors.values()))
        self.assertEqual(fixture.store.store_position(), before_position)
        for task_id in (first, second):
            self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id),
                              fixture.meaning_cell(task_id)), before[task_id])
        corrected = dict(first_rejected, clarified_meaning="A corrected valid objective.")
        self.fill(first_view, corrected)
        self.assertFalse(first_view.has_rejected_edits)
        self.assertEqual(session.meaning_text, corrected)
        # This valid unsaved edit still has raw widget custody. Explicitly
        # flush it before recording a proposal so a later dialog/runtime
        # failure cannot leave its only copy in the native widget.
        session.prioritize_editor_custody(first)
        self.poll(first_view)
        self.assertFalse(first_view.propose_button.isEnabled())
        self.assertEqual(session.editor_recovery_status(first), "SAVING")
        results = self.complete_editor_custody(session, service, first_view)
        self.assertEqual([request.operation for request, _ in results], ["task.editor_retain"])
        first_corrected_raw = self.assert_raw_editor_recovery(first_view, session, fixture)
        self.assertTrue(first_view.propose_button.isEnabled())
        self.click(first_view.propose_button)
        self.assertEqual(service.complete().kind, "TASK_MEANING_PROPOSAL")
        self.poll(first_view)
        proposal = fixture.proposal(first)
        self.assertEqual(proposal["state"], "UNACCEPTED")
        self.assertEqual({name: bytes.fromhex(proposal["meaning"][name]).decode("utf8") for name in FIELDS}, corrected)
        self.assertEqual(proposal["basis_revision"], before[first][0].revision)
        self.assertEqual(fixture.draft_cell(first), before[first][0])
        self.assertEqual(fixture.kernel_cell(first), before[first][1])
        with patch.object(QMessageBox, "question") as prompt:
            self.click(first_view.close_button)
        prompt.assert_not_called()
        self.flush_deferred_deletes()
        self.assertFalse(isValid(first_view)); self.assertNotIn(first, window._meaning_views)
        window.meaning_recovery_picker.setCurrentIndex(window.meaning_recovery_picker.findText(second))
        self.click(window.meaning_recovery_button)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as prompt:
            self.click(second_view.close_button)
        self.assertEqual(prompt.call_args.args[-1], QMessageBox.StandardButton.No)
        self.flush_deferred_deletes()
        self.assertTrue(isValid(second_view)); self.assertTrue(second_view.isVisible())
        self.assertEqual(second_view.editors["evidence"].toPlainText(), second_rejected["evidence"])
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.click(second_view.close_button)
        self.assertTrue(isValid(second_view)); self.assertTrue(second_view.isVisible())
        self.assertFalse(second_view.return_authorized)
        self.assertEqual(session.editor_recovery_status(second), "DISCARDING")
        results = self.complete_editor_custody(session, service, second_view)
        self.assertEqual([request.operation for request, _ in results], ["task.editor_discard"])
        self.assertEqual(session.editor_recovery_snapshot(second)["state"], "DISCARDED")
        self.click(second_view.close_button)
        self.flush_deferred_deletes()
        self.assertFalse(isValid(second_view)); self.assertFalse(window._meaning_views)
        self.assertEqual(session.meaning_text, second_valid)
        self.assertEqual((fixture.draft_cell(second), fixture.kernel_cell(second), fixture.meaning_cell(second)), before[second])
        self.assertEqual(service.stop_calls, 0)
        historical = [row[0] for row in fixture.store._connection.execute("SELECT value_wire FROM store_changes")]
        for raw in (first_raw, second_raw, first_corrected_raw): self.assertIn(raw, historical)
        self.assertEqual(session.editor_recovery_snapshot(first)["state"], "RETAINED")
        self.assertIn(first, session.editor_recovery_task_ids)
        self.assertNotIn(second, session.editor_recovery_task_ids)
        self.assertEqual([message.operation for message in service.sent],
            ["task.create", "task.meaning_propose", "task.editor_retain",
             "task.create", "task.meaning_propose", "task.editor_retain",
             "task.editor_retain", "task.meaning_propose", "task.editor_discard"])

    def test_direct_done_accept_and_reject_share_invalid_discard_guard(self):
        from PySide6.QtWidgets import QDialog, QMessageBox
        from shiboken6 import isValid
        for route in ("done_rejected", "done_accepted", "accept", "reject"):
            with self.subTest(route=route):
                view, session, service, fixture = self.view()
                task_id = session.task_id
                retained = supplied_meaning("retained before " + route)
                self.fill(view, retained)
                view.editors["evidence"].setPlainText("x" * 16385)
                view.poll_timer.start()
                before = (fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id))
                action = (lambda: view.done(QDialog.DialogCode.Rejected)) if route == "done_rejected" else (
                    (lambda: view.done(QDialog.DialogCode.Accepted)) if route == "done_accepted" else getattr(view, route))
                with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as prompt:
                    action()
                prompt.assert_called_once()
                self.assertEqual(prompt.call_args.args[-1], QMessageBox.StandardButton.No)
                self.flush_deferred_deletes()
                self.assertTrue(isValid(view)); self.assertTrue(view.isVisible())
                self.assertTrue(view.poll_timer.isActive()); self.assertFalse(view.return_authorized)
                self.assertEqual(view.editors["evidence"].toPlainText(), "x" * 16385)
                self.assertEqual(session.meaning_text, retained)
                with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes): action()
                # A positive answer is a disposition intent, not permission to
                # drop the only raw documents. The exact capture first becomes
                # durable, then the exact retained revision receives its
                # authenticated discard receipt.
                self.assertTrue(view.isVisible()); self.assertTrue(view.poll_timer.isActive())
                self.assertFalse(view.return_authorized)
                self.assertEqual(session.editor_recovery_status(), "SAVING")
                self.assertEqual([message.operation for message in service.sent],
                                 ["task.create", "task.editor_retain"])
                results = self.complete_editor_custody(session, service, view)
                self.assertEqual([request.operation for request, _ in results],
                                 ["task.editor_retain", "task.editor_discard"])
                self.assertEqual(session.editor_recovery_snapshot()["state"], "DISCARDED")
                self.assertFalse(view.isVisible()); self.assertFalse(view.poll_timer.isActive())
                self.assertTrue(view.return_authorized)
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)), before)
                self.assertEqual(service.stop_calls, 0)

    def test_parent_close_guards_rejected_dialog_not_in_session_and_stop_still_freezes_it(self):
        from PySide6.QtWidgets import QMessageBox
        from shiboken6 import isValid
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        window = self.task_window(session, service)
        rejected = dict.fromkeys(FIELDS, "")
        rejected["clarified_meaning"] = "x" * 16385
        child = self.interrupted_interpretation(window, rejected, poll_interval_ms=60000)
        before = (fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id),
                  fixture.store.store_position())
        self.assertTrue(session.has_unconfirmed)
        self.assertEqual(session.editor_recovery_status(), "QUEUED")
        self.assertIsNone(session.editor_recovery_snapshot())
        self.assertIsNone(session._pending)
        self.assertIsNone(service.pending)
        self.assertEqual([message.operation for message in service.sent], ["task.create"])
        raw_documents = session.editor_local_documents()
        self.assertEqual(raw_documents["documents"]["clarified_meaning"]["utf16le_bytes"],
                         child.editors["clarified_meaning"].document().toRawText().encode("utf-16-le"))
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as prompt:
            self.assertFalse(window.close())
        prompt.assert_called_once()
        self.assertEqual(prompt.call_args.args[-1], QMessageBox.StandardButton.No)
        self.assertFalse(window._close_requested); self.assertTrue(window.isVisible())
        self.assertEqual(service.stop_calls, 0)
        with patch.object(QMessageBox, "question") as prompt:
            self.click(window.stop_button)
        prompt.assert_not_called()
        self.assertEqual(service.stop_calls, 1); self.assertEqual(session.status, "STOPPING")
        self.assertTrue(all(editor.isReadOnly() for editor in child.editors.values()))
        self.assertTrue(child.isVisible()); self.assertTrue(child.poll_timer.isActive())
        self.assertEqual(child.editors["clarified_meaning"].toPlainText(), rejected["clarified_meaning"])
        service.finish_stop(); self.poll(window)
        self.assertEqual(session.status, "STOPPED")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as prompt:
            self.assertFalse(window.close())
        prompt.assert_called_once()
        self.flush_deferred_deletes()
        self.assertTrue(isValid(child)); self.assertTrue(window.isVisible())
        self.assertTrue(window.meaning_recovery_button.isEnabled())
        # A stopped owned service cannot manufacture the authenticated
        # retain/discard receipt. Even a positive local answer must leave the
        # window and exact raw documents available for a later restart.
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.assertFalse(window.close())
        self.flush_deferred_deletes()
        self.assertTrue(isValid(child)); self.assertTrue(window.isVisible())
        self.assertTrue(child.isVisible()); self.assertTrue(child.poll_timer.isActive())
        self.assertFalse(child.return_authorized)
        self.assertIs(window._meaning_views[task_id], child)
        self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id),
                          fixture.store.store_position()), before)
        self.assertEqual(session.editor_recovery_status(), "QUEUED")
        self.assertEqual(session.editor_local_documents()["documents"]["clarified_meaning"]["utf16le_bytes"],
                         raw_documents["documents"]["clarified_meaning"]["utf16le_bytes"])
        self.assertIsNone(session.editor_recovery_snapshot())
        self.assertEqual([message.operation for message in service.sent], ["task.create"])

    def test_cleanup_errors_retain_owned_documents_until_later_guarded_return(self):
        from PySide6.QtWidgets import QMessageBox
        from shiboken6 import isValid
        for failed_cleanup in ("timer_stop", "delete_later"):
            with self.subTest(failed_cleanup=failed_cleanup):
                session, service, fixture = self.session()
                task_id = self.create(session, service)
                window = self.task_window(session, service)
                rejected = dict.fromkeys(FIELDS, "")
                rejected["evidence"] = "x" * 16385
                child = self.interrupted_interpretation(window, rejected)
                before = (fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id),
                          fixture.store.store_position())
                # Consent starts a two-step durable protocol. It cannot invoke
                # any Qt cleanup while the only raw copy is still merely local.
                with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                    child.reject()
                self.assertTrue(child.isVisible()); self.assertFalse(child.return_authorized)
                self.assertEqual(service.pending["request"].operation, "task.editor_retain")
                self.assertEqual(service.complete().kind, "TASK_EDITOR_RETAINED")
                session.poll(); child._poll()
                self.assertEqual(service.pending["request"].operation, "task.editor_discard")
                target, name = (child.poll_timer, "stop") if failed_cleanup == "timer_stop" else (child, "deleteLater")
                with patch.object(target, name, side_effect=RuntimeError("controlled cleanup failure")):
                    self.assertEqual(service.complete().kind, "TASK_EDITOR_DISCARDED")
                    session.poll()
                    if failed_cleanup == "timer_stop":
                        with self.assertRaisesRegex(RuntimeError, "controlled cleanup failure"):
                            child._poll()
                    else:
                        child._poll()
                self.flush_deferred_deletes()
                self.assertTrue(isValid(child)); self.assertIs(window._meaning_views[task_id], child)
                self.assertTrue(child.isVisible()); self.assertTrue(child.poll_timer.isActive())
                self.assertFalse(child.return_authorized)
                # The exact raw text is no longer represented as active input
                # after its authenticated discard receipt, but is retained in
                # the durable discarded snapshot rather than being lost in the
                # cleanup fault.
                self.assertEqual(child.editors["evidence"].toPlainText(), "")
                self.assertEqual((fixture.draft_cell(task_id), fixture.kernel_cell(task_id), fixture.meaning_cell(task_id)),
                                 before[:3])
                position = fixture.store.store_position()
                self.assertEqual(position.next_commit, before[3].next_commit + 2)
                discarded = session.editor_recovery_snapshot()
                self.assertEqual(discarded["state"], "DISCARDED")
                self.assertEqual(bytes.fromhex(discarded["payload"]["documents"]["evidence"]["utf16le_hex"]),
                                 rejected["evidence"].encode("utf-16-le", errors="surrogatepass"))
                # The authenticated discard record now guards later return;
                # a cleanup fault cannot turn it into an accepted task or
                # interpretation write.
                child.reject()
                self.flush_deferred_deletes()
                self.assertFalse(isValid(child)); self.assertFalse(window._meaning_views)
                self.assertEqual(service.stop_calls, 0)

    def test_recovery_navigation_does_not_replace_another_rejected_raw_task_document(self):
        session, service, _ = self.session()
        first = self.create(session, service, draft="First task.")
        window = self.task_window(session, service)
        rejected = dict.fromkeys(FIELDS, "")
        rejected["scope"] = "x" * 16385
        child = self.interrupted_interpretation(window, rejected)
        # The interrupted raw editor is now an owned asynchronous custody
        # request.  Observe its bounded retain result before issuing a second
        # task command; no raw form is promoted into meaning/task state.
        session.prioritize_editor_custody(first)
        results = self.complete_editor_custody(session, service, child)
        self.assertEqual([request.operation for request, _ in results], ["task.editor_retain"])
        session.new_task()
        second = self.create(session, service, draft="Second task.")
        window._refresh()
        title, draft = session.title, session.draft
        window.title_editor.setText("x" * 257)
        self.app.processEvents()
        self.assertEqual(window._text_error, "TASK_TEXT_SIZE")
        window.meaning_recovery_picker.setCurrentIndex(window.meaning_recovery_picker.findText(first))
        self.click(window.meaning_recovery_button)
        self.assertEqual(session.task_id, second)
        self.assertEqual(window.title_editor.text(), "x" * 257)
        self.assertEqual(session.title, title); self.assertEqual(session.draft, draft)
        self.assertTrue(child.isVisible())
        self.assertTrue(all(editor.isReadOnly() for editor in child.editors.values()))
        self.assertEqual(child.editors["scope"].toPlainText(), rejected["scope"])
        window.title_editor.setText(title)
        self.app.processEvents()
        self.click(window.meaning_recovery_button)
        self.assertEqual(session.task_id, first)
        self.assertFalse(child.editors["scope"].isReadOnly())
        self.assertEqual(child.editors["scope"].toPlainText(), rejected["scope"])

    def test_real_task_view_modal_return_and_window_close_share_session_and_retire_timer(self):
        from PySide6.QtCore import QCoreApplication, QEvent, QTimer
        from PySide6.QtWidgets import QDialog, QMessageBox
        from shiboken6 import isValid
        from ceta.desktop.meaning_view import MeaningView
        session, service, _ = self.session()
        self.create(session, service)
        window = self.task_window(session, service)
        for close_method in ("return_button", "window_close"):
            with self.subTest(close_method=close_method):
                outcome = {}
                rescue = QTimer()
                rescue.setSingleShot(True)

                def rescue_modal():
                    outcome["rescued"] = True
                    child = outcome.get("dialog") or self.app.activeModalWidget()
                    if isinstance(child, QDialog):
                        child.done(QDialog.DialogCode.Rejected)

                def settle_custody():
                    """Complete the held real journal protocol inside exec()."""
                    child = outcome.get("dialog")
                    if not isinstance(child, MeaningView) or not isValid(child) or child.return_authorized:
                        return
                    turns = outcome.get("settlement_turns", 0) + 1
                    outcome["settlement_turns"] = turns
                    if turns > 8:
                        outcome["error"] = AssertionError("Modal return did not settle bounded editor custody")
                        return
                    if service.pending is not None:
                        outcome.setdefault("custody_operations", []).append(service.pending["request"].operation)
                        service.complete()
                    child._poll()
                    if child.isVisible() and not child.return_authorized:
                        QTimer.singleShot(0, settle_custody)

                def edit_and_return():
                    try:
                        child = self.app.activeModalWidget()
                        if not isinstance(child, MeaningView):
                            raise AssertionError("TaskView did not open the real MeaningView")
                        outcome["dialog"] = child
                        child.destroyed.connect(
                            lambda _obj=None: outcome.__setitem__("destroyed", True))
                        outcome["same_session"] = child._session is session
                        outcome["timer_before"] = child.poll_timer.isActive()
                        self.fill(child, supplied_meaning(close_method))
                        if close_method == "window_close":
                            child.close()
                        else:
                            self.click(child.close_button)
                        # A valid-but-unsaved interpretation is also raw
                        # custody. The initial positive response keeps the
                        # real dialog alive until retain + discard receipts
                        # bind the exact capture.
                        outcome["visible_while_receipt_pending"] = child.isVisible()
                        outcome["timer_while_receipt_pending"] = child.poll_timer.isActive()
                        QTimer.singleShot(0, settle_custody)
                    except BaseException as error:
                        outcome["error"] = error
                        child = outcome.get("dialog") or self.app.activeModalWidget()
                        if isinstance(child, QDialog):
                            child.done(QDialog.DialogCode.Rejected)

                rescue.timeout.connect(rescue_modal)
                rescue.start(1500)
                QTimer.singleShot(0, edit_and_return)
                try:
                    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                        self.click(window.meaning_button)
                finally:
                    rescue.stop()
                self.assertNotIn("error", outcome, repr(outcome.get("error")))
                self.assertNotIn("rescued", outcome, "Modal close did not finish before fixture rescue")
                self.assertTrue(outcome.get("same_session"))
                self.assertTrue(outcome.get("timer_before"))
                child = outcome["dialog"]
                self.assertTrue(outcome["visible_while_receipt_pending"])
                self.assertTrue(outcome["timer_while_receipt_pending"])
                self.assertEqual(outcome.get("custody_operations"),
                                 ["task.editor_retain", "task.editor_discard"])
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                self.app.processEvents()
                self.assertTrue(outcome.get("destroyed"))
                self.assertFalse(isValid(child))
                self.assertEqual(window.findChildren(MeaningView), [])
                self.assertEqual(session.meaning_text, supplied_meaning(close_method))
                self.assertTrue(session.has_unconfirmed)
                self.assertEqual(session.editor_recovery_snapshot()["state"], "DISCARDED")
                self.assertEqual(service.stop_calls, 0)
                self.assertTrue(window.isVisible())

    def test_hidden_meaning_edit_requires_task_close_consent_then_observed_stop(self):
        from PySide6.QtWidgets import QMessageBox
        session, service, _ = self.session()
        first = self.create(session, service, draft="Task with hidden interpretation.")
        session.set_meaning_fields(supplied_meaning("hidden meaning"))
        session.new_task()
        second = self.create(session, service, draft="Clean selected task.")
        window = self.task_window(session, service)
        self.assertFalse(session.dirty)
        self.assertFalse(session.meaning_dirty)
        self.assertTrue(session.has_unconfirmed)
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Cancel) as prompt:
            self.assertFalse(window.close())
        prompt.assert_called_once()
        self.assertEqual(prompt.call_args.args[-1], QMessageBox.StandardButton.Cancel)
        self.assertTrue(window.isVisible())
        self.assertEqual(session.task_id, second)
        self.assertEqual(service.stop_calls, 0)
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Close) as prompt:
            self.assertFalse(window.close())
        prompt.assert_called_once()
        self.assertEqual(service.state, "STOPPING")
        self.assertTrue(window.isVisible())
        self.assertTrue(window.draft_editor.isReadOnly())
        self.assertFalse(window.meaning_button.isEnabled())
        self.poll(window)
        self.assertTrue(window.isVisible())
        service.finish_stop()
        self.poll(window)
        self.assertFalse(window.isVisible())
        self.assertFalse(window.poll_timer.isActive())
        session.select_task(first)
        self.assertEqual(session.meaning_text, supplied_meaning("hidden meaning"))

    def test_returning_from_stopped_modal_keeps_main_task_editors_frozen(self):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtTest import QTest
        from ceta.desktop.meaning_view import MeaningView
        session, service, _ = self.session()
        self.create(session, service)
        window = self.task_window(session, service)
        title, draft = session.title, session.draft
        # Construct the same owned child without entering a nested modal loop:
        # once Stop is observed, the correct behavior is to retain it rather
        # than manufacture a return path just to let the loop finish.
        child = MeaningView(session, window)
        window._meaning_views[session.task_id] = child
        child.show(); self.app.processEvents()
        self.fill(child, supplied_meaning("stop then return"))
        self.click(child.stop_button)
        self.poll(window)
        self.assertTrue(all(editor.isReadOnly() for editor in child.editors.values()))
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.click(child.close_button)
        self.assertTrue(child.isVisible())
        self.assertTrue(child.poll_timer.isActive())
        self.assertFalse(child.return_authorized)
        self.assertEqual(session.editor_recovery_status(), "QUEUED")
        self.assertIsNotNone(session.editor_local_documents())
        self.assertEqual(service.stop_calls, 1)
        self.assertEqual(session.status, "STOPPING")
        self.assertTrue(window.title_editor.isReadOnly())
        self.assertTrue(window.draft_editor.isReadOnly())
        self.assertFalse(window.new_button.isEnabled())
        self.assertFalse(window.local_select_button.isEnabled())
        self.assertFalse(window.meaning_button.isEnabled())
        self.assertTrue(window.stop_button.isEnabled())
        QTest.keyClicks(window.title_editor, "must not append")
        QTest.keyClicks(window.draft_editor, "must not append")
        self.app.processEvents()
        self.assertEqual(session.title, title)
        self.assertEqual(session.draft, draft)
        service.finish_stop()
        self.poll(window)
        self.assertEqual(session.status, "STOPPED")
        self.assertTrue(window.title_editor.isReadOnly())
        self.assertTrue(window.draft_editor.isReadOnly())


    def test_dirty_preview_shows_latest_stored_fields_and_keeps_selected_local_basis(self):
        from PySide6.QtTest import QTest
        view, session, service, fixture = self.view()
        task_id = session.task_id
        original = session.original_instruction
        self.record(session, service, values=supplied_meaning("selected proposal"))
        self.poll(view)
        selected, selected_revision = session.meaning_proposal, session.meaning_revision
        local = supplied_meaning("retained local form")
        self.fill(view, local)
        external_draft = "External saved draft used by the latest proposal."
        fixture.external_draft(task_id, external_draft)
        external = supplied_meaning("external observed meaning")
        fixture.external_meaning(task_id, external)
        observed_revision = fixture.meaning_cell(task_id).revision
        current_task_revision = fixture.draft_cell(task_id).revision
        self.click(view.load_button)
        self.assertEqual(service.complete().kind, "TASK_MEANING_PROPOSAL")
        self.poll(view)
        preview = view.observation_editor.toPlainText()
        self.assertIn("Observed stored proposal: UNACCEPTED", preview)
        self.assertIn("Current saved task revision: " + current_task_revision, preview)
        self.assertIn("Observed proposal revision: " + observed_revision, preview)
        self.assertIn(external_draft, preview)
        labels = ("Objective", "Scope", "Exclusions", "Done when", "Assumptions",
                  "Open questions", "Standing instructions", "Requested authority",
                  "Requested limits", "Supporting evidence")
        for name, label in zip(FIELDS, labels):
            with self.subTest(field=name):
                self.assertIn(label + ":\n" + external[name], preview)
                self.assertEqual(view.editors[name].toPlainText(), local[name])
        self.assertTrue(view.observation_editor.isReadOnly())
        self.assertEqual(view.original_editor.toPlainText(), original)
        self.assertEqual(view.basis_editor.toPlainText(), original)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), original)
        self.assertEqual(session.meaning_proposal, selected)
        self.assertEqual(session.meaning_revision, selected_revision)
        self.assertEqual(session.meaning_text, local)
        self.assertTrue(session.has_meaning_remote)
        self.assertFalse(view.propose_button.isEnabled())
        self.assertEqual(service.meaning_choices, [])
        view.observation_editor.setFocus()
        self.app.processEvents()
        QTest.keyClicks(view.observation_editor, "must not alter observed evidence")
        self.app.processEvents()
        self.assertEqual(view.observation_editor.toPlainText(), preview)
        self.assertEqual(session.meaning_text, local)

    def test_stale_preview_selection_survives_poll_and_adoption_clears_preview_only(self):
        from PySide6.QtGui import QTextCursor
        view, session, service, fixture = self.view()
        task_id = session.task_id
        original = session.original_instruction
        self.record(session, service, values=supplied_meaning("selected original"))
        self.poll(view)
        selected, selected_revision = session.meaning_proposal, session.meaning_revision
        local = supplied_meaning("unconfirmed local meaning")
        self.fill(view, local)
        observed_draft = "Saved basis B used by the observed proposal."
        fixture.external_draft(task_id, observed_draft)
        external = supplied_meaning("proposal on basis B")
        fixture.external_meaning(task_id, external)
        observed_proposal = fixture.proposal(task_id)
        observed_revision = fixture.meaning_cell(task_id).revision
        fixture.external_draft(task_id, "Newer saved basis C; proposal B is stale.")
        current_task_revision = fixture.draft_cell(task_id).revision
        self.click(view.load_button)
        self.assertEqual(service.complete().kind, "TASK_MEANING_STALE")
        self.poll(view)
        preview = view.observation_editor.toPlainText()
        self.assertIn("Observed stored proposal: STALE", preview)
        self.assertIn("Current saved task revision: " + current_task_revision, preview)
        self.assertIn("Observed proposal revision: " + observed_revision, preview)
        self.assertIn(observed_draft, preview)
        for name in FIELDS:
            self.assertIn(external[name], preview)
        self.assertTrue(view.observation_editor.isReadOnly())
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(session.meaning_proposal, selected)
        self.assertEqual(session.meaning_revision, selected_revision)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), original)
        cursor = view.observation_editor.textCursor()
        cursor.setPosition(1)
        cursor.setPosition(12, QTextCursor.MoveMode.KeepAnchor)
        view.observation_editor.setTextCursor(cursor)
        selection = (cursor.anchor(), cursor.position(), cursor.selectedText())
        self.poll(view)
        cursor = view.observation_editor.textCursor()
        self.assertEqual(view.observation_editor.toPlainText(), preview)
        self.assertEqual((cursor.anchor(), cursor.position(), cursor.selectedText()), selection)
        # The visible valid-but-unsaved form received its own raw custody
        # capture before the external task save.  It remains durably retained
        # with its exact prior basis and current corrected task lineage; it is
        # never promoted into the selected task or meaning proposal.
        expected_raw = {name: editor.document().toRawText().encode(
            "utf-16-le", errors="surrogatepass") for name, editor in view.editors.items()}
        prior_basis = session.revision
        session.prioritize_editor_custody(task_id)
        results = self.complete_editor_custody(session, service, view)
        self.assertEqual([request.operation for request, _ in results], ["task.editor_retain"])
        retained = session.editor_recovery_snapshot(task_id)
        self.assertEqual(retained["state"], "RETAINED")
        self.assertEqual(retained["payload"]["basis_revision"], prior_basis)
        self.assertEqual(retained["lineage"]["task_basis_revision"], prior_basis)
        self.assertEqual(retained["lineage"]["observed_task_revision"],
                         fixture.draft_cell(task_id).revision)
        self.assertEqual(retained["lineage"]["corrected_task_revision"],
                         fixture.snapshot(task_id)["objective_revision"])
        captured_local = session.editor_local_documents(task_id)
        self.assertEqual({name: facts["utf16le_bytes"] for name, facts in captured_local["documents"].items()},
                         expected_raw)
        session.load(task_id)
        service.complete()
        self.poll(view)
        self.assertEqual(view.basis_editor.toPlainText(), "Newer saved basis C; proposal B is stale.")
        self.assertEqual(view.proposal_basis_editor.toPlainText(), original)
        self.assertEqual(view.observation_editor.toPlainText(), preview)
        self.assertEqual(session.meaning_text, local)
        self.assertTrue(view.adopt_button.isEnabled())
        self.click(view.adopt_button)
        self.assertIsNone(session.meaning_observation)
        self.assertEqual(view.observation_editor.toPlainText(), "")
        self.assertEqual(service.meaning_choices, [(task_id, observed_revision, current_task_revision)])
        self.assertEqual(session.meaning_proposal, observed_proposal)
        self.assertEqual(session.meaning_revision, observed_revision)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), observed_draft)
        for name in FIELDS:
            self.assertEqual(view.editors[name].toPlainText(), local[name])
        self.assertEqual(session.meaning_text, local)
        self.assertEqual(view.status_label.text(), "UNSAVED")
        self.assertTrue(session.has_unconfirmed)
        self.assertEqual(fixture.meaning_cell(task_id).generation, 2)
        self.poll(view)
        self.assertEqual(view.observation_editor.toPlainText(), "")

    def test_absent_preview_is_readonly_and_clears_on_explicit_choice_keeping_edits(self):
        view, session, service, fixture = self.view()
        task_id = session.task_id
        local = supplied_meaning("local interpretation with no stored proposal")
        self.fill(view, local)
        current_task_revision = session.revision
        self.click(view.load_button)
        self.assertEqual(service.complete().kind, "TASK_MEANING_ABSENT")
        self.poll(view)
        preview = view.observation_editor.toPlainText()
        self.assertIn("Observed stored proposal: ABSENT", preview)
        self.assertIn("Current saved task revision: " + current_task_revision, preview)
        self.assertNotIn("Observed proposal revision:", preview)
        self.assertTrue(view.observation_editor.isReadOnly())
        self.assertEqual(session.meaning_observation, (None, None, current_task_revision))
        self.assertIsNone(session.meaning_proposal)
        self.assertEqual(view.proposal_basis_editor.toPlainText(), "")
        self.assertEqual(session.meaning_text, local)
        for name in FIELDS:
            self.assertEqual(view.editors[name].toPlainText(), local[name])
        self.assertFalse(view.propose_button.isEnabled())
        self.assertTrue(view.adopt_button.isEnabled())
        self.assertEqual(service.meaning_choices, [])
        self.click(view.adopt_button)
        self.assertIsNone(session.meaning_observation)
        self.assertEqual(view.observation_editor.toPlainText(), "")
        self.assertEqual(service.meaning_choices, [(task_id, None, current_task_revision)])
        self.assertEqual(session.meaning_text, local)
        self.assertTrue(session.has_unconfirmed)
        self.assertEqual(fixture.meaning_cell(task_id).generation, 0)
        self.poll(view)
        self.assertEqual(view.observation_editor.toPlainText(), "")


if __name__ == "__main__":
    unittest.main()

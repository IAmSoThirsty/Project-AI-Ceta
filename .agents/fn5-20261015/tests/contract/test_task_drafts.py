"""Durable typed task input on a real journal; no consent/effect qualification.

Kernel tests use explicit synthetic message-bound identity contexts. Native tests
launch the existing Windows service/client/pipe in disposable declared fixtures
without seeding positive owners. Fresh sessions recover CREATED task content;
they do not transfer prepared permissions or infer the user's consent/meaning.
New modules are imported inside helpers/tests so the old source retains separate
missing-module/route failures rather than collapsing discovery into one error.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from fixture_paths import native_fixture_path
import sys
import threading
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.events import StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.kernel_transactions import (PeerIdentity, basis_key, encode_basis,
    task_key, task_wire)
from ceta.contracts.local_ipc import LocalMessage, decode_message, encode_message
from ceta.contracts.store_transactions import STORE_PROFILE, StoreChange, StoreExpectation
from ceta.contracts.wire import ContractError, PROFILE, RecordCodec, canonical_bytes, strict_loads
from ceta.store.journal import SqliteJournal
from test_kernel_transactions import (ADAPTER, INSTALLATION, PROJECT, OWNER_INPUT,
    REGISTRY, SCOPES, CommitBarrierJournal, KernelFixture)
from test_owned_service import _ServiceTestCase


def _owner(principal, sid):
    return "sha256:" + hashlib.sha256(b"CETA:synthetic-task-owner-fixture:v1\0" +
        canonical_bytes({"principal": principal, "sid": sid})).hexdigest()


class _Identity:
    """Synthetic contexts explicitly distinguish principal, session and SID."""
    def __init__(self, principal="operator:fixture", session="session:fixture", sid="SID:fixture"):
        self.context = object()
        self.contexts = {self.context: (PeerIdentity(principal, session), _owner(principal, sid))}
        self.messages, self.checked = {}, []

    def add(self, principal, session, sid="SID:fixture"):
        context = object()
        self.contexts[context] = (PeerIdentity(principal, session), _owner(principal, sid))
        return context

    def authenticate(self, context):
        if context not in self.contexts:
            raise ContractError("FIXTURE_AUTHENTICATION_DENIED")
        return self.contexts[context][0]

    def task_owner_binding(self, context):
        self.authenticate(context)
        return self.contexts[context][1]

    def require_message(self, context, message):
        peer = self.authenticate(context)
        if (self.messages.get(context) != message.original_message
                or message.sender_session != peer.session_id
                or message.scope_id not in SCOPES):
            raise ContractError("FIXTURE_MESSAGE_BINDING_DENIED")
        self.checked.append((context, message))


class _Fixture:
    def __init__(self, schema, *, store=None, root=None, identity=None):
        from ceta.kernel.task_drafts import TaskDrafts
        self.schema, self.codec = schema, RecordCodec(schema)
        self.identity = identity or _Identity()
        self.fail_commit = False
        self.before_commit_action = None
        self.root = root or ROOT / ".agents/fixtures/task-drafts-28" / uuid.uuid4().hex
        if store is None:
            self.root.mkdir(parents=True, exist_ok=False)
            store = CommitBarrierJournal(self.root, self.codec, SCOPES, create=True,
                profile=STORE_PROFILE, before_commit=self.fault)
        self.store = store
        self.tasks = TaskDrafts(store, self.codec, self.identity)
        self.ids, self.last_message = set(), None

    def fault(self):
        if self.fail_commit:
            raise RuntimeError("task fixture after all writer inserts")
        if self.before_commit_action is not None:
            self.before_commit_action()

    def message(self, wire, *, context=None, operation=None):
        from ceta.contracts.task_drafts import decode_command
        context = self.identity.context if context is None else context
        command = decode_command(wire)
        peer = self.identity.authenticate(context)
        operation = operation or "task." + command.as_dict()["kind"]
        envelope = encode_message(wire, self.codec, message_id="message:" + uuid.uuid4().hex,
            sender_session=peer.session_id, receiver_generation="generation:fixture",
            operation=operation, issued_at_ms=1, expires_at_ms=10000,
            correlation_ref="attempt:fixture")
        message = decode_message(envelope, self.codec)
        self.identity.messages[context] = envelope
        self.last_message = message
        if command.as_dict()["task_id"] is not None:
            self.ids.add(command.as_dict()["task_id"])
        return message, context

    def call(self, kind, *, task_id=None, title=None, instruction=None, draft=None,
             expected_revision=None, scope=PROJECT, context=None, command_id=None, wire=None):
        from ceta.contracts.task_drafts import command_wire
        wire = wire or command_wire(kind, scope, command_id or "command:" + uuid.uuid4().hex,
            task_id=task_id, title=title, instruction=instruction, draft=draft,
            expected_revision=expected_revision)
        message, actual = self.message(wire, context=context)
        return self.tasks(message, actual)

    def create(self, task_id="task:typed", *, title="Exact task", instruction="Do not erase.\r\nCafe\u0301.",
               draft="Draft", **kwargs):
        return self.call("create", task_id=task_id, title=title, instruction=instruction, draft=draft, **kwargs)

    def cell(self, key):
        return self.store.snapshot((key,))[0]

    def revision(self, result):
        from ceta.contracts.task_drafts import validate_result
        return validate_result(result, self.last_message.record, self.last_message.operation)

    def cut(self):
        return (self.store.store_position(), tuple(self.store.position(scope) for scope in SCOPES),
                self.raw_rows(), tuple(self.store.replay(scope) for scope in SCOPES))

    def raw_rows(self):
        tables = ("history_meta", "history_scopes", "history_events",
                  "store_commits", "store_changes", "store_cells")
        return tuple((name, tuple(sorted(self.store._connection.execute(
            'SELECT * FROM "' + name + '"').fetchall(), key=repr))) for name in tables)

    def put(self, key, wire):
        """A real owned fixture commit; no projection provenance claim."""
        from test_all_records import example
        cell, point = self.cell(key), self.store.position(key.scope_id)
        payload = example(self.schema["$defs"]["ObservationEnvelope"])
        payload.update(record_id="observation:" + uuid.uuid4().hex, scope_id=key.scope_id)
        payload_wire = canonical_bytes(payload)
        parsed = self.codec.decode(payload_wire)
        event_id = "event:" + uuid.uuid4().hex
        event = {"record_type": "EventRecord", "schema_version": "1", "record_id": event_id,
            "scope_id": key.scope_id, "causation_ref": None, "sequence": point.next_sequence,
            "event_type": "fixture.task.projection", "actor_id": "owner:fixture",
            "actor_session": "session:fixture", "recorded_at": "2026-10-08T12:00:00Z",
            "previous_head": point.head, "payload_ref": parsed.record_id,
            "payload_commitment": parsed.commitment, "canonicalization_profile": PROFILE,
            "signer_key_ref": None, "signature_ref": None}
        return self.store.commit((point,), (JournalEntry(canonical_bytes(event), payload_wire),),
            changes=(StoreChange(StoreExpectation(key, cell.revision), wire, event_id),))

    def reopen(self):
        from ceta.kernel.task_drafts import TaskDrafts
        self.store.close()
        self.store = CommitBarrierJournal(self.root, self.codec, SCOPES, profile=STORE_PROFILE,
            before_commit=self.fault)
        self.tasks = TaskDrafts(self.store, self.codec, self.identity)


class TaskDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)

    def setUp(self):
        self.fixtures, self.kernels = [], []

    def fixture(self, **kwargs):
        result = _Fixture(self.schema, **kwargs)
        self.fixtures.append(result)
        return result

    def tearDown(self):
        for fixture in reversed(self.fixtures):
            fixture.store.close()
        for fixture in reversed(self.kernels):
            fixture.store.close()

    def denied(self, f, action, *, code=None):
        before = f.cut()
        with self.assertRaises(ContractError) as caught:
            action()
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(f.cut(), before, "denied task operation mutated durable state")
        return caught.exception

    def test_exact_crlf_nfd_negation_and_nul_bytes_survive_noncanonical_command(self):
        from ceta.contracts.task_drafts import command_wire, decode_command, decode_snapshot, text_value
        title, instruction, draft = "Cafe\u0301", "NO. Do not remove.\r\nCafe\u0301\x00", "\t  Draft\r\n"
        wire = command_wire("create", PROJECT, "command:exact", task_id="task:exact",
            title=title, instruction=instruction, draft=draft)
        noncanonical = json.dumps(strict_loads(wire), indent=2).encode("utf8")
        parsed = decode_command(noncanonical)
        self.assertEqual(parsed.original_wire, noncanonical)
        self.assertNotEqual(parsed.original_wire, parsed.canonical_wire)
        self.assertEqual(parsed.commitment, decode_command(wire).commitment)
        f = self.fixture()
        result = f.call("create", wire=noncanonical)
        snapshot = decode_snapshot(result.snapshot_wire)
        for name, expected in (("title", title), ("instruction", instruction), ("draft", draft)):
            self.assertEqual(text_value(snapshot[name + "_hex"]).encode("utf8"), expected.encode("utf8"))
        self.assertEqual(snapshot["request_commitment"], parsed.commitment)
        self.assertEqual(f.last_message.record.original_wire, noncanonical)

    def test_text_encoding_and_declared_byte_limits_reject_malformed_inputs(self):
        from ceta.contracts.task_drafts import command_wire, decode_command, text_hex, text_value
        self.assertEqual(text_value(text_hex("\u00e9" * 32768)), "\u00e9" * 32768)
        for text, limit in (("x" * 65537, 65536), ("\u00e9" * 129, 256), ("\ud800", 65536)):
            with self.subTest(text_bytes=len(text), limit=limit):
                with self.assertRaises(ContractError):
                    text_hex(text, maximum=limit)
        for encoded in ("FF", "f", "zz", "ed a0 80", "eda080", "ff", 3, None):
            with self.subTest(encoded=encoded):
                with self.assertRaises(ContractError):
                    text_value(encoded)
        for title, instruction in (("  ", "instruction"), ("title", "\t\r\n")):
            with self.assertRaises(ContractError):
                command_wire("create", PROJECT, "command:empty", task_id="task:empty",
                    title=title, instruction=instruction, draft="")
        base = strict_loads(command_wire("create", PROJECT, "command:hex", task_id="task:hex",
            title="Title", instruction="Instruction", draft=""))
        base["instruction_hex"] = "ff"
        with self.assertRaises(ContractError):
            decode_command(canonical_bytes(base))

    def test_command_shapes_reject_extra_fields_rewritten_original_and_route_substitution(self):
        from ceta.contracts.task_drafts import command_wire, decode_command
        wire = command_wire("save", PROJECT, "command:shape", task_id="task:shape",
            expected_revision="sha256:" + "1" * 64, title="Title", draft="Draft")
        for change in ({"instruction_hex": "61"}, {"allow": True}, {"expected_revision": True},
                       {"kind": "execute"}, {"profile": "ceta-task-command-v2"}):
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    decode_command(canonical_bytes(dict(strict_loads(wire), **change)))
        with self.assertRaises(ContractError):
            encode_message(wire, self.codec, message_id="message:wrong-route", sender_session="session:fixture",
                receiver_generation="generation:fixture", operation="task.create", issued_at_ms=1, expires_at_ms=100)

    def test_catalog_bounds_duplicates_and_owner_scope_are_checked(self):
        from ceta.contracts.task_drafts import CATALOG_PROFILE, decode_catalog
        owner = _owner("operator:fixture", "SID:fixture")
        value = {"profile": CATALOG_PROFILE, "scope_id": PROJECT, "owner_binding": owner,
                 "task_ids": ["task:" + str(i) for i in range(256)]}
        self.assertEqual(len(decode_catalog(canonical_bytes(value), PROJECT, owner)), 256)
        for change in ({"task_ids": value["task_ids"] + ["task:256"]}, {"task_ids": ["task:a", "task:a"]},
                       {"owner_binding": _owner("operator:other", "SID:fixture")}, {"scope_id": INSTALLATION}):
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    decode_catalog(canonical_bytes(dict(value, **change)), PROJECT, owner)

    def test_create_atomically_commits_audited_created_draft_kernel_revision_and_catalog(self):
        from ceta.contracts.task_drafts import catalog_key, decode_snapshot, draft_key
        f = self.fixture()
        before = f.store.store_position()
        result = f.create()
        snapshot = decode_snapshot(result.snapshot_wire)
        revision = f.revision(result)
        owner = f.identity.task_owner_binding(f.identity.context)
        self.assertEqual(result.kind, "TASK_SNAPSHOT")
        self.assertEqual((result.generation, snapshot["objective_generation"], snapshot["state"]), (1, 1, "CREATED"))
        self.assertEqual(set(snapshot["meaning"]), {"clarified_meaning", "scope", "exclusions", "completion_predicates",
            "assumptions", "unresolved_questions", "standing_instructions", "authority", "budgets", "evidence"})
        self.assertTrue(all(value is None for value in snapshot["meaning"].values()))
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        self.assertEqual(f.cell(draft_key(PROJECT, "task:typed")).revision, revision)
        self.assertEqual(f.cell(task_key(PROJECT, "task:typed")).value_wire,
            task_wire(PROJECT, "task:typed", snapshot["objective_revision"]))
        self.assertEqual(strict_loads(f.cell(catalog_key(PROJECT, owner)).value_wire)["task_ids"], ["task:typed"])
        rows = f.store.replay(PROJECT)
        self.assertEqual(len(rows), 1)
        event, payload = self.codec.decode(rows[0].event_wire).as_dict(), self.codec.decode(rows[0].payload_wire).as_dict()
        self.assertEqual((event["event_type"], event["actor_id"], event["actor_session"], event["causation_ref"]),
            ("task.created", "operator:fixture", "session:fixture", f.last_message.record.record_id))
        self.assertEqual(payload["record_type"], "ObservationEnvelope")
        self.assertIsNone(payload["observed_at"])
        self.assertIn("consent", " ".join(payload["uncertainty"]))
        self.assertEqual(f.store._connection.execute(
            "SELECT COUNT(*) FROM store_cells WHERE collection!='projection'").fetchone()[0], 0)
        before_read = f.cut()
        self.assertEqual(f.call("load", task_id="task:typed").snapshot_wire, result.snapshot_wire)
        self.assertEqual(f.cut(), before_read)

    def test_save_keeps_original_instruction_and_advances_atomic_objective_revision(self):
        from ceta.contracts.task_drafts import catalog_key, decode_snapshot, text_value
        f = self.fixture()
        created = f.create(instruction="DO NOT reinterpret this.\r\nCafe\u0301", draft="Original draft")
        first, revision = decode_snapshot(created.snapshot_wire), f.revision(created)
        catalog = f.cell(catalog_key(PROJECT, f.identity.task_owner_binding(f.identity.context)))
        position = f.store.store_position()
        saved = f.call("save", task_id="task:typed", title="Edited title", draft="Exact revised\r\n draft\t",
            expected_revision=revision)
        latest = decode_snapshot(saved.snapshot_wire)
        self.assertEqual(latest["instruction_hex"], first["instruction_hex"])
        self.assertEqual(text_value(latest["draft_hex"]), "Exact revised\r\n draft\t")
        self.assertEqual(latest["created_session"], first["created_session"])
        self.assertEqual(latest["state"], "CREATED")
        self.assertEqual((saved.generation, latest["objective_generation"]), (2, 2))
        self.assertNotEqual(latest["objective_revision"], first["objective_revision"])
        self.assertNotEqual(f.revision(saved), revision)
        self.assertEqual(f.cell(catalog.key), catalog)
        self.assertEqual(f.cell(task_key(PROJECT, "task:typed")).value_wire,
            task_wire(PROJECT, "task:typed", latest["objective_revision"]))
        self.assertEqual(f.store.store_position().next_commit, position.next_commit + 1)
        self.assertEqual(self.codec.decode(f.store.replay(PROJECT)[-1].event_wire).as_dict()["event_type"], "task.draft.saved")

    def test_same_principal_sid_recovers_and_saves_after_reopen_with_fresh_session(self):
        from ceta.contracts.task_drafts import decode_snapshot, draft_key
        f = self.fixture()
        first = f.create()
        before = f.cut()
        f.reopen()
        fresh = f.identity.add("operator:fixture", "session:after-restart")
        loaded = f.call("load", task_id="task:typed", context=fresh)
        self.assertEqual((loaded.snapshot_wire, loaded.generation), (first.snapshot_wire, first.generation))
        self.assertEqual(f.call("list", context=fresh).task_ids, ("task:typed",))
        self.assertEqual(f.cut(), before)
        revision = f.cell(draft_key(PROJECT, "task:typed")).revision
        saved = f.call("save", task_id="task:typed", title="Fresh session edit", draft="New draft",
            expected_revision=revision, context=fresh)
        snapshot = decode_snapshot(saved.snapshot_wire)
        self.assertEqual((snapshot["created_session"], snapshot["updated_session"]),
            ("session:fixture", "session:after-restart"))

    def test_foreign_logical_principal_or_sid_cannot_load_save_or_list_owner_content(self):
        f = self.fixture()
        created = f.create()
        revision = f.revision(created)
        for principal, sid in (("operator:foreign", "SID:fixture"), ("operator:fixture", "SID:foreign")):
            with self.subTest(principal=principal, sid=sid):
                foreign = f.identity.add(principal, "session:foreign", sid)
                self.denied(f, lambda: f.call("load", task_id="task:typed", context=foreign), code="TASK_OWNER_DENIED")
                self.denied(f, lambda: f.call("save", task_id="task:typed", title="Overwrite", draft="Foreign",
                    expected_revision=revision, context=foreign), code="TASK_OWNER_DENIED")
                before = f.cut()
                self.assertEqual(f.call("list", context=foreign).task_ids, ())
                self.assertEqual(f.cut(), before)

    def test_task_scope_isolated_even_when_same_task_identifier_is_reused(self):
        f = self.fixture()
        project = f.create(title="Project private")
        before = f.cut()
        absent = f.call("load", task_id="task:typed", scope=INSTALLATION)
        self.assertEqual((absent.kind, absent.snapshot_wire, absent.generation, absent.task_ids),
            ("TASK_ABSENT", None, 0, ()))
        self.assertEqual(f.cut(), before)
        installation = f.create(scope=INSTALLATION, title="Installation private")
        self.assertNotEqual(project.snapshot_wire, installation.snapshot_wire)
        self.assertEqual(f.call("load", task_id="task:typed").snapshot_wire, project.snapshot_wire)
        self.assertEqual(f.call("load", task_id="task:typed", scope=INSTALLATION).snapshot_wire, installation.snapshot_wire)

    def test_stale_revision_denies_and_exact_noop_retains_event_count_and_revision(self):
        from ceta.contracts.task_drafts import validate_result
        f = self.fixture()
        created = f.create()
        original_revision = f.revision(created)
        saved = f.call("save", task_id="task:typed", title="Changed", draft="Changed", expected_revision=original_revision)
        current_revision = f.revision(saved)
        self.denied(f, lambda: f.call("save", task_id="task:typed", title="Lost update", draft="Lost",
            expected_revision=original_revision), code="TASK_REVISION_CONFLICT")
        before = f.cut()
        same = f.call("save", task_id="task:typed", title="Changed", draft="Changed", expected_revision=current_revision)
        self.assertEqual((same.kind, same.snapshot_wire, same.generation),
            ("TASK_UNCHANGED", saved.snapshot_wire, saved.generation))
        self.assertEqual(validate_result(same, f.last_message.record, "task.save"), current_revision)
        self.assertEqual(f.cut(), before)

    def test_two_real_connections_have_one_save_winner_without_lost_update(self):
        from ceta.contracts.task_drafts import decode_snapshot
        f = self.fixture()
        first = f.create()
        revision = f.revision(first)
        second_store = CommitBarrierJournal(f.root, f.codec, SCOPES, profile=STORE_PROFILE)
        g = self.fixture(store=second_store, root=f.root,
            identity=_Identity(session="session:second-writer"))
        barrier = threading.Barrier(2)
        f.store.commit_barrier = g.store.commit_barrier = barrier

        def saving(target, title):
            try:
                return target.call("save", task_id="task:typed", title=title, draft=title, expected_revision=revision)
            except ContractError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as pool:
            future_a = pool.submit(saving, f, "Winner A")
            future_b = pool.submit(saving, g, "Winner B")
            results = (future_a.result(timeout=30), future_b.result(timeout=30))
        f.store.commit_barrier = g.store.commit_barrier = None
        winners = [result for result in results if not isinstance(result, ContractError)]
        denials = [result for result in results if isinstance(result, ContractError)]
        self.assertEqual((len(winners), len(denials)), (1, 1))
        self.assertIn(denials[0].code, {"JOURNAL_REVISION_CONFLICT", "STORE_REVISION_CONFLICT", "TASK_REVISION_CONFLICT"})
        loaded = f.call("load", task_id="task:typed")
        self.assertEqual(loaded.snapshot_wire, winners[0].snapshot_wire)
        self.assertEqual(decode_snapshot(loaded.snapshot_wire)["objective_generation"], 2)
        self.assertEqual(f.store.store_position().next_commit, 2)

    def test_original_instruction_cannot_be_replaced_by_a_save_command(self):
        from ceta.contracts.task_drafts import command_wire
        f = self.fixture()
        first = f.create(instruction="Original exact instruction")
        revision = f.revision(first)
        wire = command_wire("save", PROJECT, "command:replace-original", task_id="task:typed",
            title="Title", draft="Draft", expected_revision=revision)
        changed = dict(strict_loads(wire), instruction_hex="Replacement".encode("utf8").hex())
        self.denied(f, lambda: f.call("save", wire=canonical_bytes(changed)), code="TASK_ORIGINAL_INSTRUCTION_IMMUTABLE")
        self.assertEqual(f.call("load", task_id="task:typed").snapshot_wire, first.snapshot_wire)

    def test_forged_context_original_message_or_parsed_command_denies_without_writes(self):
        from ceta.contracts.task_drafts import command_wire
        f = self.fixture()
        wire = command_wire("create", PROJECT, "command:forged", task_id="task:forged",
            title="Title", instruction="Instruction", draft="")
        message, context = f.message(wire)
        self.denied(f, lambda: f.tasks(message, object()), code="FIXTURE_AUTHENTICATION_DENIED")
        f.identity.messages[context] = b"different authenticated message"
        self.denied(f, lambda: f.tasks(message, context), code="FIXTURE_MESSAGE_BINDING_DENIED")
        f.identity.messages[context] = message.original_message
        record = replace(message.record, commitment="sha256:" + "f" * 64)
        self.denied(f, lambda: f.tasks(replace(message, record=record), context), code="TASK_MESSAGE_REQUIRED")
        self.denied(f, lambda: f.tasks(replace(message, scope_id=INSTALLATION), context))

    def test_existing_or_tombstoned_kernel_task_key_cannot_be_replaced_by_create(self):
        for value in (task_wire(PROJECT, "task:typed", "sha256:" + "1" * 64), None):
            with self.subTest(tombstone=value is None):
                f = self.fixture()
                if value is None:
                    f.put(task_key(PROJECT, "task:typed"), task_wire(PROJECT, "task:typed", "sha256:" + "1" * 64))
                f.put(task_key(PROJECT, "task:typed"), value)
                self.denied(f, f.create, code="TASK_EXISTS_OR_CONFLICT")

    def test_mismatched_kernel_revision_denies_load_and_save(self):
        f = self.fixture()
        first = f.create()
        revision = f.revision(first)
        f.put(task_key(PROJECT, "task:typed"), task_wire(PROJECT, "task:typed", "sha256:" + "2" * 64))
        self.denied(f, lambda: f.call("load", task_id="task:typed"), code="TASK_KERNEL_REVISION_MISMATCH")
        self.denied(f, lambda: f.call("save", task_id="task:typed", title="Title", draft="Draft",
            expected_revision=revision), code="TASK_KERNEL_REVISION_MISMATCH")

    def test_missing_catalog_membership_or_invalid_catalog_denies_without_repair(self):
        from ceta.contracts.task_drafts import catalog_key
        for change in ({"task_ids": []}, {"task_ids": ["task:typed", "task:typed"]}, {"scope_id": INSTALLATION}):
            with self.subTest(change=change):
                f = self.fixture()
                f.create()
                key = catalog_key(PROJECT, f.identity.task_owner_binding(f.identity.context))
                value = dict(strict_loads(f.cell(key).value_wire), **change)
                f.put(key, canonical_bytes(value))
                self.denied(f, lambda: f.call("load", task_id="task:typed"))

    def test_after_all_insert_failure_rolls_back_create_and_save_before_exact_retry(self):
        from ceta.contracts.task_drafts import command_wire
        for kind in ("create", "save"):
            with self.subTest(kind=kind):
                f = self.fixture()
                revision = None
                if kind == "save":
                    revision = f.revision(f.create())
                wire = command_wire(kind, PROJECT, "command:atomic-" + kind, task_id="task:typed",
                    expected_revision=revision, title="Atomic title", draft="Atomic draft",
                    instruction="Atomic instruction" if kind == "create" else None)
                before = f.cut()
                f.fail_commit = True
                with self.assertRaisesRegex(RuntimeError, "after all writer inserts"):
                    f.call(kind, wire=wire)
                self.assertFalse(f.store._connection.in_transaction)
                self.assertEqual(f.cut(), before)
                f.fail_commit = False
                result = f.call(kind, wire=wire)
                self.assertEqual(result.kind, "TASK_SNAPSHOT")
                self.assertEqual(f.store.store_position().next_commit, before[0].next_commit + 1)

    def test_original_context_invalidated_inside_writer_guard_rolls_back_all_task_values(self):
        f = self.fixture()
        original = f.identity.context
        f.before_commit_action = lambda: f.identity.contexts.pop(original)
        self.denied(f, f.create, code="FIXTURE_AUTHENTICATION_DENIED")
        self.assertEqual(f.store.store_position().next_commit, 0)

    def test_authentication_denial_after_real_commit_keeps_task_and_reconciles_by_load(self):
        from ceta.contracts.task_drafts import decode_snapshot, draft_key
        f = self.fixture()
        original = f.identity.context
        f.store.after_commit = lambda: f.identity.contexts.pop(original)
        with self.assertRaises(ContractError) as caught:
            f.create(instruction="Preserve committed input", draft="Committed draft")
        self.assertEqual(caught.exception.code, "FIXTURE_AUTHENTICATION_DENIED")
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(f.store.store_position().next_commit, 1)
        durable = f.cell(draft_key(PROJECT, "task:typed"))
        self.assertEqual(durable.generation, 1)
        self.assertEqual(bytes.fromhex(decode_snapshot(durable.value_wire)["instruction_hex"]).decode("utf8"),
            "Preserve committed input")
        f.store.after_commit = None
        f.reopen()
        fresh = f.identity.add("operator:fixture", "session:after-denied-return")
        before = f.cut()
        loaded = f.call("load", task_id="task:typed", context=fresh)
        self.assertEqual((loaded.snapshot_wire, loaded.generation), (durable.value_wire, durable.generation))
        self.assertEqual(f.call("list", context=fresh).task_ids, ("task:typed",))
        self.assertEqual(f.cut(), before, "reconciliation performed another write")

    def test_context_and_owner_are_rechecked_after_event_and_after_final_union_read(self):
        from ceta.contracts.task_drafts import command_wire, draft_key
        for variant in ("after_event_invalidated", "after_event_owner_changed", "final_snapshot_invalidated"):
            with self.subTest(variant=variant):
                f = self.fixture()
                created = f.create()
                value = strict_loads(created.snapshot_wire)
                original = f.identity.context
                message, context = f.message(command_wire(
                    "load", PROJECT, "command:recheck", task_id="task:typed"))
                original_replay, original_snapshot = f.store.replay, f.store.snapshot
                original_authenticate = f.identity.authenticate
                reached, auth_after_replay, final_read, contexts = [], [], [], []
                union = {draft_key(PROJECT, "task:typed"), task_key(PROJECT, "task:typed")}

                def authenticate(actual):
                    contexts.append(actual)
                    self.assertIs(actual, original)
                    peer = original_authenticate(actual)
                    if reached:
                        auth_after_replay.append(True)
                    return peer

                def replay_then_invalidate(scope, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope, start, limit, checkpoints=checkpoints)
                    if scope == PROJECT and start == value["event_sequence"] and limit == 1 and not reached:
                        reached.append(True)
                        if variant == "after_event_invalidated":
                            f.identity.contexts.pop(original)
                        elif variant == "after_event_owner_changed":
                            peer, _ = f.identity.contexts[original]
                            f.identity.contexts[original] = (peer, _owner(peer.principal_id, "SID:changed"))
                    return rows

                def snapshot_then_invalidate(keys, *, state_checkpoint=None):
                    cells = original_snapshot(keys, state_checkpoint=state_checkpoint)
                    if (variant == "final_snapshot_invalidated" and reached and auth_after_replay
                            and not final_read and union.issubset(set(keys))):
                        final_read.append(True)
                        f.identity.contexts.pop(original)
                    return cells

                before = f.cut()
                with patch.object(f.identity, "authenticate", authenticate), \
                        patch.object(f.store, "replay", replay_then_invalidate), \
                        patch.object(f.store, "snapshot", snapshot_then_invalidate):
                    with self.assertRaises(ContractError) as caught:
                        f.tasks(message, context)
                self.assertEqual(caught.exception.code, "TASK_CONTEXT_CHANGED" if variant == "after_event_owner_changed"
                    else "FIXTURE_AUTHENTICATION_DENIED")
                self.assertEqual(reached, [True])
                if variant == "final_snapshot_invalidated":
                    self.assertEqual(final_read, [True], "must invalidate the union read after successful post-event authentication")
                self.assertGreaterEqual(len(contexts), 2)
                self.assertEqual(f.cut(), before)

    def test_generation_aba_in_each_selected_read_cell_denies_beyond_injected_commits(self):
        from ceta.contracts.task_drafts import catalog_key, draft_key
        for selected in ("draft", "task", "catalog"):
            with self.subTest(selected=selected):
                f = self.fixture()
                created = f.create()
                value = strict_loads(created.snapshot_wire)
                target = {"draft": draft_key(PROJECT, "task:typed"), "task": task_key(PROJECT, "task:typed"),
                    "catalog": catalog_key(PROJECT, f.identity.task_owner_binding(f.identity.context))}[selected]
                prior_cell = f.cell(target)
                original_replay = f.store.replay
                reached, injected = [], []

                def replay_then_aba(scope, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope, start, limit, checkpoints=checkpoints)
                    if scope == PROJECT and start == value["event_sequence"] and limit == 1 and not reached:
                        reached.append(True)
                        f.put(target, canonical_bytes({"fixture": "ABA intermediary"}))
                        f.put(target, prior_cell.value_wire)
                        injected.append(f.cut())
                    return rows

                with patch.object(f.store, "replay", replay_then_aba):
                    with self.assertRaises(ContractError) as caught:
                        f.call("load", task_id="task:typed")
                self.assertEqual(caught.exception.code, "TASK_READ_CHANGED")
                self.assertEqual(reached, [True])
                self.assertEqual(f.cut(), injected[0], "query wrote beyond explicit fixture ABA")
                current = f.cell(target)
                self.assertEqual((current.value_wire, current.generation), (prior_cell.value_wire, prior_cell.generation + 2))
                self.assertNotEqual(current.revision, prior_cell.revision)

    def test_task_event_actor_session_causation_method_and_payload_association_are_checked(self):
        from ceta.contracts.events import EventContract
        for event_change, payload_change in (({"actor_id": "operator:foreign"}, {}),
                ({"actor_session": "session:foreign"}, {}), ({"causation_ref": "command:foreign"}, {}),
                ({"event_type": "fixture.not-task"}, {}), ({"record_id": "event:foreign"}, {}),
                ({}, {"method": "authenticated.local.foreign"}), ({}, {"payload_commitment": "sha256:" + "a" * 64}),
                ({}, {"observed_at": "2026-10-08T12:00:00Z"}),
                ({}, {"completeness": "UNAVAILABLE"}), ({}, {"epistemic_status": "INFERRED"}),
                ({}, {"sensitivity": "PUBLIC"}), ({}, {"valid_until": "2026-10-09T12:00:00Z"}),
                ({}, {"supersedes": "observation:foreign"}), ({}, {"recorded_at": "2026-10-08T10:00:00Z"})):
            with self.subTest(event_change=event_change, payload_change=payload_change):
                f = self.fixture()
                value = strict_loads(f.create().snapshot_wire)
                original_replay = f.store.replay
                reached = []

                def substituted_replay(scope, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope, start, limit, checkpoints=checkpoints)
                    if scope == PROJECT and start == value["event_sequence"] and limit == 1:
                        event = dict(strict_loads(rows[0].event_wire), **event_change)
                        payload = dict(strict_loads(rows[0].payload_wire), **payload_change)
                        payload_wire = canonical_bytes(payload)
                        if payload_change:
                            event["payload_commitment"] = self.codec.decode(payload_wire).commitment
                            # The substituted row still satisfies the actual
                            # EventContract and record schema. Only the task's
                            # stricter meaning/observation association rejects it.
                            event_wire = canonical_bytes(event)
                            events = EventContract(self.codec)
                            events.require_successor(event_wire, StreamPosition(PROJECT,
                                value["event_sequence"], value["previous_head"]))
                            events.require_payload(event_wire, payload_wire)
                        reached.append(True)
                        return (JournalEntry(canonical_bytes(event), payload_wire),)
                    return rows

                with patch.object(f.store, "replay", substituted_replay):
                    self.denied(f, lambda: f.call("load", task_id="task:typed"),
                        code="TASK_EVENT_BINDING" if payload_change else None)
                self.assertTrue(reached)

    def test_corrupt_real_history_is_preserved_and_denied_without_automatic_repair(self):
        f = self.fixture()
        value = strict_loads(f.create().snapshot_wire)
        f.store._connection.execute("UPDATE history_events SET payload_wire=? WHERE scope_id=? AND sequence=?",
            (b'{"corrupt":"task-history"}', PROJECT, value["event_sequence"]))
        before = f.raw_rows()
        with patch.object(f.store, "commit", side_effect=AssertionError("corrupt load wrote")):
            with self.assertRaises(ContractError):
                f.call("load", task_id="task:typed")
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(f.raw_rows(), before)

    def test_draft_a_to_b_to_a_cannot_revive_an_actual_prepared_kernel_basis(self):
        from ceta.contracts.task_drafts import decode_snapshot
        k = KernelFixture(self.schema)
        self.kernels.append(k)
        identity = _Identity(k.owners.worker.principal_id, k.owners.worker.session_id)
        f = self.fixture(store=k.store, root=k.root, identity=identity)
        created = f.create("task:typed-authority", title="Title A", draft="Draft A")
        first = decode_snapshot(created.snapshot_wire)
        original_revision = f.revision(created)
        proposal = dict(k.proposal, record_id="proposal:typed-authority", task_id="task:typed-authority")
        proposal_wire = canonical_bytes(proposal)
        grant = dict(k.grant, purpose_ref="task:typed-authority")
        k.grant_wire = canonical_bytes(grant)
        k.put(k.grant_key, k.grant_wire)
        basis = encode_basis(self.codec.decode(proposal_wire), k.grant_key, k.read_set,
            principal_id=k.owners.worker.principal_id, actor_session=k.owners.worker.session_id,
            adapter_commitment=ADAPTER, registry_commitment=REGISTRY, owner_input_commitment=OWNER_INPUT,
            candidate_commitment=None, task_revision=first["objective_revision"],
            review_refs=("review:fixture",), approval_evidence_ref="evidence:fixture-approval")
        k.allow(proposal_wire, basis)
        k.put(basis_key(PROJECT, "proposal:typed-authority"), basis)
        prepared = k.service.prepare(proposal_wire, k.owners.worker_context)
        changed = f.call("save", task_id="task:typed-authority", title="Title B", draft="Draft B",
            expected_revision=original_revision)
        restored = f.call("save", task_id="task:typed-authority", title="Title A", draft="Draft A",
            expected_revision=f.revision(changed))
        final = decode_snapshot(restored.snapshot_wire)
        self.assertEqual((final["title_hex"], final["instruction_hex"], final["draft_hex"]),
            (first["title_hex"], first["instruction_hex"], first["draft_hex"]))
        self.assertEqual(final["objective_generation"], first["objective_generation"] + 2)
        self.assertNotEqual(final["objective_revision"], first["objective_revision"])
        fresh_proposal = dict(proposal, record_id="proposal:typed-authority-after-aba")
        fresh_wire = canonical_bytes(fresh_proposal)
        stale_basis = encode_basis(self.codec.decode(fresh_wire), k.grant_key, k.read_set,
            principal_id=k.owners.worker.principal_id, actor_session=k.owners.worker.session_id,
            adapter_commitment=ADAPTER, registry_commitment=REGISTRY, owner_input_commitment=OWNER_INPUT,
            candidate_commitment=None, task_revision=first["objective_revision"],
            review_refs=("review:fixture",), approval_evidence_ref="evidence:fixture-approval")
        k.allow(fresh_wire, stale_basis)
        k.put(basis_key(PROJECT, fresh_proposal["record_id"]), stale_basis)
        before, budget = f.cut(), k.budget()
        with self.assertRaises(ContractError) as caught:
            k.service.prepare(fresh_wire, k.owners.worker_context)
        self.assertEqual(caught.exception.code, "KERNEL_TASK_REVISION_CHANGED")
        self.assertEqual(f.cut(), before)
        self.assertEqual(k.budget(), budget)
        with self.assertRaises(ContractError) as caught:
            k.service.consume(prepared.record_wire, k.owners.worker_context)
        self.assertEqual(caught.exception.code, "KERNEL_RELEVANT_STATE_CHANGED")
        self.assertEqual(f.cut(), before)
        self.assertEqual(k.budget(), budget)

    def test_task_result_binds_command_scope_content_generation_and_unchanged_revision(self):
        from ceta.contracts.task_drafts import (command_wire, decode_command, TaskResult,
            task_content_revision, validate_result)
        f = self.fixture()
        result = f.create()
        command = f.last_message.record
        expected = f.revision(result)
        self.assertEqual(validate_result(result, command, "task.create"), expected)
        for change in ({"task_id": "task:other"}, {"scope_id": INSTALLATION}, {"request_id": "command:other"},
                       {"title_hex": "Changed".encode("utf8").hex()}, {"instruction_hex": "Changed".encode("utf8").hex()},
                       {"request_commitment": "sha256:" + "1" * 64}, {"state": "AUTHORIZED"}):
            with self.subTest(change=change):
                snapshot = dict(strict_loads(result.snapshot_wire), **change)
                snapshot["objective_revision"] = task_content_revision(snapshot)
                with self.assertRaises(ContractError):
                    validate_result(replace(result, snapshot_wire=canonical_bytes(snapshot)), command, "task.create")
        with self.assertRaises(ContractError):
            validate_result(replace(result, generation=result.generation + 1), command, "task.create")
        with self.assertRaises(ContractError):
            validate_result(replace(result, kind="TASK_UNCHANGED"), command, "task.create")
        save = decode_command(command_wire("save", PROJECT, "command:noop-binding", task_id="task:typed",
            title="Exact task", draft="Draft", expected_revision=expected))
        unchanged = TaskResult("TASK_UNCHANGED", result.snapshot_wire, result.generation)
        self.assertEqual(validate_result(unchanged, save, "task.save"), expected)
        wrong = replace(save, commitment="sha256:" + "2" * 64)
        with self.assertRaises(ContractError):
            validate_result(unchanged, wrong, "task.save")
        bad_save = decode_command(command_wire("save", PROJECT, "command:stale-noop", task_id="task:typed",
            title="Exact task", draft="Draft", expected_revision="sha256:" + "3" * 64))
        with self.assertRaises(ContractError):
            validate_result(unchanged, bad_save, "task.save")

    def test_ingress_forwards_exact_original_message_and_context_to_the_captured_task_owner(self):
        from ceta.application.ipc_service import KernelIngress
        from ceta.contracts.task_drafts import command_wire
        f = self.fixture()
        wire = command_wire("create", PROJECT, "command:forward", task_id="task:forward",
            title="Title", instruction="Do not rewrite", draft="")
        exact = json.dumps(strict_loads(wire), indent=3).encode("utf8")
        message, context = f.message(exact)
        calls = []
        marker = object()

        def captured(actual_message, actual_context):
            calls.append((actual_message, actual_context))
            self.assertIs(actual_message, message)
            self.assertIs(actual_context, context)
            self.assertEqual(actual_message.record.original_wire, exact)
            return marker

        self.assertIs(KernelIngress(object(), f.identity, captured)(message, context), marker)
        self.assertEqual(calls, [(message, context)])
        self.assertTrue(all(actual is context for actual, _ in f.identity.checked))
        before = f.cut()
        with self.assertRaises(ContractError) as caught:
            KernelIngress(object(), f.identity)(message, context)
        self.assertEqual(caught.exception.code, "TASK_OWNER_UNAVAILABLE")
        self.assertEqual(f.cut(), before)

    def test_correlated_task_response_rejects_request_route_session_and_revision_substitution(self):
        from ceta.contracts.local_results import encode_response, decode_response
        f = self.fixture()
        result = f.create()
        request = f.last_message
        wire = encode_response(request, result, self.codec)
        observed = decode_response(wire, request, self.codec)
        self.assertEqual(observed.task_result, result)
        self.assertEqual(observed.original_response, wire)
        self.assertIsNone(observed.record_wire)
        self.assertIsNone(observed.event_wire)
        self.assertIsNone(observed.prior_position)
        for change in ({"message_id": "message:other"}, {"operation": "task.load"}, {"sender_session": "session:other"},
                       {"request_sha256": "f" * 64}, {"revision": "sha256:" + "f" * 64},
                       {"generation": result.generation + 1}, {"kind": "COMMITTED"}):
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    decode_response(canonical_bytes(dict(strict_loads(wire), **change)), request, self.codec)
        snapshot = dict(strict_loads(result.snapshot_wire), updated_session="session:other")
        forged = replace(result, snapshot_wire=canonical_bytes(snapshot))
        with self.assertRaises(ContractError):
            encode_response(request, forged, self.codec)
        denied = decode_response(encode_response(request, ContractError("TASK_REVISION_CONFLICT"), self.codec), request, self.codec)
        self.assertEqual(denied.kind, "DENIED_RECONCILE")
        self.assertIsNone(denied.task_result)

    def test_malformed_list_results_deny_boolean_generation_and_unhashable_identifiers(self):
        from ceta.contracts.local_results import encode_response, decode_response
        f = self.fixture()
        f.create()
        listing = f.call("list")
        request = f.last_message
        wire = encode_response(request, listing, self.codec)
        self.assertEqual(decode_response(wire, request, self.codec).task_result, listing)
        for change in ({"generation": False}, {"task_ids": [["task:typed"]]},
                       {"task_ids": [{"task_id": "task:typed"}]}, {"kind": []}, {"kind": {}}):
            with self.subTest(change=change):
                substituted = canonical_bytes(dict(strict_loads(wire), **change))
                with self.assertRaises(ContractError):
                    # A TypeError is a failure: malformed wire input must be a
                    # typed protocol denial rather than escape the decoder.
                    decode_response(substituted, request, self.codec)

    def test_absent_requires_current_never_present_cells_and_owner_catalog_exclusion(self):
        from ceta.contracts.task_drafts import catalog_key, draft_key, validate_result
        f = self.fixture()
        for populated in (False, True):
            with self.subTest(populated_owner_catalog=populated):
                if populated:
                    f.create("task:other")
                before = f.cut()
                absent = f.call("load", task_id="task:never-present")
                self.assertEqual((absent.kind, absent.snapshot_wire, absent.generation, absent.task_ids),
                    ("TASK_ABSENT", None, 0, ()))
                self.assertIsNone(validate_result(absent, f.last_message.record, "task.load"))
                for key in (draft_key(PROJECT, "task:never-present"), task_key(PROJECT, "task:never-present")):
                    self.assertEqual((f.cell(key).generation, f.cell(key).value_wire), (0, None))
                catalog = f.cell(catalog_key(PROJECT, f.identity.task_owner_binding(f.identity.context)))
                if catalog.value_wire is not None:
                    self.assertNotIn("task:never-present", strict_loads(catalog.value_wire)["task_ids"])
                self.assertEqual(f.cut(), before, "current absence observation wrote or created a tombstone")

    def test_absent_is_denied_for_tombstones_foreign_collisions_or_catalog_only_references(self):
        from ceta.contracts.task_drafts import CATALOG_PROFILE, catalog_key, draft_key
        for variant in ("draft_tombstone", "task_tombstone", "catalog_tombstone", "kernel_collision", "catalog_reference", "foreign_task"):
            with self.subTest(variant=variant):
                f = self.fixture()
                context = None
                if variant == "draft_tombstone":
                    f.put(draft_key(PROJECT, "task:typed"), canonical_bytes({"fixture": "existing draft before deletion"}))
                    f.put(draft_key(PROJECT, "task:typed"), None)
                elif variant == "task_tombstone":
                    f.put(task_key(PROJECT, "task:typed"), task_wire(PROJECT, "task:typed", "sha256:" + "a" * 64))
                    f.put(task_key(PROJECT, "task:typed"), None)
                elif variant == "catalog_tombstone":
                    owner = f.identity.task_owner_binding(f.identity.context)
                    f.put(catalog_key(PROJECT, owner), canonical_bytes({"profile": CATALOG_PROFILE,
                        "scope_id": PROJECT, "owner_binding": owner, "task_ids": []}))
                    f.put(catalog_key(PROJECT, f.identity.task_owner_binding(f.identity.context)), None)
                elif variant == "kernel_collision":
                    f.put(task_key(PROJECT, "task:typed"), task_wire(PROJECT, "task:typed", "sha256:" + "a" * 64))
                elif variant == "catalog_reference":
                    owner = f.identity.task_owner_binding(f.identity.context)
                    f.put(catalog_key(PROJECT, owner), canonical_bytes({"profile": CATALOG_PROFILE,
                        "scope_id": PROJECT, "owner_binding": owner, "task_ids": ["task:typed"]}))
                else:
                    f.create()
                    context = f.identity.add("operator:foreign", "session:foreign")
                self.denied(f, lambda: f.call("load", task_id="task:typed", context=context),
                    code="TASK_OWNER_DENIED" if variant == "foreign_task" else None if variant == "catalog_tombstone" else "TASK_NOT_FOUND")

    def test_absent_rechecks_each_selected_cell_generation_and_original_context_after_last_read(self):
        from ceta.contracts.task_drafts import catalog_key, command_wire, draft_key
        for variant in ("draft_generation_changed", "task_generation_changed", "catalog_generation_changed", "last_read_context_invalidated"):
            with self.subTest(variant=variant):
                f = self.fixture()
                message, context = f.message(command_wire("load", PROJECT, "command:absence-boundary", task_id="task:absent"))
                original_snapshot, original_authenticate = f.store.snapshot, f.identity.authenticate
                union = {draft_key(PROJECT, "task:absent"), task_key(PROJECT, "task:absent")}
                first_read, post_read_authentication, injected, last_read = [], [], [], []

                def authenticate(actual):
                    self.assertIs(actual, context)
                    peer = original_authenticate(actual)
                    if first_read:
                        post_read_authentication.append(True)
                    return peer

                def snapshot_then_change(keys, *, state_checkpoint=None):
                    cells = original_snapshot(keys, state_checkpoint=state_checkpoint)
                    if union.issubset(set(keys)) and not first_read:
                        first_read.append(True)
                        if variant != "last_read_context_invalidated":
                            target = {"draft_generation_changed": draft_key(PROJECT, "task:absent"),
                                "task_generation_changed": task_key(PROJECT, "task:absent"),
                                "catalog_generation_changed": catalog_key(PROJECT, f.identity.task_owner_binding(context))}[variant]
                            f.put(target, canonical_bytes({"fixture": "present then tombstoned"}))
                            f.put(target, None)
                            injected.append(f.cut())
                    elif (union.issubset(set(keys)) and post_read_authentication
                            and variant == "last_read_context_invalidated" and not last_read):
                        last_read.append(True)
                        f.identity.contexts.pop(context)
                    return cells

                before = f.cut()
                with patch.object(f.identity, "authenticate", authenticate), \
                        patch.object(f.store, "snapshot", snapshot_then_change):
                    with self.assertRaises(ContractError) as caught:
                        f.tasks(message, context)
                self.assertEqual(first_read, [True])
                if variant == "last_read_context_invalidated":
                    self.assertEqual(caught.exception.code, "FIXTURE_AUTHENTICATION_DENIED")
                    self.assertEqual(last_read, [True])
                    self.assertEqual(f.cut(), before)
                else:
                    self.assertEqual(caught.exception.code, "TASK_READ_CHANGED")
                    self.assertEqual(f.cut(), injected[0], "absence query wrote beyond the explicit fixture commits")

    def test_absent_result_rejects_other_routes_types_generations_and_embedded_content(self):
        from ceta.contracts.local_results import decode_response, encode_response
        from ceta.contracts.task_drafts import TaskResult, command_wire, decode_command, validate_result
        f = self.fixture()
        result = f.call("load", task_id="task:absent")
        request = f.last_message
        self.assertEqual(result.kind, "TASK_ABSENT")
        wire = encode_response(request, result, self.codec)
        self.assertEqual(decode_response(wire, request, self.codec).task_result, result)
        self.assertIsNone(validate_result(result, request.record, "task.load"))
        for changed in (replace(result, generation=False), replace(result, generation=1),
                        replace(result, snapshot_wire=b"{}"), replace(result, task_ids=("task:absent",)),
                        replace(result, kind=[]), replace(result, kind={})): 
            with self.subTest(changed=changed):
                with self.assertRaises(ContractError):
                    validate_result(changed, request.record, "task.load")
                with self.assertRaises(ContractError):
                    encode_response(request, changed, self.codec)
        for kind in ("create", "save", "list"):
            with self.subTest(route=kind):
                command = decode_command(command_wire(kind, PROJECT, "command:wrong-absence-route", 
                    task_id=None if kind == "list" else "task:absent",
                    title=None if kind == "list" else "Title", draft=None if kind == "list" else "",
                    instruction="Instruction" if kind == "create" else None,
                    expected_revision="sha256:" + "1" * 64 if kind == "save" else None))
                with self.assertRaises(ContractError):
                    validate_result(TaskResult("TASK_ABSENT"), command, "task." + kind)
        for change in ({"kind": []}, {"kind": {}}, {"generation": False}, {"snapshot_wire": "{}"},
                       {"task_ids": ["task:absent"]}, {"scope_id": INSTALLATION}, {"revision": "sha256:" + "a" * 64}):
            with self.subTest(wire_change=change):
                with self.assertRaises(ContractError):
                    decode_response(canonical_bytes(dict(strict_loads(wire), **change)), request, self.codec)


class NativeTaskDraftTests(_ServiceTestCase):
    """Real Windows fixtures; controlled missing-pipe and capacity seams disclosed.

    A redirected single attempt still uses the real client/native API and real
    later authenticated reads. The redirection is a controlled failure stimulus,
    not native security qualification or proof of any historical rollback.
    """
    def empty_service(self, *, root=None, principal="operator:development"):
        from ceta.composition.owned_service import OwnedService
        selected = root or self.directory()
        result = OwnedService(selected, self.codec, INSTALLATION, SCOPES,
            create=root is None, principal_id=principal)
        self.services.append(result)
        self.ready(result)
        self.assertEqual(result.poll()["authority"], "CLOSED")
        return result, selected

    def task_call(self, service, kind, *, task_id=None, title=None, instruction=None, draft=None,
                  expected_revision=None, command_id=None, scope=PROJECT):
        from ceta.contracts.task_drafts import command_wire
        self.until(lambda: service.poll()["state"] in {"READY", "RECOVERING"}
            and service._send_task is None and service._pending is None,
            explanation="previous exact call/send lifetime was not retired")
        wire = command_wire(kind, scope, command_id or "command:" + uuid.uuid4().hex,
            task_id=task_id, title=title, instruction=instruction, draft=draft, expected_revision=expected_revision)
        attempt, response = self.call(service, wire, "task." + kind)
        self.assertEqual(service.poll()["authority"], "CLOSED")
        return attempt, response

    def missing_pipe_task_attempt(self, service, kind, *, task_id, title="Uncertain title",
                                  instruction=None, draft="", expected_revision=None, scope=PROJECT):
        """One disclosed failure of actual native transport, exact request retained."""
        from ceta.contracts.task_drafts import command_wire
        self.until(lambda: service.poll()["state"] == "READY"
            and service._send_task is None and service._pending is None)
        wire = command_wire(kind, scope, "command:" + uuid.uuid4().hex, task_id=task_id,
            title=title, instruction=instruction, draft=draft, expected_revision=expected_revision)
        original_send = service._client.send
        missing_pipe = r"\\.\pipe\CETA-" + uuid.uuid4().hex
        dispatched = []

        def actual_send_to_missing_pipe(command):
            self.assertEqual(command["pipe"], service._pipe)
            redirected = dict(command, pipe=missing_pipe, timeout_ms=100)
            dispatched.append((dict(command), redirected))
            return original_send(redirected)

        with patch.object(service._client, "send", actual_send_to_missing_pipe):
            attempt = service.begin_call(wire, "task." + kind)

            def uncertain_observed():
                snapshot = service.poll()
                call = snapshot.get("call")
                return call if (snapshot["state"] == "RECOVERING" and call is not None
                    and call["attempt"] == attempt and call["kind"] == "TRANSPORT_UNCERTAIN"
                    and service._pending is None and service._send_task is None) else None

            call = self.until(uncertain_observed,
                explanation="real native client did not report/retire the controlled missing-pipe attempt")
        self.assertEqual(len(dispatched), 1)
        self.assertNotEqual(dispatched[0][1]["pipe"], service._pipe)
        request_wire = (native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes()
        request = decode_message(request_wire, self.codec)
        self.assertEqual(request.record.original_wire, wire)
        self.assertEqual(service._uncertain_task_request, request)
        self.assertNotIn("response", call)
        self.assertFalse((native_fixture_path(service._spool / (attempt + ".response.json"))).exists())
        self.assertIsNone(service._client.process.poll())
        self.assertIsNone(service._service.process.poll())
        self.assertEqual(service.poll()["authority"], "CLOSED")
        return attempt, request

    def response_revision(self, response):
        from ceta.contracts.store_transactions import StoreCell
        from ceta.contracts.task_drafts import draft_key
        snapshot = strict_loads(response.task_result.snapshot_wire)
        return StoreCell(draft_key(snapshot["scope_id"], snapshot["task_id"]),
            response.task_result.generation, response.task_result.snapshot_wire).revision

    def durable_cut(self, root):
        store = SqliteJournal(root, self.codec, SCOPES, profile=STORE_PROFILE)
        try:
            tables = ("history_meta", "history_scopes", "history_events", "store_commits", "store_changes", "store_cells")
            rows = tuple((name, tuple(sorted(store._connection.execute(
                'SELECT * FROM "' + name + '"').fetchall(), key=repr))) for name in tables)
            return (store.store_position(), rows)
        finally:
            store.close()

    def test_actual_create_save_list_restart_load_preserves_exact_text_under_fresh_session(self):
        from ceta.contracts.task_drafts import decode_snapshot, text_value
        service, root = self.empty_service()
        _, created = self.task_call(service, "create", task_id="task:native", title="Cafe\u0301",
            instruction="NO. Do not delete.\r\nCafe\u0301", draft="Exact draft\r\n")
        self.assertEqual(created.kind, "TASK_SNAPSHOT")
        _, saved = self.task_call(service, "save", task_id="task:native", title="Edited title", draft="Final \t draft\r\n",
            expected_revision=self.response_revision(created))
        self.assertEqual(saved.kind, "TASK_SNAPSHOT")
        snapshot = decode_snapshot(saved.task_result.snapshot_wire)
        self.assertEqual(text_value(snapshot["instruction_hex"]), "NO. Do not delete.\r\nCafe\u0301")
        self.assertEqual(text_value(snapshot["draft_hex"]), "Final \t draft\r\n")
        _, listing = self.task_call(service, "list")
        self.assertEqual((listing.kind, listing.task_result.task_ids), ("TASK_LIST", ("task:native",)))
        self.stop(service)
        before = self.durable_cut(root)
        restarted, _ = self.empty_service(root=root)
        self.assertNotEqual(service._session, restarted._session)
        self.assertNotEqual(service.generation, restarted.generation)
        _, loaded = self.task_call(restarted, "load", task_id="task:native")
        self.assertEqual(loaded.task_result, saved.task_result)
        self.stop(restarted)
        self.assertEqual(self.durable_cut(root), before)

    def test_actual_other_launcher_bound_logical_principal_is_denied_owner_task_content(self):
        service, root = self.empty_service()
        _, created = self.task_call(service, "create", task_id="task:private", title="Private task",
            instruction="Private instruction", draft="Private draft")
        self.assertEqual(created.kind, "TASK_SNAPSHOT")
        self.stop(service)
        before = self.durable_cut(root)
        foreign, _ = self.empty_service(root=root, principal="operator:foreign")
        _, denied = self.task_call(foreign, "load", task_id="task:private")
        self.assertEqual((denied.kind, denied.error_code), ("DENIED_RECONCILE", "TASK_OWNER_DENIED"))
        self.assertIsNone(denied.task_result)
        _, listing = self.task_call(foreign, "list")
        self.assertEqual(listing.task_result.task_ids, ())
        self.stop(foreign)
        self.assertEqual(self.durable_cut(root), before)

    def test_actual_stale_save_denies_then_load_reconciles_without_losing_current_draft(self):
        from ceta.contracts.task_drafts import decode_snapshot, text_value
        service, root = self.empty_service()
        _, first = self.task_call(service, "create", task_id="task:cas", title="Title", instruction="Immutable", draft="First")
        initial_revision = self.response_revision(first)
        _, current = self.task_call(service, "save", task_id="task:cas", title="Current", draft="Current draft",
            expected_revision=initial_revision)
        stale_attempt, denied = self.task_call(service, "save", task_id="task:cas", title="Lost update", draft="Lost draft",
            expected_revision=initial_revision, command_id="command:native-stale")
        self.assertEqual((denied.kind, denied.error_code), ("DENIED_RECONCILE", "TASK_REVISION_CONFLICT"))
        self.assertIsNone(denied.task_result)
        self.until(lambda: service.poll()["state"] == "RECOVERING" and service._send_task is None)
        retained = decode_message((native_fixture_path(service._spool / (stale_attempt + ".request.json"))).read_bytes(), self.codec)
        self.assertEqual(retained.record.as_dict()["expected_revision"], initial_revision)
        self.assertEqual(retained.record.record_id, "command:native-stale")
        _, loaded = self.task_call(service, "load", task_id="task:cas")
        self.assertEqual(loaded.task_result, current.task_result)
        self.assertEqual(text_value(decode_snapshot(loaded.task_result.snapshot_wire)["draft_hex"]), "Current draft")
        self.stop(service)
        position, _ = self.durable_cut(root)
        self.assertEqual(position.next_commit, 2)

    def test_actual_task_capture_leaves_effect_authority_closed_and_recovery_read_only(self):
        from test_all_records import example
        service, root = self.empty_service()
        _, created = self.task_call(service, "create", task_id="task:no-authority", title="Task",
            instruction="User input alone is not authority", draft="")
        self.until(lambda: service.poll()["state"] == "READY" and service._send_task is None)
        proposal = example(self.schema["$defs"]["ActionProposal"])
        proposal.update(record_id="proposal:no-task-authority", scope_id=PROJECT, task_id="task:no-authority")
        _, denial = self.call(service, canonical_bytes(proposal), "kernel.prepare")
        self.assertEqual(denial.kind, "DENIED_RECONCILE")
        self.assertIsNone(denial.record_wire)
        self.assertEqual(service.poll()["authority"], "CLOSED")
        self.until(lambda: service.poll()["state"] == "RECOVERING" and service._send_task is None)
        _, loaded = self.task_call(service, "load", task_id="task:no-authority")
        self.assertEqual(loaded.task_result, created.task_result)
        self.assertEqual(service.poll()["state"], "RECOVERING",
            "a successful task read must not clear prior kernel uncertainty")
        self.assertIsNone(service._uncertain_task_request)
        with self.assertRaises(ContractError) as caught:
            service.acknowledge_task_reconciliation("task:no-authority", self.response_revision(loaded))
        self.assertEqual(caught.exception.code, "SERVICE_TASK_RECONCILIATION_NOT_MATCHED")
        _, listing = self.task_call(service, "list")
        self.assertEqual(listing.task_result.task_ids, ("task:no-authority",))
        self.assertEqual(service.poll()["state"], "RECOVERING")
        self.assertEqual(service._task_reconciliation_history, [])
        self.stop(service)
        store = SqliteJournal(root, self.codec, SCOPES, profile=STORE_PROFILE)
        try:
            self.assertEqual(store.store_position().next_commit, 1)
            self.assertEqual(store._connection.execute(
                "SELECT COUNT(*) FROM store_cells WHERE collection!='projection'").fetchone()[0], 0)
            self.assertEqual(len(store.replay(PROJECT)), 1)
        finally:
            store.close()

    def test_actual_uncertain_create_current_absence_requires_explicit_ack_without_rollback_claim(self):
        service, root = self.empty_service()
        attempt, request = self.missing_pipe_task_attempt(service, "create", task_id="task:uncertain-create",
            instruction="Exact original uncertain create", draft="Preserve me")
        retained_path = service._spool / (attempt + ".request.json")
        retained_wire = native_fixture_path(retained_path).read_bytes()
        _, absent = self.task_call(service, "load", task_id="task:uncertain-create")
        self.assertEqual((absent.kind, absent.task_result.snapshot_wire, absent.task_result.generation),
            ("TASK_ABSENT", None, 0))
        self.assertEqual(service.poll()["state"], "RECOVERING")
        self.assertEqual(service._uncertain_task_request, request)
        self.assertEqual(service._task_reconciliation_history, [])
        service.acknowledge_task_reconciliation("task:uncertain-create", None)
        self.assertEqual(service.poll()["state"], "READY")
        self.assertIsNone(service._uncertain_task_request)
        self.assertEqual(len(service._task_reconciliation_history), 1)
        preserved = service._task_reconciliation_history[0]
        self.assertEqual(preserved[:2], (request.original_message, absent.original_response))
        self.assertIn("PRIOR_WRITE_HISTORY_UNRESOLVED", preserved[2])
        self.assertEqual(native_fixture_path(retained_path).read_bytes(), retained_wire)
        _, created = self.task_call(service, "create", task_id="task:uncertain-create", title="Selected next create",
            instruction="Explicit new create after current absence observation", draft="Current draft")
        self.assertEqual(created.kind, "TASK_SNAPSHOT")
        self.assertEqual(native_fixture_path(retained_path).read_bytes(), retained_wire)
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 1)

    def test_actual_wrong_scope_same_id_absence_cannot_acknowledge_uncertain_create(self):
        service, root = self.empty_service()
        _, request = self.missing_pipe_task_attempt(service, "create", task_id="task:scope-collision",
            instruction="Project task request", scope=PROJECT)
        _, installation_absent = self.task_call(service, "load", task_id="task:scope-collision", scope=INSTALLATION)
        self.assertEqual(installation_absent.kind, "TASK_ABSENT")
        self.assertEqual(service._observed_task_snapshot[3], INSTALLATION)
        with self.assertRaises(ContractError) as caught:
            service.acknowledge_task_reconciliation("task:scope-collision", None)
        self.assertEqual(caught.exception.code, "SERVICE_TASK_RECONCILIATION_SCOPE")
        self.assertEqual(service._uncertain_task_request, request)
        self.assertEqual(service.poll()["state"], "RECOVERING")
        self.assertEqual(service._task_reconciliation_history, [])
        _, project_absent = self.task_call(service, "load", task_id="task:scope-collision", scope=PROJECT)
        self.assertEqual(project_absent.kind, "TASK_ABSENT")
        service.acknowledge_task_reconciliation("task:scope-collision", None)
        self.assertEqual(service.poll()["state"], "READY")
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 0)

    def test_actual_stale_prewrite_task_observation_is_invalidated_and_save_absence_cannot_ack(self):
        service, root = self.empty_service()
        _, created = self.task_call(service, "create", task_id="task:stale-observation", title="Current",
            instruction="Immutable", draft="Draft")
        _, prior_load = self.task_call(service, "load", task_id="task:stale-observation")
        old_revision = self.response_revision(prior_load)
        self.assertIsNotNone(service._observed_task_snapshot)
        _, denied = self.task_call(service, "save", task_id="task:stale-observation", title="Attempt",
            draft="Denied change", expected_revision="sha256:" + "f" * 64)
        self.assertEqual(denied.error_code, "TASK_REVISION_CONFLICT")
        self.assertIsNone(service._observed_task_snapshot)
        with self.assertRaises(ContractError) as caught:
            service.acknowledge_task_reconciliation("task:stale-observation", old_revision)
        self.assertEqual(caught.exception.code, "SERVICE_TASK_OBSERVATION_REQUIRED")
        _, current = self.task_call(service, "load", task_id="task:stale-observation")
        self.assertEqual(current.task_result, created.task_result)
        service.acknowledge_task_reconciliation("task:stale-observation", self.response_revision(current))
        self.assertEqual(service.poll()["state"], "READY")
        _, missing_save = self.task_call(service, "save", task_id="task:never-created-save", title="Absent save",
            draft="No task exists", expected_revision="sha256:" + "a" * 64)
        self.assertEqual(missing_save.kind, "DENIED_RECONCILE")
        _, absent = self.task_call(service, "load", task_id="task:never-created-save")
        self.assertEqual(absent.kind, "TASK_ABSENT")
        uncertain = service._uncertain_task_request
        with self.assertRaises(ContractError) as caught:
            service.acknowledge_task_reconciliation("task:never-created-save", None)
        self.assertEqual(caught.exception.code, "SERVICE_TASK_ABSENCE_REQUIRES_CREATE")
        self.assertIs(service._uncertain_task_request, uncertain)
        self.assertEqual(service.poll()["state"], "RECOVERING")
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 1)

    def test_actual_unrelated_present_absent_and_list_reads_preserve_original_task_uncertainty(self):
        service, root = self.empty_service()
        _, original = self.task_call(service, "create", task_id="task:uncertain-original", title="Original",
            instruction="Original instruction", draft="Original draft")
        _, unrelated = self.task_call(service, "create", task_id="task:unrelated", title="Other",
            instruction="Other instruction", draft="Other draft")
        _, denied = self.task_call(service, "save", task_id="task:uncertain-original", title="Stale attempt",
            draft="Stale draft", expected_revision="sha256:" + "f" * 64)
        self.assertEqual(denied.error_code, "TASK_REVISION_CONFLICT")
        request = service._uncertain_task_request
        _, unrelated_load = self.task_call(service, "load", task_id="task:unrelated")
        self.assertEqual(unrelated_load.task_result, unrelated.task_result)
        with self.assertRaises(ContractError) as caught:
            service.acknowledge_task_reconciliation("task:unrelated", self.response_revision(unrelated_load))
        self.assertEqual(caught.exception.code, "SERVICE_TASK_RECONCILIATION_NOT_MATCHED")
        _, absence = self.task_call(service, "load", task_id="task:unrelated-absent")
        self.assertEqual(absence.kind, "TASK_ABSENT")
        _, listing = self.task_call(service, "list")
        self.assertEqual(set(listing.task_result.task_ids), {"task:uncertain-original", "task:unrelated"})
        self.assertEqual(service.poll()["state"], "RECOVERING")
        self.assertIs(service._uncertain_task_request, request)
        self.assertEqual(service._task_reconciliation_history, [])
        _, current = self.task_call(service, "load", task_id="task:uncertain-original")
        self.assertEqual(current.task_result, original.task_result)
        self.assertEqual(service.poll()["state"], "RECOVERING")
        service.acknowledge_task_reconciliation("task:uncertain-original", self.response_revision(current))
        self.assertEqual(service.poll()["state"], "READY")
        self.assertEqual(service._task_reconciliation_history[0][:2],
            (request.original_message, current.original_response))
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 2)

    def test_controlled_history_capacity_retains_receipts_and_blocks_new_native_dispatch(self):
        """One genuine native receipt; repeated controlled fillers test only the cap."""
        service, root = self.empty_service()
        _, request = self.missing_pipe_task_attempt(service, "create", task_id="task:capacity",
            instruction="Original uncertain request")
        _, absence = self.task_call(service, "load", task_id="task:capacity")
        # A separate disclosed capacity fixture exercises the acknowledgment
        # boundary without manufacturing 256 successful reconciliations.
        capacity_marker = (request.original_message, absence.original_response,
            "CONTROLLED_CAPACITY_MARKER_NOT_A_RECONCILIATION")
        service._task_reconciliation_history = [capacity_marker] * 256
        full_unresolved = tuple(service._task_reconciliation_history)
        with self.assertRaises(ContractError) as caught:
            service.acknowledge_task_reconciliation("task:capacity", None)
        self.assertEqual(caught.exception.code, "SERVICE_TASK_RECONCILIATION_CAPACITY")
        self.assertEqual(service.poll()["state"], "RECOVERING")
        self.assertEqual(service._uncertain_task_request, request)
        self.assertEqual(tuple(service._task_reconciliation_history), full_unresolved)
        # Remove only these controlled local markers; no genuine receipt has
        # been appended at this point. The real acknowledgment is retained below.
        service._task_reconciliation_history = []
        service.acknowledge_task_reconciliation("task:capacity", None)
        receipt = service._task_reconciliation_history[0]
        self.assertEqual(receipt[:2], (request.original_message, absence.original_response))
        # Deliberate local controller-state fixture, not 256 natural cycles,
        # native security proof or independently generated reconciliation evidence.
        service._task_reconciliation_history.extend([receipt] * 255)
        before = tuple(service._task_reconciliation_history)
        request_paths = tuple(sorted(path.name for path in service._spool.glob("*.request.json")))
        from ceta.contracts.task_drafts import command_wire
        for kind in ("create", "save"):
            with self.subTest(kind=kind):
                wire = command_wire(kind, PROJECT, "command:capacity-" + kind, task_id="task:capacity",
                    title="Blocked", instruction="Instruction" if kind == "create" else None, draft="",
                    expected_revision="sha256:" + "a" * 64 if kind == "save" else None)
                with self.assertRaises(ContractError) as caught:
                    service.begin_call(wire, "task." + kind)
                self.assertEqual(caught.exception.code, "SERVICE_TASK_RECONCILIATION_CAPACITY")
                self.assertIsNone(service._pending)
                self.assertIsNone(service._send_task)
                self.assertEqual(tuple(service._task_reconciliation_history), before)
                self.assertEqual(tuple(sorted(path.name for path in service._spool.glob("*.request.json"))), request_paths)
        _, still_absent = self.task_call(service, "load", task_id="task:capacity")
        self.assertEqual(still_absent.kind, "TASK_ABSENT")
        self.assertEqual(tuple(service._task_reconciliation_history), before)
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 0)


if __name__ == "__main__":
    unittest.main()

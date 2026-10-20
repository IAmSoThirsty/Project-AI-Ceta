"""Revision-bound unaccepted meaning: real journals and native Windows fixtures.

Kernel identity/invalidation and replay substitution are explicitly controlled
stimuli over the real atomic SQLite implementation. Native cases start the
actual owned service, client and authenticated pipe with no positive owners
seeded. These are development regressions, not original B-case acceptance,
model/compiler qualification, consent, grants or finished-product evidence.
New APIs are imported inside helpers/methods to preserve old-source discovery.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.kernel_transactions import task_key
from ceta.contracts.store_transactions import STORE_PROFILE, StoreCell
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
import test_task_drafts as infrastructure
from test_kernel_transactions import CommitBarrierJournal, INSTALLATION, PROJECT, SCOPES


def _text(marker="first"):
    from ceta.contracts.task_meaning import MEANING_FIELDS
    return {name: marker + ":" + name + ': NO. Do not remove "excluded".\r\nCafe\u0301\x00\t'
            for name in MEANING_FIELDS}


class TaskMeaningTests(unittest.TestCase):
    # Reuse fixture lifecycle/helpers only. Inheriting TaskDraftTests, or binding
    # that TestCase into this module, would rediscover its existing test methods.
    setUpClass = classmethod(infrastructure.TaskDraftTests.setUpClass.__func__)
    setUp = infrastructure.TaskDraftTests.setUp
    tearDown = infrastructure.TaskDraftTests.tearDown
    fixture = infrastructure.TaskDraftTests.fixture
    denied = infrastructure.TaskDraftTests.denied

    def start_task(self, *, task_id="task:meaning", **kwargs):
        from ceta.contracts.task_drafts import draft_key
        f = self.fixture()
        result = f.create(task_id, instruction="NO. Do not change original.\r\nCafe\u0301\x00",
                          title="Exact title", draft="Unedited draft\r\n", **kwargs)
        return f, result, f.cell(draft_key(PROJECT, task_id)).revision

    def meaning_wire(self, kind="meaning_propose", *, task_id="task:meaning", task_revision=None,
                     meaning_revision=None, text=None, scope=PROJECT, command_id=None):
        from ceta.contracts.task_drafts import command_wire
        from ceta.contracts.task_meaning import meaning_from_text
        return command_wire(kind, scope, command_id or "command:" + uuid.uuid4().hex,
            task_id=task_id, expected_revision=task_revision,
            meaning=None if kind == "meaning_load" else meaning_from_text(_text() if text is None else text),
            meaning_expected_revision=meaning_revision)

    def meaning_call(self, f, kind="meaning_propose", *, context=None, wire=None, **kwargs):
        wire = self.meaning_wire(kind, **kwargs) if wire is None else wire
        message, actual_context = f.message(wire, context=context)
        return f.tasks(message, actual_context)

    def meaning_revision(self, f, result):
        from ceta.contracts.task_drafts import validate_result
        return validate_result(result, f.last_message.record, f.last_message.operation)

    def test_all_ten_fields_preserve_quotes_negation_crlf_nfd_nul_and_original_bytes(self):
        from ceta.contracts.task_meaning import decode_proposal, meaning_as_text, meaning_from_text
        from ceta.contracts.task_drafts import decode_snapshot
        text = _text()
        self.assertEqual(meaning_as_text(meaning_from_text(text)), text)
        f, created, revision = self.start_task()
        before = decode_snapshot(created.snapshot_wire)
        proposed = self.meaning_call(f, task_revision=revision, text=text)
        value = decode_proposal(proposed.snapshot_wire)
        self.assertEqual(meaning_as_text(value["meaning"]), text)
        for field in text:
            self.assertEqual(bytes.fromhex(value["meaning"][field]), text[field].encode("utf8"))
        for name in ("title_hex", "instruction_hex", "draft_hex"):
            self.assertEqual(value[name], before[name])
        self.assertEqual((value["state"], value["basis_revision"], value["task_objective_revision"]),
                         ("UNACCEPTED", revision, before["objective_revision"]))
        self.assertEqual(f.call("load", task_id="task:meaning").snapshot_wire, created.snapshot_wire)

    def test_meaning_utf8_field_and_total_bounds_are_bytes_and_required_fields_are_nonblank(self):
        from ceta.contracts.task_meaning import MEANING_FIELDS, meaning_as_text, meaning_from_text
        values = {name: "" for name in MEANING_FIELDS}
        values.update(clarified_meaning="\u00e9" * 8192, scope="s" * 16384,
                      exclusions="e" * 16384, completion_predicates="c" * 16384)
        self.assertEqual(sum(len(v.encode("utf8")) for v in values.values()), 65536)
        self.assertEqual(meaning_as_text(meaning_from_text(values)), values)
        variants = (dict(values, evidence="x"), dict(values, scope="\u00e9" * 8193),
                    dict(values, clarified_meaning=" \r\n"), dict(values, scope="\t"),
                    dict(values, authority="\ud800"), dict(values, budgets=True),
                    {name: value for name, value in values.items() if name != "exclusions"},
                    dict(values, authority_granted="true"))
        for candidate in variants:
            with self.subTest(fields=list(candidate)):
                with self.assertRaises(ContractError):
                    meaning_from_text(candidate)

    def test_meaning_hex_rejects_wrong_types_invalid_utf8_and_nonlowercase_encodings(self):
        from ceta.contracts.task_meaning import decode_meaning, meaning_from_text
        base = meaning_from_text(_text())
        for invalid in (None, True, 1, [], {}, "f", "FF", "zz", "ff", "eda080", "61 62"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ContractError):
                    decode_meaning(dict(base, exclusions=invalid))
        for wrong in (None, [], "text", True):
            with self.assertRaises(ContractError):
                decode_meaning(wrong)

    def test_meaning_commands_require_v2_and_do_not_change_raw_v1_command_shapes(self):
        from ceta.contracts.task_drafts import command_wire, decode_command
        f, _, revision = self.start_task()
        wire = self.meaning_wire(task_revision=revision)
        parsed = decode_command(wire)
        self.assertEqual(parsed.as_dict()["profile"], "ceta-task-command-v2")
        raw = command_wire("load", PROJECT, "command:raw-v1", task_id="task:meaning")
        self.assertEqual(decode_command(raw).as_dict()["profile"], "ceta-task-command-v1")
        changes = ({"profile": "ceta-task-command-v1"}, {"record_type": "TaskMeaning"},
                   {"expected_revision": True}, {"meaning_expected_revision": False},
                   {"title_hex": "61"}, {"instruction_hex": "61"}, {"draft_hex": "61"},
                   {"allow": True}, {"kind": "meaning_accept"}, {"meaning_hex": None})
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    decode_command(canonical_bytes(dict(strict_loads(wire), **change)))
        load = strict_loads(self.meaning_wire("meaning_load"))
        for field in ("meaning_hex", "meaning_expected_revision", "expected_revision"):
            changed = dict(load, **{field: strict_loads(wire)[field] or revision})
            with self.assertRaises(ContractError):
                decode_command(canonical_bytes(changed))
        with self.assertRaises(ContractError):
            command_wire("load", PROJECT, "command:raw-with-meaning", task_id="task:meaning",
                         meaning={})
        self.assertEqual(f.store.store_position().next_commit, 1)

    def test_duplicate_keys_and_noncanonical_inner_meaning_deny_before_any_write(self):
        from ceta.contracts.task_drafts import decode_command
        f, _, revision = self.start_task()
        wire = self.meaning_wire(task_revision=revision)
        outer = strict_loads(wire)
        meaning = strict_loads(bytes.fromhex(outer["meaning_hex"]))
        noncanonical = json.dumps(meaning, indent=2).encode("utf8")
        self.denied(f, lambda: self.meaning_call(f, wire=canonical_bytes(
            dict(outer, meaning_hex=noncanonical.hex()))), code="MEANING_CANONICAL")
        duplicate = b'{"clarified_meaning":"61",' + canonical_bytes(meaning)[1:]
        self.denied(f, lambda: self.meaning_call(f, wire=canonical_bytes(
            dict(outer, meaning_hex=duplicate.hex()))))
        with self.assertRaises(ContractError):
            decode_command(b'{"kind":"meaning_propose",' + wire[1:])
        # Noncanonical outer command bytes remain authenticated original input;
        # only the enclosed typed meaning representation must be canonical.
        original = json.dumps(outer, indent=3).encode("utf8")
        result = self.meaning_call(f, wire=original)
        self.assertEqual(result.kind, "TASK_MEANING_PROPOSAL")
        self.assertEqual(f.last_message.record.original_wire, original)
        self.assertEqual(f.last_message.record.commitment, decode_command(wire).commitment)

    def test_projection_decoder_rejects_accepted_state_wrong_generations_extra_and_noncanonical_bytes(self):
        from ceta.contracts.task_meaning import decode_proposal
        f, _, revision = self.start_task()
        value = decode_proposal(self.meaning_call(f, task_revision=revision).snapshot_wire)
        for change in ({"state": "ACCEPTED"}, {"profile": "ceta-task-meaning-v2"},
                       {"generation": True}, {"generation": 0}, {"event_sequence": False},
                       {"basis_revision": True}, {"task_objective_revision": None},
                       {"permission": "ALLOW"}, {"instruction_hex": "ff"}, {"meaning": None}):
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    decode_proposal(canonical_bytes(dict(value, **change)))
        with self.assertRaises(ContractError):
            decode_proposal(json.dumps(value, indent=2).encode("utf8"))

    def test_initial_proposal_atomically_adds_one_attributed_event_without_changing_raw_task_or_catalog(self):
        from ceta.contracts.task_drafts import catalog_key, draft_key
        from ceta.contracts.task_meaning import decode_proposal, meaning_commitment, meaning_key
        f, created, revision = self.start_task()
        owner = f.identity.task_owner_binding(f.identity.context)
        keys = (draft_key(PROJECT, "task:meaning"), task_key(PROJECT, "task:meaning"), catalog_key(PROJECT, owner))
        raw_cells = tuple(f.cell(key) for key in keys)
        before = f.store.store_position()
        result = self.meaning_call(f, task_revision=revision, command_id="command:meaning-atomic")
        value = decode_proposal(result.snapshot_wire)
        self.assertEqual(tuple(f.cell(key) for key in keys), raw_cells)
        self.assertEqual((result.kind, result.generation, result.current_task_revision),
                         ("TASK_MEANING_PROPOSAL", 1, revision))
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        cell = f.cell(meaning_key(PROJECT, "task:meaning"))
        self.assertEqual((cell.value_wire, cell.generation), (result.snapshot_wire, 1))
        self.assertEqual(self.meaning_revision(f, result), cell.revision)
        row = f.store.replay(PROJECT)[-1]
        event, payload = self.codec.decode(row.event_wire).as_dict(), self.codec.decode(row.payload_wire).as_dict()
        self.assertEqual((event["event_type"], event["actor_id"], event["actor_session"], event["causation_ref"]),
                         ("task.meaning.proposed", "operator:fixture", "session:fixture", "command:meaning-atomic"))
        self.assertEqual((payload["epistemic_status"], payload["payload_commitment"]),
                         ("ATTRIBUTED", meaning_commitment(result.snapshot_wire)))
        self.assertEqual(payload["resource"]["revision"], meaning_commitment(result.snapshot_wire))
        self.assertIsNone(payload["observed_at"])
        self.assertIn("unaccepted", " ".join(payload["uncertainty"]))
        self.assertEqual(value["request_commitment"], f.last_message.record.commitment)
        self.assertEqual(f.store._connection.execute(
            "SELECT COUNT(*) FROM store_cells WHERE collection!='projection'").fetchone()[0], 0)
        self.assertEqual(f.call("load", task_id="task:meaning").snapshot_wire, created.snapshot_wire)

    def test_proposal_revisions_have_exact_meaning_cas_and_leave_task_objective_revision_unchanged(self):
        from ceta.contracts.task_meaning import decode_proposal
        f, original, task_revision = self.start_task()
        first = self.meaning_call(f, task_revision=task_revision)
        first_revision = self.meaning_revision(f, first)
        self.denied(f, lambda: self.meaning_call(f, task_revision=task_revision, text=_text("overwrite")),
                    code="MEANING_REVISION_CONFLICT")
        second = self.meaning_call(f, task_revision=task_revision, meaning_revision=first_revision, text=_text("second"))
        second_revision = self.meaning_revision(f, second)
        self.assertNotEqual(first_revision, second_revision)
        self.assertEqual((first.generation, second.generation), (1, 2))
        self.assertEqual(decode_proposal(second.snapshot_wire)["basis_revision"], task_revision)
        self.denied(f, lambda: self.meaning_call(f, task_revision=task_revision,
            meaning_revision=first_revision, text=_text("stale update")), code="MEANING_REVISION_CONFLICT")
        before = f.cut()
        loaded = self.meaning_call(f, "meaning_load")
        self.assertEqual(loaded, second)
        self.assertEqual(f.cut(), before)
        self.assertEqual(f.call("load", task_id="task:meaning").snapshot_wire, original.snapshot_wire)

    def test_changed_task_revision_rejects_old_basis_without_an_event_or_semantic_overwrite(self):
        f, _, revision = self.start_task()
        first = self.meaning_call(f, task_revision=revision)
        meaning_revision = self.meaning_revision(f, first)
        f.call("save", task_id="task:meaning", title="Revised title", draft="Revised draft", expected_revision=revision)
        self.denied(f, lambda: self.meaning_call(f, task_revision=revision, meaning_revision=meaning_revision),
                    code="MEANING_TASK_REVISION_CONFLICT")

    def test_stale_disclosure_keeps_proposal_original_and_basis_draft_and_names_actual_current_revision(self):
        from ceta.contracts.task_drafts import draft_key, text_value
        from ceta.contracts.task_meaning import decode_proposal
        f, original, revision = self.start_task()
        proposed = self.meaning_call(f, task_revision=revision)
        f.call("save", task_id="task:meaning", title="Current title", draft="New draft\r\n", expected_revision=revision)
        current = f.cell(draft_key(PROJECT, "task:meaning"))
        before = f.cut()
        loaded = self.meaning_call(f, "meaning_load")
        value = decode_proposal(loaded.snapshot_wire)
        self.assertEqual((loaded.kind, loaded.snapshot_wire, loaded.generation),
                         ("TASK_MEANING_STALE", proposed.snapshot_wire, 1))
        self.assertEqual(loaded.current_task_revision, current.revision)
        self.assertNotEqual(value["basis_revision"], loaded.current_task_revision)
        self.assertEqual(value["instruction_hex"], strict_loads(original.snapshot_wire)["instruction_hex"])
        self.assertEqual(text_value(value["draft_hex"]), "Unedited draft\r\n")
        self.assertEqual(f.cut(), before)

    def test_task_content_a_b_a_keeps_old_meaning_stale_and_cannot_reuse_old_basis(self):
        from ceta.contracts.task_drafts import draft_key
        f, original, initial = self.start_task()
        meaning = self.meaning_call(f, task_revision=initial)
        meaning_revision = self.meaning_revision(f, meaning)
        changed = f.call("save", task_id="task:meaning", title="B", draft="B", expected_revision=initial)
        f.call("save", task_id="task:meaning", title="Exact title", draft="Unedited draft\r\n",
               expected_revision=f.revision(changed))
        current = f.cell(draft_key(PROJECT, "task:meaning"))
        raw = strict_loads(current.value_wire)
        original_value = strict_loads(original.snapshot_wire)
        self.assertEqual(tuple(raw[n] for n in ("title_hex", "instruction_hex", "draft_hex")),
                         tuple(original_value[n] for n in ("title_hex", "instruction_hex", "draft_hex")))
        self.assertNotEqual(current.revision, initial)
        self.assertEqual(self.meaning_call(f, "meaning_load").kind, "TASK_MEANING_STALE")
        self.denied(f, lambda: self.meaning_call(f, task_revision=initial, meaning_revision=meaning_revision),
                    code="MEANING_TASK_REVISION_CONFLICT")

    def test_rebased_proposal_requires_current_task_and_latest_meaning_revisions_and_keeps_original(self):
        from ceta.contracts.task_meaning import decode_proposal
        f, created, task_revision = self.start_task()
        old = self.meaning_call(f, task_revision=task_revision)
        meaning_revision = self.meaning_revision(f, old)
        saved = f.call("save", task_id="task:meaning", title="Current", draft="Changed\r\n", expected_revision=task_revision)
        current_revision = f.revision(saved)
        rebased = self.meaning_call(f, task_revision=current_revision, meaning_revision=meaning_revision, text=_text("rebased"))
        value = decode_proposal(rebased.snapshot_wire)
        self.assertEqual((rebased.generation, value["basis_revision"], rebased.current_task_revision),
                         (2, current_revision, current_revision))
        self.assertEqual(value["draft_hex"], strict_loads(saved.snapshot_wire)["draft_hex"])
        self.assertEqual(value["instruction_hex"], strict_loads(created.snapshot_wire)["instruction_hex"])
        self.assertEqual(f.call("load", task_id="task:meaning").snapshot_wire, saved.snapshot_wire)

    def test_other_principal_or_sid_cannot_load_or_overwrite_meaning(self):
        f, _, revision = self.start_task()
        first = self.meaning_call(f, task_revision=revision)
        meaning_revision = self.meaning_revision(f, first)
        for principal, sid in (("operator:foreign", "SID:fixture"), ("operator:fixture", "SID:foreign")):
            with self.subTest(principal=principal, sid=sid):
                context = f.identity.add(principal, "session:foreign", sid)
                self.denied(f, lambda: self.meaning_call(f, "meaning_load", context=context), code="TASK_OWNER_DENIED")
                self.denied(f, lambda: self.meaning_call(f, task_revision=revision,
                    meaning_revision=meaning_revision, context=context), code="TASK_OWNER_DENIED")

    def test_reopen_same_principal_sid_fresh_session_recovers_read_only_and_records_new_update_session(self):
        from ceta.contracts.task_meaning import decode_proposal
        f, _, revision = self.start_task()
        first = self.meaning_call(f, task_revision=revision)
        meaning_revision = self.meaning_revision(f, first)
        before = f.cut()
        f.reopen()
        fresh = f.identity.add("operator:fixture", "session:meaning-after-restart")
        self.assertEqual(self.meaning_call(f, "meaning_load", context=fresh), first)
        self.assertEqual(f.cut(), before)
        updated = self.meaning_call(f, task_revision=revision, meaning_revision=meaning_revision,
                                    context=fresh, text=_text("fresh"))
        self.assertEqual(decode_proposal(updated.snapshot_wire)["updated_session"], "session:meaning-after-restart")
        self.assertEqual(decode_proposal(first.snapshot_wire)["updated_session"], "session:fixture")

    def test_same_task_identifier_in_two_scopes_has_distinct_meaning_and_task_basis(self):
        from ceta.contracts.task_drafts import draft_key
        f, _, project_revision = self.start_task()
        install = f.create("task:meaning", title="Installation task", scope=INSTALLATION)
        install_revision = f.cell(draft_key(INSTALLATION, "task:meaning")).revision
        first = self.meaning_call(f, task_revision=project_revision, text=_text("project"))
        second = self.meaning_call(f, scope=INSTALLATION, task_revision=install_revision, text=_text("installation"))
        self.assertNotEqual(first.snapshot_wire, second.snapshot_wire)
        self.assertEqual(self.meaning_call(f, "meaning_load"), first)
        self.assertEqual(self.meaning_call(f, "meaning_load", scope=INSTALLATION), second)
        self.assertEqual(f.call("load", task_id="task:meaning", scope=INSTALLATION).snapshot_wire, install.snapshot_wire)

    def test_forged_context_message_route_scope_and_command_attributes_cannot_propose(self):
        f, _, revision = self.start_task()
        message, context = f.message(self.meaning_wire(task_revision=revision))
        self.denied(f, lambda: f.tasks(message, object()), code="FIXTURE_AUTHENTICATION_DENIED")
        f.identity.messages[context] = b"foreign original message"
        self.denied(f, lambda: f.tasks(message, context), code="FIXTURE_MESSAGE_BINDING_DENIED")
        f.identity.messages[context] = message.original_message
        forged = replace(message.record, commitment="sha256:" + "f" * 64)
        for changed in (replace(message, record=forged), replace(message, operation="task.load"),
                        replace(message, scope_id=INSTALLATION), replace(message, sender_session="session:foreign")):
            self.denied(f, lambda: f.tasks(changed, context), code="TASK_MESSAGE_REQUIRED")

    def test_tombstoned_or_malformed_meaning_cell_is_denied_without_repair_or_overwrite(self):
        from ceta.contracts.task_meaning import meaning_key
        for variant in ("tombstone", "bad-profile", "generation-mismatch"):
            with self.subTest(variant=variant):
                f, _, revision = self.start_task()
                first = self.meaning_call(f, task_revision=revision)
                key = meaning_key(PROJECT, "task:meaning")
                value = None if variant == "tombstone" else (canonical_bytes({"profile": "foreign"})
                    if variant == "bad-profile" else first.snapshot_wire)
                f.put(key, value)
                self.denied(f, lambda: self.meaning_call(f, "meaning_load"))
                self.denied(f, lambda: self.meaning_call(f, task_revision=revision,
                    meaning_revision=f.cell(key).revision))

    def test_meaning_event_actor_session_causation_and_attributed_payload_binding_reject_substitutions(self):
        from ceta.contracts.task_meaning import decode_proposal
        variants = (({"actor_id": "operator:foreign"}, {}), ({"actor_session": "session:foreign"}, {}),
            ({"causation_ref": "command:foreign"}, {}), ({"event_type": "task.meaning.accepted"}, {}),
            ({"record_id": "event:foreign"}, {}), ({}, {"method": "authenticated.local.foreign"}),
            ({}, {"payload_commitment": "sha256:" + "a" * 64}), ({}, {"observer_session": "session:foreign"}),
            ({}, {"causation_ref": "command:foreign"}), ({}, {"payload_ref": "task:foreign"}),
            ({}, {"observed_at": "2026-10-08T12:00:00Z"}), ({}, {"valid_until": "2026-10-09T12:00:00Z"}),
            ({}, {"supersedes": "observation:foreign"}), ({}, {"completeness": "UNAVAILABLE"}),
            ({}, {"epistemic_status": "OBSERVED"}), ({}, {"sensitivity": "PUBLIC"}),
            ({}, {"recorded_at": "2026-10-08T10:00:00Z"}))
        for event_change, payload_change in variants:
            with self.subTest(event_change=event_change, payload_change=payload_change):
                f, _, revision = self.start_task()
                value = decode_proposal(self.meaning_call(f, task_revision=revision).snapshot_wire)
                original_replay, reached = f.store.replay, []

                def substitute(scope, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope, start, limit, checkpoints=checkpoints)
                    if scope == PROJECT and start == value["event_sequence"] and limit == 1:
                        event = dict(strict_loads(rows[0].event_wire), **event_change)
                        payload = dict(strict_loads(rows[0].payload_wire), **payload_change)
                        payload_wire = canonical_bytes(payload)
                        if payload_change:
                            event["payload_commitment"] = self.codec.decode(payload_wire).commitment
                        event_wire = canonical_bytes(event)
                        events = EventContract(self.codec)
                        events.require_successor(event_wire, StreamPosition(PROJECT, value["event_sequence"], value["previous_head"]))
                        events.require_payload(event_wire, payload_wire)
                        reached.append(True)
                        return (JournalEntry(event_wire, payload_wire),)
                    return rows

                with patch.object(f.store, "replay", substitute):
                    self.denied(f, lambda: self.meaning_call(f, "meaning_load"), code="MEANING_EVENT_BINDING")
                self.assertTrue(reached, "actual selected meaning-event read was not reached")

    def test_snapshot_substitution_cannot_change_meaning_instruction_owner_task_or_basis(self):
        from ceta.contracts.task_meaning import meaning_key, decode_proposal
        changes = ({"owner_binding": "sha256:" + "a" * 64}, {"principal_id": "operator:foreign"},
            {"task_id": "task:foreign"}, {"scope_id": INSTALLATION}, {"generation": 99},
            {"instruction_hex": "Foreign original".encode("utf8").hex()},
            {"title_hex": "Foreign title".encode("utf8").hex()}, {"basis_revision": "sha256:" + "b" * 64},
            {"request_id": "command:foreign"}, {"request_commitment": "sha256:" + "c" * 64})
        for change in changes:
            with self.subTest(change=change):
                f, _, revision = self.start_task()
                value = decode_proposal(self.meaning_call(f, task_revision=revision).snapshot_wire)
                target, original_snapshot = meaning_key(PROJECT, "task:meaning"), f.store.snapshot
                forged = canonical_bytes(dict(value, **change))

                def substitute(keys, *, state_checkpoint=None):
                    return tuple(StoreCell(cell.key, cell.generation, forged) if cell.key == target else cell
                        for cell in original_snapshot(keys, state_checkpoint=state_checkpoint))

                with patch.object(f.store, "snapshot", substitute):
                    self.denied(f, lambda: self.meaning_call(f, "meaning_load"))

    def test_corrupt_actual_meaning_history_is_denied_and_preserved_without_automatic_write(self):
        from ceta.contracts.task_meaning import decode_proposal
        f, _, revision = self.start_task()
        value = decode_proposal(self.meaning_call(f, task_revision=revision).snapshot_wire)
        f.store._connection.execute("UPDATE history_events SET payload_wire=? WHERE scope_id=? AND sequence=?",
            (b'{"corrupt":"meaning-history"}', PROJECT, value["event_sequence"]))
        before = f.raw_rows()
        with patch.object(f.store, "commit", side_effect=AssertionError("corrupt read attempted repair")):
            with self.assertRaises(ContractError):
                self.meaning_call(f, "meaning_load")
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(f.raw_rows(), before)

    def test_failure_after_all_real_inserts_rolls_back_initial_and_updated_proposal_then_exact_retry(self):
        for updating in (False, True):
            with self.subTest(updating=updating):
                f, _, revision = self.start_task()
                meaning_revision = None
                if updating:
                    meaning_revision = self.meaning_revision(f, self.meaning_call(f, task_revision=revision))
                wire = self.meaning_wire(task_revision=revision, meaning_revision=meaning_revision,
                                         text=_text("atomic"), command_id="command:atomic-meaning")
                before = f.cut()
                f.fail_commit = True
                with self.assertRaisesRegex(RuntimeError, "after all writer inserts"):
                    self.meaning_call(f, wire=wire)
                self.assertFalse(f.store._connection.in_transaction)
                self.assertEqual(f.cut(), before)
                f.fail_commit = False
                committed = self.meaning_call(f, wire=wire)
                self.assertEqual(committed.kind, "TASK_MEANING_PROPOSAL")
                self.assertEqual(f.store.store_position().next_commit, before[0].next_commit + 1)

    def test_original_context_invalidated_inside_real_writer_guard_rolls_back_meaning(self):
        f, _, revision = self.start_task()
        original = f.identity.context
        f.before_commit_action = lambda: f.identity.contexts.pop(original)
        self.denied(f, lambda: self.meaning_call(f, task_revision=revision), code="FIXTURE_AUTHENTICATION_DENIED")
        self.assertEqual(f.store.store_position().next_commit, 1)

    def test_original_context_denial_after_real_commit_keeps_proposal_and_fresh_load_does_not_repeat_write(self):
        from ceta.contracts.task_meaning import decode_proposal, meaning_key, meaning_as_text
        f, original_task, revision = self.start_task()
        original = f.identity.context
        f.store.after_commit = lambda: f.identity.contexts.pop(original)
        with self.assertRaises(ContractError) as caught:
            self.meaning_call(f, task_revision=revision, text=_text("committed despite denial"))
        self.assertEqual(caught.exception.code, "FIXTURE_AUTHENTICATION_DENIED")
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(f.store.store_position().next_commit, 2)
        durable = f.cell(meaning_key(PROJECT, "task:meaning"))
        self.assertEqual(meaning_as_text(decode_proposal(durable.value_wire)["meaning"]), _text("committed despite denial"))
        f.store.after_commit = None
        f.reopen()
        fresh = f.identity.add("operator:fixture", "session:post-denial")
        before = f.cut()
        loaded = self.meaning_call(f, "meaning_load", context=fresh)
        self.assertEqual((loaded.snapshot_wire, loaded.generation), (durable.value_wire, durable.generation))
        self.assertEqual(f.call("load", task_id="task:meaning", context=fresh).snapshot_wire, original_task.snapshot_wire)
        self.assertEqual(f.cut(), before)

    def test_meaning_load_rechecks_original_context_and_owner_after_event_and_after_final_union_read(self):
        from ceta.contracts.task_meaning import decode_proposal, meaning_key
        for variant in ("after_event_invalidated", "after_event_owner_changed", "final_read_invalidated"):
            with self.subTest(variant=variant):
                f, _, revision = self.start_task()
                value = decode_proposal(self.meaning_call(f, task_revision=revision).snapshot_wire)
                message, context = f.message(self.meaning_wire("meaning_load"))
                original_authenticate, original_replay, original_snapshot = f.identity.authenticate, f.store.replay, f.store.snapshot
                reached, auth_after_event, last_read, contexts = [], [], [], []

                def authenticate(actual):
                    contexts.append(actual)
                    self.assertIs(actual, context)
                    peer = original_authenticate(actual)
                    if reached:
                        auth_after_event.append(True)
                    return peer

                def replay(scope, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope, start, limit, checkpoints=checkpoints)
                    if scope == PROJECT and start == value["event_sequence"] and limit == 1 and not reached:
                        reached.append(True)
                        if variant == "after_event_invalidated":
                            f.identity.contexts.pop(context)
                        elif variant == "after_event_owner_changed":
                            peer, _ = f.identity.contexts[context]
                            f.identity.contexts[context] = (peer, infrastructure._owner(peer.principal_id, "SID:changed"))
                    return rows

                def snapshot(keys, *, state_checkpoint=None):
                    cells = original_snapshot(keys, state_checkpoint=state_checkpoint)
                    if (variant == "final_read_invalidated" and reached and auth_after_event and not last_read
                            and meaning_key(PROJECT, "task:meaning") in keys):
                        last_read.append(True)
                        f.identity.contexts.pop(context)
                    return cells

                before = f.cut()
                with patch.object(f.identity, "authenticate", authenticate), patch.object(f.store, "replay", replay), \
                        patch.object(f.store, "snapshot", snapshot):
                    with self.assertRaises(ContractError) as caught:
                        f.tasks(message, context)
                self.assertEqual(caught.exception.code, "TASK_CONTEXT_CHANGED" if variant == "after_event_owner_changed"
                                 else "FIXTURE_AUTHENTICATION_DENIED")
                self.assertEqual(reached, [True])
                if variant == "final_read_invalidated":
                    self.assertEqual(last_read, [True])
                self.assertGreaterEqual(len(contexts), 2)
                self.assertEqual(f.cut(), before)

    def test_meaning_load_detects_aba_generations_in_all_four_selected_cells(self):
        from ceta.contracts.task_drafts import catalog_key, draft_key
        from ceta.contracts.task_meaning import decode_proposal, meaning_key
        for selected in ("meaning", "draft", "task", "catalog"):
            with self.subTest(selected=selected):
                f, _, revision = self.start_task()
                value = decode_proposal(self.meaning_call(f, task_revision=revision).snapshot_wire)
                target = {"meaning": meaning_key(PROJECT, "task:meaning"), "draft": draft_key(PROJECT, "task:meaning"),
                    "task": task_key(PROJECT, "task:meaning"),
                    "catalog": catalog_key(PROJECT, f.identity.task_owner_binding(f.identity.context))}[selected]
                prior, original_replay, reached, injected = f.cell(target), f.store.replay, [], []

                def replay(scope, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope, start, limit, checkpoints=checkpoints)
                    if scope == PROJECT and start == value["event_sequence"] and limit == 1 and not reached:
                        reached.append(True)
                        f.put(target, canonical_bytes({"fixture": "ABA intermediary"}))
                        f.put(target, prior.value_wire)
                        injected.append(f.cut())
                    return rows

                with patch.object(f.store, "replay", replay):
                    with self.assertRaises(ContractError) as caught:
                        self.meaning_call(f, "meaning_load")
                self.assertEqual(caught.exception.code, "TASK_READ_CHANGED")
                self.assertEqual(reached, [True])
                self.assertEqual(f.cut(), injected[0])
                current = f.cell(target)
                self.assertEqual((current.value_wire, current.generation), (prior.value_wire, prior.generation + 2))
                self.assertNotEqual(current.revision, prior.revision)

    def test_two_real_connections_proposing_same_revision_have_one_winner_without_lost_update(self):
        from ceta.contracts.task_drafts import draft_key
        f, _, revision = self.start_task()
        raw = f.cell(draft_key(PROJECT, "task:meaning"))
        second_store = CommitBarrierJournal(f.root, f.codec, SCOPES, profile=STORE_PROFILE)
        g = self.fixture(store=second_store, root=f.root, identity=infrastructure._Identity(session="session:second-meaning"))
        barrier = threading.Barrier(2)
        f.store.commit_barrier = g.store.commit_barrier = barrier

        def proposing(target, marker):
            try:
                return self.meaning_call(target, task_revision=revision, text=_text(marker))
            except ContractError as error:
                return error

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a, b = pool.submit(proposing, f, "writer-a"), pool.submit(proposing, g, "writer-b")
                results = a.result(timeout=30), b.result(timeout=30)
        finally:
            f.store.commit_barrier = g.store.commit_barrier = None
        winners = [result for result in results if not isinstance(result, ContractError)]
        denials = [result for result in results if isinstance(result, ContractError)]
        self.assertEqual((len(winners), len(denials)), (1, 1))
        self.assertIn(denials[0].code, {"JOURNAL_REVISION_CONFLICT", "STORE_REVISION_CONFLICT", "MEANING_REVISION_CONFLICT"})
        self.assertEqual(self.meaning_call(f, "meaning_load"), winners[0])
        self.assertEqual(f.cell(raw.key), raw)
        self.assertEqual(f.store.store_position().next_commit, 2)

    def test_proposal_and_raw_save_real_connection_race_never_returns_current_meaning_for_wrong_basis(self):
        f, _, revision = self.start_task()
        second_store = CommitBarrierJournal(f.root, f.codec, SCOPES, profile=STORE_PROFILE)
        g = self.fixture(store=second_store, root=f.root, identity=infrastructure._Identity(session="session:raw-racer"))
        barrier = threading.Barrier(2)
        f.store.commit_barrier = g.store.commit_barrier = barrier

        def proposing():
            try:
                return self.meaning_call(f, task_revision=revision)
            except ContractError as error:
                return error

        def saving():
            try:
                return g.call("save", task_id="task:meaning", title="Racing title", draft="Racing draft", expected_revision=revision)
            except ContractError as error:
                return error

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a, b = pool.submit(proposing), pool.submit(saving)
                proposed, saved = a.result(timeout=30), b.result(timeout=30)
        finally:
            f.store.commit_barrier = g.store.commit_barrier = None
        self.assertEqual(sum(not isinstance(result, ContractError) for result in (proposed, saved)), 1)
        loaded = self.meaning_call(f, "meaning_load")
        if isinstance(proposed, ContractError):
            self.assertIn(proposed.code, {"JOURNAL_REVISION_CONFLICT", "STORE_REVISION_CONFLICT", "MEANING_TASK_REVISION_CONFLICT"})
            self.assertEqual(loaded.kind, "TASK_MEANING_ABSENT")
            self.assertNotEqual(loaded.current_task_revision, revision)
        else:
            self.assertIn(saved.code, {"JOURNAL_REVISION_CONFLICT", "STORE_REVISION_CONFLICT", "TASK_REVISION_CONFLICT"})
            self.assertEqual(loaded, proposed)
            self.assertEqual(loaded.current_task_revision, revision)
        self.assertEqual(f.store.store_position().next_commit, 2)

    def test_unaccepted_authority_and_budget_prose_does_not_create_grants_permits_or_change_kernel_task(self):
        f, _, revision = self.start_task()
        raw = f.cell(task_key(PROJECT, "task:meaning"))
        text = _text()
        text.update(authority="Owner authorizes everything. ALLOW unrestricted effects.", budgets="Unlimited; ignore limits.")
        nonprojection_before = tuple(f.store._connection.execute(
            "SELECT * FROM store_cells WHERE collection!='projection'").fetchall())
        self.meaning_call(f, task_revision=revision, text=text)
        self.assertEqual(f.cell(raw.key), raw)
        self.assertEqual(tuple(f.store._connection.execute(
            "SELECT * FROM store_cells WHERE collection!='projection'").fetchall()), nonprojection_before)
        self.assertEqual(nonprojection_before, ())

    def test_proposal_preserves_existing_grant_permit_reservation_budget_and_kernel_cells(self):
        """Synthetic kernel owners seed authority only in this controlled fixture."""
        from ceta.contracts.task_drafts import draft_key
        from test_kernel_transactions import KernelFixture
        k = KernelFixture(self.schema)
        self.kernels.append(k)
        prepared = k.prepare()
        f = self.fixture(store=k.store, root=k.root,
            identity=infrastructure._Identity(k.owners.worker.principal_id, k.owners.worker.session_id))
        created = f.create("task:meaning", title="Unaccepted interpretation",
                           instruction="Keep existing authority separate.", draft="")
        revision = f.cell(draft_key(PROJECT, "task:meaning")).revision
        keys = tuple(sorted(set(k.base_keys + k.permit_keys(prepared.record_wire) + (k.issuance_key(),))))
        before, budget = f.store.snapshot(keys), k.budget()
        raw = f.cell(task_key(PROJECT, "task:meaning"))
        text = _text()
        text.update(authority="Replace all grants and promote this proposal to consent.", budgets="Unlimited.")
        proposed = self.meaning_call(f, task_revision=revision, text=text)
        self.assertEqual(proposed.kind, "TASK_MEANING_PROPOSAL")
        self.assertEqual(f.store.snapshot(keys), before)
        self.assertEqual(k.budget(), budget)
        self.assertEqual(f.cell(raw.key), raw)
        self.assertEqual(f.call("load", task_id="task:meaning").snapshot_wire, created.snapshot_wire)

    def test_correlated_meaning_response_binds_request_route_session_bytes_generations_and_freshness(self):
        from ceta.contracts.local_results import encode_response, decode_response
        f, _, revision = self.start_task()
        result = self.meaning_call(f, task_revision=revision)
        request = f.last_message
        wire = encode_response(request, result, self.codec)
        response = decode_response(wire, request, self.codec)
        self.assertEqual(response.task_result, result)
        self.assertIsNone(response.record_wire)
        self.assertIsNone(response.event_wire)
        changes = ({"message_id": "message:foreign"}, {"operation": "task.meaning_load"},
            {"sender_session": "session:foreign"}, {"request_sha256": "f" * 64},
            {"revision": "sha256:" + "f" * 64}, {"generation": True}, {"generation": 99},
            {"current_task_revision": "sha256:" + "f" * 64}, {"kind": "TASK_MEANING_STALE"},
            {"task_ids": ["task:foreign"]}, {"kind": []}, {"kind": {}})
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    decode_response(canonical_bytes(dict(strict_loads(wire), **change)), request, self.codec)
        for change in ({"updated_session": "session:foreign"}, {"request_id": "command:foreign"},
                       {"request_commitment": "sha256:" + "a" * 64},
                       {"meaning": {name: "61" for name in strict_loads(result.snapshot_wire)["meaning"]}}):
            with self.subTest(proposal_change=change):
                forged = replace(result, snapshot_wire=canonical_bytes(dict(strict_loads(result.snapshot_wire), **change)))
                with self.assertRaises(ContractError):
                    encode_response(request, forged, self.codec)

    def test_absent_meaning_is_read_only_requires_actual_task_and_rejects_embedded_content_or_wrong_routes(self):
        from ceta.contracts.local_results import encode_response, decode_response
        from ceta.contracts.task_drafts import validate_result
        f, _, revision = self.start_task()
        before = f.cut()
        result = self.meaning_call(f, "meaning_load")
        request = f.last_message
        self.assertEqual((result.kind, result.snapshot_wire, result.generation, result.current_task_revision),
                         ("TASK_MEANING_ABSENT", None, 0, revision))
        self.assertIsNone(validate_result(result, request.record, request.operation))
        wire = encode_response(request, result, self.codec)
        self.assertEqual(decode_response(wire, request, self.codec).task_result, result)
        self.assertEqual(f.cut(), before)
        for changed in (replace(result, generation=False), replace(result, generation=1),
                        replace(result, snapshot_wire=b"{}"), replace(result, task_ids=("task:meaning",)),
                        replace(result, current_task_revision=None), replace(result, kind="TASK_ABSENT")):
            with self.assertRaises(ContractError):
                encode_response(request, changed, self.codec)
        self.denied(f, lambda: self.meaning_call(f, "meaning_load", task_id="task:never-created"), code="TASK_NOT_FOUND")
        command, _ = f.message(self.meaning_wire(task_revision=revision))
        with self.assertRaises(ContractError):
            encode_response(command, result, self.codec)


class NativeTaskMeaningTests(infrastructure._ServiceTestCase):
    """Actual disposable service/client/pipe/SQLite; no positive-owner seeding."""
    empty_service = infrastructure.NativeTaskDraftTests.empty_service
    task_call = infrastructure.NativeTaskDraftTests.task_call
    response_revision = infrastructure.NativeTaskDraftTests.response_revision
    durable_cut = infrastructure.NativeTaskDraftTests.durable_cut

    def meaning_call(self, service, kind="meaning_propose", *, task_id="task:native-meaning",
                     task_revision=None, meaning_revision=None, text=None, command_id=None, scope=PROJECT):
        from ceta.contracts.task_drafts import command_wire
        from ceta.contracts.task_meaning import meaning_from_text
        self.until(lambda: service.poll()["state"] in {"READY", "RECOVERING"}
                   and service._send_task is None and service._pending is None,
                   explanation="prior owned call/send lifetime was not retired")
        wire = command_wire(kind, scope, command_id or "command:" + uuid.uuid4().hex,
            task_id=task_id, expected_revision=task_revision,
            meaning=None if kind == "meaning_load" else meaning_from_text(_text() if text is None else text),
            meaning_expected_revision=meaning_revision)
        attempt, response = self.call(service, wire, "task." + kind)
        self.assertEqual(service.poll()["authority"], "CLOSED")
        return attempt, response

    def meaning_revision(self, response):
        from ceta.contracts.task_meaning import decode_proposal, meaning_key
        value = decode_proposal(response.task_result.snapshot_wire)
        return StoreCell(meaning_key(value["scope_id"], value["task_id"]), response.task_result.generation,
                         response.task_result.snapshot_wire).revision

    def create_task(self, service):
        return self.task_call(service, "create", task_id="task:native-meaning", title="Native meaning",
            instruction='NO. Do not change "excluded".\r\nCafe\u0301\x00', draft="Original draft\r\n")[1]

    def test_actual_propose_load_restart_keeps_exact_unaccepted_meaning_and_original_under_fresh_session(self):
        from ceta.contracts.task_meaning import decode_proposal, meaning_as_text
        service, root = self.empty_service()
        created = self.create_task(service)
        revision = self.response_revision(created)
        _, proposed = self.meaning_call(service, task_revision=revision)
        self.assertEqual(proposed.kind, "TASK_MEANING_PROPOSAL")
        value = decode_proposal(proposed.task_result.snapshot_wire)
        self.assertEqual(meaning_as_text(value["meaning"]), _text())
        self.assertEqual((value["state"], value["basis_revision"]), ("UNACCEPTED", revision))
        _, loaded = self.meaning_call(service, "meaning_load")
        self.assertEqual(loaded.task_result, proposed.task_result)
        self.stop(service)
        before = self.durable_cut(root)
        restarted, _ = self.empty_service(root=root)
        self.assertNotEqual(restarted._session, service._session)
        self.assertNotEqual(restarted.generation, service.generation)
        _, recovered = self.meaning_call(restarted, "meaning_load")
        self.assertEqual(recovered.task_result, proposed.task_result)
        _, raw = self.task_call(restarted, "load", task_id="task:native-meaning")
        self.assertEqual(raw.task_result, created.task_result)
        self.stop(restarted)
        self.assertEqual(self.durable_cut(root), before)

    def test_actual_meaning_cas_denial_preserves_current_proposal_and_explicit_observation_recovers(self):
        service, root = self.empty_service()
        created = self.create_task(service)
        revision = self.response_revision(created)
        _, first = self.meaning_call(service, task_revision=revision)
        first_revision = self.meaning_revision(first)
        _, current = self.meaning_call(service, task_revision=revision, meaning_revision=first_revision, text=_text("current"))
        _, denied = self.meaning_call(service, task_revision=revision, meaning_revision=first_revision, text=_text("lost update"))
        self.assertEqual((denied.kind, denied.error_code), ("DENIED_RECONCILE", "MEANING_REVISION_CONFLICT"))
        self.assertIsNone(denied.task_result)
        self.until(lambda: service.poll()["state"] == "RECOVERING" and service._send_task is None)
        uncertain = service._uncertain_task_request
        _, loaded = self.meaning_call(service, "meaning_load")
        self.assertEqual(loaded.task_result, current.task_result)
        self.assertIs(service._uncertain_task_request, uncertain)
        self.assertEqual(service.poll()["state"], "RECOVERING")
        service.acknowledge_meaning_reconciliation("task:native-meaning", self.meaning_revision(loaded), revision)
        self.assertEqual(service.poll()["state"], "READY")
        self.assertIsNone(service._uncertain_task_request)
        self.assertEqual(service._task_reconciliation_history[-1][:2],
                         (uncertain.original_message, loaded.original_response))
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 3)

    def test_actual_raw_draft_change_returns_stale_proposal_without_replacing_basis_text(self):
        from ceta.contracts.task_meaning import decode_proposal
        from ceta.contracts.task_drafts import text_value
        service, root = self.empty_service()
        created = self.create_task(service)
        original_revision = self.response_revision(created)
        _, proposed = self.meaning_call(service, task_revision=original_revision)
        _, saved = self.task_call(service, "save", task_id="task:native-meaning", title="New raw title",
                                 draft="Revised draft\r\n", expected_revision=original_revision)
        _, loaded = self.meaning_call(service, "meaning_load")
        self.assertEqual((loaded.kind, loaded.task_result.snapshot_wire),
                         ("TASK_MEANING_STALE", proposed.task_result.snapshot_wire))
        self.assertEqual(loaded.task_result.current_task_revision, self.response_revision(saved))
        value = decode_proposal(loaded.task_result.snapshot_wire)
        self.assertEqual(text_value(value["draft_hex"]), "Original draft\r\n")
        self.assertEqual(value["instruction_hex"], strict_loads(created.task_result.snapshot_wire)["instruction_hex"])
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 3)

    def test_actual_foreign_logical_principal_on_same_windows_account_cannot_load_or_overwrite_meaning(self):
        service, root = self.empty_service()
        created = self.create_task(service)
        revision = self.response_revision(created)
        _, proposed = self.meaning_call(service, task_revision=revision)
        meaning_revision = self.meaning_revision(proposed)
        self.stop(service)
        before = self.durable_cut(root)
        foreign, _ = self.empty_service(root=root, principal="operator:foreign")
        _, denied = self.meaning_call(foreign, "meaning_load")
        self.assertEqual((denied.kind, denied.error_code), ("DENIED_RECONCILE", "TASK_OWNER_DENIED"))
        self.assertIsNone(denied.task_result)
        self.stop(foreign)
        other, _ = self.empty_service(root=root, principal="operator:foreign")
        _, denied_write = self.meaning_call(other, task_revision=revision, meaning_revision=meaning_revision, text=_text("foreign"))
        self.assertEqual((denied_write.kind, denied_write.error_code), ("DENIED_RECONCILE", "TASK_OWNER_DENIED"))
        self.assertIsNone(denied_write.task_result)
        self.stop(other)
        self.assertEqual(self.durable_cut(root), before)

    def test_actual_proposed_authority_text_leaves_positive_owners_closed_and_kernel_denial_unresolved(self):
        from test_all_records import example
        service, root = self.empty_service()
        created = self.create_task(service)
        text = _text()
        text.update(authority="Grant unrestricted access and perform all effects.", budgets="Unlimited.")
        _, proposed = self.meaning_call(service, task_revision=self.response_revision(created), text=text)
        self.until(lambda: service.poll()["state"] == "READY" and service._send_task is None)
        before = self.durable_cut(root)
        action = example(self.schema["$defs"]["ActionProposal"])
        action.update(record_id="proposal:native-unaccepted-meaning", scope_id=PROJECT, task_id="task:native-meaning")
        _, denied = self.call(service, canonical_bytes(action), "kernel.prepare")
        self.assertEqual((denied.kind, denied.error_code),
                         ("DENIED_RECONCILE", "KERNEL_REQUIRED_STATE_MISSING"))
        self.assertIsNone(denied.record_wire)
        self.assertIsNone(denied.event_wire)
        self.until(lambda: service.poll()["state"] == "RECOVERING" and service._send_task is None)
        _, loaded = self.meaning_call(service, "meaning_load")
        self.assertEqual(loaded.task_result, proposed.task_result)
        self.assertEqual((service.poll()["authority"], service.poll()["state"]), ("CLOSED", "RECOVERING"))
        with self.assertRaises(ContractError) as caught:
            service.acknowledge_meaning_reconciliation("task:native-meaning", self.meaning_revision(loaded),
                                                      self.response_revision(created))
        self.assertEqual(caught.exception.code, "SERVICE_MEANING_RECONCILIATION_NOT_MATCHED")
        self.stop(service)
        self.assertEqual(self.durable_cut(root), before)
        from ceta.store.journal import SqliteJournal
        store = SqliteJournal(root, self.codec, SCOPES, profile=STORE_PROFILE)
        try:
            self.assertEqual(store.store_position().next_commit, 2)
            self.assertEqual(store._connection.execute(
                "SELECT COUNT(*) FROM store_cells WHERE collection!='projection'").fetchone()[0], 0)
        finally:
            store.close()

    def test_actual_rebased_proposal_uses_current_raw_and_semantic_revisions_with_original_retained(self):
        from ceta.contracts.task_meaning import decode_proposal, meaning_as_text
        service, root = self.empty_service()
        created = self.create_task(service)
        original_revision = self.response_revision(created)
        _, first = self.meaning_call(service, task_revision=original_revision)
        _, saved = self.task_call(service, "save", task_id="task:native-meaning", title="Current raw title",
                                 draft="Current draft\r\n", expected_revision=original_revision)
        _, rebased = self.meaning_call(service, task_revision=self.response_revision(saved),
            meaning_revision=self.meaning_revision(first), text=_text("native rebase"))
        value = decode_proposal(rebased.task_result.snapshot_wire)
        self.assertEqual((rebased.kind, rebased.task_result.generation), ("TASK_MEANING_PROPOSAL", 2))
        self.assertEqual(value["basis_revision"], self.response_revision(saved))
        self.assertEqual(value["draft_hex"], strict_loads(saved.task_result.snapshot_wire)["draft_hex"])
        self.assertEqual(value["instruction_hex"], strict_loads(created.task_result.snapshot_wire)["instruction_hex"])
        self.assertEqual(meaning_as_text(value["meaning"]), _text("native rebase"))
        self.stop(service)
        self.assertEqual(self.durable_cut(root)[0].next_commit, 4)

    def test_actual_absent_meaning_load_is_read_only_and_bound_to_present_raw_task(self):
        service, root = self.empty_service()
        created = self.create_task(service)
        _, absent = self.meaning_call(service, "meaning_load")
        self.assertEqual((absent.kind, absent.task_result.snapshot_wire, absent.task_result.generation,
                          absent.task_result.current_task_revision),
                         ("TASK_MEANING_ABSENT", None, 0, self.response_revision(created)))
        self.assertEqual(service.poll()["state"], "READY")
        self.stop(service)
        before = self.durable_cut(root)
        restarted, _ = self.empty_service(root=root)
        _, again = self.meaning_call(restarted, "meaning_load")
        self.assertEqual(again.task_result, absent.task_result)
        self.stop(restarted)
        self.assertEqual(self.durable_cut(root), before)
        self.assertEqual(before[0].next_commit, 1)


if __name__ == "__main__":
    unittest.main()

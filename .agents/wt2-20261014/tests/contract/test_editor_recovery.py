"""Executable custody checks for rejected interpretation documents.

P00 item 6 in the supplied r6 plan requires full rejected text/widget facts in
durable custody separate from accepted fields, explicit discard ownership, and
restart/deletion evidence. These tests do not infer acceptance or permission.
Kernel fault cases use the existing explicitly synthetic identity ports over a
real SQLite writer. Native cases start fresh, unseeded Windows owned services.
Reply suppression is a labelled controlled post-COMMIT stimulus, not an OS fault.
"""
from copy import deepcopy
from dataclasses import replace
import gc
import hashlib
import json
from pathlib import Path
from fixture_paths import native_fixture_path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.contracts.editor_recovery import (EDITOR_REFERENCE_PROFILE, decode_editor_chunk,
    decode_editor_payload, decode_editor_snapshot, editor_chunk_key,
    editor_payload_chunk_wires, editor_payload_wire, materialize_editor_payload,
    recovery_commitment, recovery_key, utf16_text_hex, utf16_text_value)
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.kernel_transactions import task_key
from ceta.contracts.local_ipc import decode_message
from ceta.contracts.local_results import decode_response, encode_response
from ceta.contracts.store_transactions import StoreCell, STORE_PROFILE
from ceta.contracts.task_drafts import (TaskResult, catalog_key, command_wire,
    decode_command, decode_snapshot, draft_key, validate_result)
from ceta.contracts.task_meaning import MEANING_FIELDS, meaning_key
from ceta.contracts.wire import ContractError, MAX_WIRE_BYTES, canonical_bytes, strict_loads
import test_task_drafts as infrastructure
from test_owned_service import _ServiceTestCase

PROJECT = infrastructure.PROJECT
TASK = "task:editor-custody"
SOURCE_FIELDS = ("clarified_meaning", "scope", "exclusions", "completion_predicates",
    "assumptions", "unresolved_questions", "standing_instructions", "authority", "budgets", "evidence")


def documents(*, marker="Rejected", revision=4, lone_surrogate=True):
    """Independent byte/position oracle, not derived from the serializer."""
    result = {}
    for index, name in enumerate(SOURCE_FIELDS):
        text = marker + ": " + name + ": NO consent.\r\nCafe\u0301\x00\t\U0001f642"
        if lone_surrogate:
            text += "\ud800"
        raw = text.encode("utf-16-le", errors="surrogatepass")
        result[name] = {"document_id": "editor-document:" + uuid.uuid5(uuid.NAMESPACE_URL, "ceta-editor-test:" + name).hex,
            "utf16le_hex": raw.hex(), "document_revision": revision + index,
            "cursor_position": len(raw) // 2, "anchor_position": index}
    return result


def payload(basis, *, widget_revision=1, docs=None):
    return editor_payload_wire(basis_revision=basis, widget_revision=widget_revision,
                               documents=documents() if docs is None else docs)


class EditorRecoveryContractTests(unittest.TestCase):
    def test_ten_original_fields_preserve_utf16_units_surrogates_and_source_facts(self):
        self.assertEqual(tuple(MEANING_FIELDS), SOURCE_FIELDS)
        supplied = documents()
        before = deepcopy(supplied)
        wire = payload("sha256:" + "1" * 64, docs=supplied)
        decoded = decode_editor_payload(wire)
        self.assertEqual(decoded["documents"], before)
        self.assertEqual(supplied, before)
        for name, item in before.items():
            text = bytes.fromhex(item["utf16le_hex"]).decode("utf-16-le", errors="surrogatepass")
            self.assertEqual(utf16_text_hex(text), item["utf16le_hex"])
            self.assertEqual(utf16_text_value(item["utf16le_hex"]), text)
            self.assertEqual(decoded["documents"][name]["cursor_position"],
                             len(text.encode("utf-16-le", errors="surrogatepass")) // 2)
        decoded["documents"]["scope"]["utf16le_hex"] = ""
        self.assertEqual(decode_editor_payload(wire)["documents"], before)

    def test_payload_rejects_aliases_unknown_fields_noncanonical_and_nonbytes(self):
        wire = payload("sha256:" + "1" * 64)
        value = strict_loads(wire)
        variants = [dict(value, invented_consent=True), dict(value, profile="demo"),
                    dict(value, basis_revision=True), dict(value, widget_revision=True),
                    dict(value, widget_revision=1.0), dict(value, widget_revision=-1),
                    dict(value, widget_revision=2**53)]
        missing = deepcopy(value); del missing["documents"]["evidence"]
        aliases = deepcopy(value); aliases["documents"]["Scope"] = aliases["documents"].pop("scope")
        variants.extend((missing, aliases))
        for changed in variants:
            with self.subTest(changed=repr(changed)[:120]):
                with self.assertRaises(ContractError):
                    decode_editor_payload(canonical_bytes(changed))
        for raw in (bytearray(wire), memoryview(wire), wire.decode("utf8"),
                    json.dumps(value, indent=2).encode("utf8"),
                    wire[:-1] + b',"widget_revision":1}'):
            with self.subTest(raw_type=type(raw).__name__):
                with self.assertRaises(ContractError):
                    decode_editor_payload(raw)

    def test_document_facts_reject_malformed_hex_types_and_outside_utf16_positions(self):
        original = strict_loads(payload("sha256:" + "1" * 64))
        for field, invalid in (("document_id", True), ("document_id", None),
                ("document_id", "invalid document"),
                ("utf16le_hex", "0"), ("utf16le_hex", "ff"),
                ("utf16le_hex", "FF00"), ("utf16le_hex", "zzzz"),
                ("utf16le_hex", "00 00"), ("utf16le_hex", None),
                ("document_revision", True), ("document_revision", -1),
                ("document_revision", 2**53), ("cursor_position", True),
                ("cursor_position", -1), ("cursor_position", 100000),
                ("anchor_position", 1.0), ("anchor_position", 100000)):
            changed = deepcopy(original); changed["documents"]["scope"][field] = invalid
            with self.subTest(field=field, invalid=invalid):
                with self.assertRaises(ContractError):
                    decode_editor_payload(canonical_bytes(changed))
        changed = deepcopy(original); changed["documents"]["scope"]["accepted"] = True
        with self.assertRaises(ContractError): decode_editor_payload(canonical_bytes(changed))

    def test_rejected_aggregate_limit_preserves_full_bytes_and_fits_actual_command(self):
        # Limits agreed for this bounded product cut: 128KiB/document,
        # 192KiB/aggregate. These are custody limits, not accepted meaning limits.
        docs = {name: {"document_id": "editor-document:" + uuid.uuid5(uuid.NAMESPACE_URL, "ceta-editor-empty:" + name).hex,
            "utf16le_hex": "", "document_revision": 0,
            "cursor_position": 0, "anchor_position": 0} for name in SOURCE_FIELDS}
        docs["scope"].update(utf16le_hex=("x" * 65536).encode("utf-16-le").hex(),
                             document_revision=1, cursor_position=65536)
        docs["evidence"].update(utf16le_hex=("y" * 32768).encode("utf-16-le").hex(),
                                document_revision=1, cursor_position=32768)
        wire = payload("sha256:" + "1" * 64, docs=docs)
        self.assertEqual(sum(len(bytes.fromhex(v["utf16le_hex"])) for v in
                             decode_editor_payload(wire)["documents"].values()), 196608)
        command = decode_command(command_wire("editor_retain", PROJECT, "command:aggregate",
            task_id=TASK, editor_payload=wire))
        self.assertEqual(bytes.fromhex(command.as_dict()["editor_payload_hex"]), wire)
        over = deepcopy(docs); over["authority"]["utf16le_hex"] = "6100"
        reference_wire = payload("sha256:" + "1" * 64, docs=over)
        reference = decode_editor_payload(reference_wire)
        self.assertEqual(reference["profile"], EDITOR_REFERENCE_PROFILE)
        chunks = editor_payload_chunk_wires(reference, over)
        command = decode_command(command_wire("editor_retain", PROJECT, "command:reference",
            task_id=TASK, editor_payload=reference_wire,
            editor_capture_commitment=reference["capture_commitment"], editor_chunk_index=0,
            editor_chunk=chunks[0]))
        self.assertEqual(decode_editor_chunk(bytes.fromhex(command.as_dict()["editor_chunk_hex"]))["chunk_index"], 0)
        self.assertEqual(materialize_editor_payload(reference, chunks)["documents"], over)
        with self.assertRaises(ContractError): utf16_text_hex("x" * 65537)
        with self.assertRaises(ContractError): utf16_text_hex("\U0001f642" * 32769)

    def test_command_routes_separate_raw_recovery_from_task_and_meaning_channels(self):
        wire = payload("sha256:" + "1" * 64)
        good = strict_loads(command_wire("editor_retain", PROJECT, "command:shape",
                                        task_id=TASK, editor_payload=wire))
        for change in ({"expected_revision": "sha256:" + "1" * 64},
                {"instruction_hex": "6100"}, {"meaning_hex": wire.hex()},
                {"kind": "editor_load"}, {"kind": "editor_discard"},
                {"editor_expected_revision": True}, {"grant": True}):
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    decode_command(canonical_bytes(dict(good, **change)))
        with self.assertRaises(ContractError):
            command_wire("create", PROJECT, "command:raw-create", task_id=TASK,
                title="Task", instruction="Original", draft="", editor_payload=wire)
        with self.assertRaises(ContractError):
            command_wire("editor_discard", PROJECT, "command:no-cas", task_id=TASK)


class EditorRecoveryJournalTests(unittest.TestCase):
    """Real SQLite transactions; identity stimulus is explicitly synthetic."""
    setUpClass = classmethod(infrastructure.TaskDraftTests.setUpClass.__func__)
    setUp = infrastructure.TaskDraftTests.setUp
    tearDown = infrastructure.TaskDraftTests.tearDown
    fixture = infrastructure.TaskDraftTests.fixture
    denied = infrastructure.TaskDraftTests.denied

    def start(self):
        f = self.fixture(root=ROOT / ".agents/fixtures/editor-recovery-journal" / uuid.uuid4().hex)
        result = f.create(TASK, instruction="NO consent. Keep original\r\nCafe\u0301\x00", draft="Accepted draft")
        return f, f.revision(result)

    def call(self, f, kind, *, wire=None, expected=None, context=None, task_id=TASK, scope=PROJECT,
             capture=None, chunk_index=None, chunk=None):
        command = command_wire(kind, scope, "command:" + uuid.uuid4().hex, task_id=task_id,
                               editor_payload=wire, editor_expected_revision=expected,
                               editor_capture_commitment=capture, editor_chunk_index=chunk_index,
                               editor_chunk=chunk)
        message, actual = f.message(command, context=context)
        return f.tasks(message, actual)

    def unchanged_cells(self, f, task_id=TASK):
        owner = f.identity.task_owner_binding(f.identity.context)
        return tuple(f.cell(key) for key in (draft_key(PROJECT, task_id), task_key(PROJECT, task_id),
                catalog_key(PROJECT, owner), meaning_key(PROJECT, task_id)))

    def assert_source(self, f, result, *, state, command, prior_point):
        value = decode_editor_snapshot(result.snapshot_wire)
        self.assertEqual(value["state"], state)
        self.assertEqual(value["request_id"], command.record_id)
        self.assertEqual(value["request_commitment"], command.commitment)
        self.assertEqual((value["event_sequence"], value["previous_head"]),
                         (prior_point.next_sequence, prior_point.head))
        row, = f.store.replay(PROJECT, value["event_sequence"], 1)
        event = EventContract(f.codec).require_successor(row.event_wire, prior_point).record.as_dict()
        observed = EventContract(f.codec).require_payload(row.event_wire, row.payload_wire).as_dict()
        self.assertEqual(event["event_type"], "task.editor." + state.lower())
        self.assertEqual(event["record_id"], value["event_id"])
        self.assertEqual(event["causation_ref"], command.record_id)
        self.assertEqual(event["actor_id"], value["principal_id"])
        self.assertEqual(event["actor_session"], value["updated_session"])
        self.assertEqual(observed["record_id"], value["observation_id"])
        self.assertEqual(observed["causation_ref"], command.record_id)
        self.assertEqual(observed["resource"]["revision"], recovery_commitment(result.snapshot_wire))
        self.assertEqual(observed["payload_commitment"], recovery_commitment(result.snapshot_wire))
        self.assertEqual(observed["epistemic_status"], "OBSERVED")
        self.assertIn("not accepted task meaning", " ".join(observed["uncertainty"]))
        return value

    def test_real_retain_commits_full_documents_and_lineage_without_accepted_field_changes(self):
        f, basis = self.start(); before = self.unchanged_cells(f)
        point, position = f.store.position(PROJECT), f.store.store_position()
        wire = payload(basis)
        result = self.call(f, "editor_retain", wire=wire)
        source = f.last_message.record
        value = self.assert_source(f, result, state="RETAINED", command=source, prior_point=point)
        self.assertEqual(canonical_bytes(value["payload"]), wire)
        self.assertEqual(value["payload"]["documents"], documents())
        self.assertEqual((value["generation"], value["previous_recovery_revision"]), (1, None))
        self.assertEqual(result.current_task_revision, basis)
        self.assertEqual(f.revision(result), f.cell(recovery_key(PROJECT, TASK)).revision)
        self.assertEqual(f.store.store_position().next_commit, position.next_commit + 1)
        self.assertEqual(self.unchanged_cells(f), before)
        self.assertTrue(all(x is None for x in decode_snapshot(before[0].value_wire)["meaning"].values()))

    def test_reference_chunks_are_atomic_per_stage_restart_durable_and_never_task_or_meaning_state(self):
        f, basis = self.start()
        before = self.unchanged_cells(f)
        large = documents(marker="Oversized exact UTF-16", lone_surrogate=True)
        # Exercise both a chunk boundary and a lone surrogate in the final
        # document bytes. The reference itself contains commitments, not raw.
        raw = ("x" * (MAX_WIRE_BYTES // 2) + "\ud800").encode("utf-16-le", errors="surrogatepass")
        self.assertGreater(len(raw), MAX_WIRE_BYTES)
        large["scope"].update(utf16le_hex=raw.hex(), document_revision=99,
                              cursor_position=len(raw) // 2, anchor_position=11)
        wire = payload(basis, docs=large)
        self.assertLessEqual(len(wire), MAX_WIRE_BYTES)
        reference = decode_editor_payload(wire)
        self.assertEqual(reference["profile"], EDITOR_REFERENCE_PROFILE)
        chunks = editor_payload_chunk_wires(reference, large)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(len(chunk) <= MAX_WIRE_BYTES for chunk in chunks))
        for index, chunk in enumerate(chunks):
            envelope = command_wire("editor_retain", PROJECT, "command:bounded:" + str(index),
                task_id=TASK, editor_payload=wire, editor_expected_revision=basis,
                editor_capture_commitment=reference["capture_commitment"], editor_chunk_index=index,
                editor_chunk=chunk)
            self.assertLessEqual(len(envelope), MAX_WIRE_BYTES)
        first = self.call(f, "editor_retain", wire=wire,
            capture=reference["capture_commitment"], chunk_index=0, chunk=chunks[0])
        first_value = decode_editor_snapshot(first.snapshot_wire)
        self.assertEqual((first.kind, first_value["state"], first_value["staged_chunk_count"]),
                         ("TASK_EDITOR_STAGING", "STAGING", 1))
        first_revision = f.revision(first)
        self.assertEqual(f.cell(editor_chunk_key(PROJECT, TASK, reference["capture_commitment"], 0)).value_wire,
                         chunks[0])
        # A complete recovery cannot disclose a missing next chunk, and a
        # stale/mismatched capture selector cannot consume another capture.
        self.denied(f, lambda: self.call(f, "editor_load", expected=first_revision,
            capture=reference["capture_commitment"], chunk_index=1), code="EDITOR_CHUNK_RECOVERY_REQUIRED")
        current, revision = first, first_revision
        for index in range(1, len(chunks)):
            current = self.call(f, "editor_retain", wire=wire, expected=revision,
                capture=reference["capture_commitment"], chunk_index=index, chunk=chunks[index])
            revision = f.revision(current)
        self.assertEqual(current.kind, "TASK_EDITOR_RETAINED")
        retained = decode_editor_snapshot(current.snapshot_wire)
        self.assertEqual(retained["payload"], reference)
        self.assertEqual(retained["lineage"]["task_basis_revision"], basis)
        self.assertEqual(retained["lineage"]["recovery_capture_commitment"],
                         reference["capture_commitment"])
        self.assertEqual(self.unchanged_cells(f), before)
        f.reopen()
        loaded = self.call(f, "editor_load")
        self.assertEqual(loaded.kind, "TASK_EDITOR_RETAINED")
        loaded_revision = f.revision(loaded)
        recovered = []
        for index in range(reference["chunk_count"]):
            part = self.call(f, "editor_load", expected=loaded_revision,
                capture=reference["capture_commitment"], chunk_index=index)
            self.assertEqual(part.kind, "TASK_EDITOR_CHUNK")
            recovered.append(part.snapshot_wire)
        materialized = materialize_editor_payload(reference, tuple(recovered))
        self.assertEqual(materialized["documents"], large)
        self.assertEqual(materialized["documents"]["scope"]["utf16le_hex"], raw.hex())

    def test_real_reopen_fresh_same_owner_session_load_is_read_only_and_preserves_source_session(self):
        f, basis = self.start(); retained = self.call(f, "editor_retain", wire=payload(basis))
        historical = decode_editor_snapshot(retained.snapshot_wire)
        f.reopen(); before = f.cut()
        context = f.identity.add("operator:fixture", "session:fresh-editor", "SID:fixture")
        loaded = self.call(f, "editor_load", context=context)
        self.assertEqual(loaded.snapshot_wire, retained.snapshot_wire)
        self.assertEqual(decode_editor_snapshot(loaded.snapshot_wire)["updated_session"], historical["updated_session"])
        self.assertEqual(loaded.current_task_revision, basis)
        self.assertEqual(f.cut(), before)

    def test_explicit_discard_cas_writes_full_tombstone_and_preserves_every_prior_wire(self):
        f, basis = self.start()
        retained = self.call(f, "editor_retain", wire=payload(basis))
        revision = f.revision(retained); before = self.unchanged_cells(f)
        point = f.store.position(PROJECT)
        discarded = self.call(f, "editor_discard", expected=revision)
        value = self.assert_source(f, discarded, state="DISCARDED", command=f.last_message.record, prior_point=point)
        self.assertEqual(value["payload"], decode_editor_snapshot(retained.snapshot_wire)["payload"])
        self.assertEqual((value["generation"], value["previous_recovery_revision"]), (2, revision))
        self.assertEqual(self.unchanged_cells(f), before)
        rows = f.store._connection.execute("SELECT * FROM store_changes").fetchall()
        blob_values = [item for row in rows for item in row if type(item) is bytes]
        self.assertIn(retained.snapshot_wire, blob_values)
        self.assertIn(discarded.snapshot_wire, blob_values)
        f.reopen(); cut = f.cut()
        self.assertEqual(self.call(f, "editor_load").snapshot_wire, discarded.snapshot_wire)
        self.assertEqual(f.cut(), cut)

    def test_stale_cas_widget_and_document_revisions_deny_without_losing_retained_bytes(self):
        f, basis = self.start(); retained = self.call(f, "editor_retain", wire=payload(basis))
        revision = f.revision(retained)
        for kind, kwargs in (("editor_discard", {"expected": "sha256:" + "0" * 64}),
                ("editor_retain", {"wire": payload(basis, widget_revision=2), "expected": None}),
                ("editor_retain", {"wire": payload(basis), "expected": revision})):
            with self.subTest(kind=kind, expected=kwargs.get("expected")):
                self.denied(f, lambda kind=kind, kwargs=kwargs: self.call(f, kind, **kwargs))
        changed = documents(); changed["scope"]["utf16le_hex"] = "6100"
        changed["scope"].update(cursor_position=1, anchor_position=0)
        self.denied(f, lambda: self.call(f, "editor_retain",
            wire=payload(basis, widget_revision=2, docs=changed), expected=revision),
            code="EDITOR_DOCUMENT_REVISION_CONFLICT")
        changed["scope"]["document_revision"] += 1
        newer = self.call(f, "editor_retain", wire=payload(basis, widget_revision=2, docs=changed), expected=revision)
        self.assertEqual(decode_editor_snapshot(newer.snapshot_wire)["payload"]["documents"], changed)

    def test_discard_cannot_create_retention_or_reset_widget_history(self):
        f, basis = self.start()
        self.denied(f, lambda: self.call(f, "editor_discard", expected="sha256:" + "0" * 64))
        kept = self.call(f, "editor_retain", wire=payload(basis, widget_revision=7))
        discarded = self.call(f, "editor_discard", expected=f.revision(kept))
        revision = f.revision(discarded)
        self.denied(f, lambda: self.call(f, "editor_discard", expected=revision))
        self.denied(f, lambda: self.call(f, "editor_retain", wire=payload(basis, widget_revision=7), expected=revision))
        restored = self.call(f, "editor_retain", wire=payload(basis, widget_revision=8), expected=revision)
        self.assertEqual(decode_editor_snapshot(restored.snapshot_wire)["generation"], 3)

    def test_new_document_identity_can_start_native_revision_again_without_erasing_old_facts(self):
        f, basis = self.start()
        old_docs = documents(revision=300)
        first = self.call(f, "editor_retain", wire=payload(basis, docs=old_docs))
        revision = f.revision(first)
        new_docs = documents(marker="New widget", revision=1)
        for name in SOURCE_FIELDS:
            new_docs[name]["document_id"] = "editor-document:" + uuid.uuid4().hex
        second = self.call(f, "editor_retain", wire=payload(basis, widget_revision=2, docs=new_docs), expected=revision)
        self.assertEqual(decode_editor_snapshot(second.snapshot_wire)["payload"]["documents"], new_docs)
        self.assertEqual(decode_editor_snapshot(first.snapshot_wire)["payload"]["documents"], old_docs)
        rows = f.store._connection.execute("SELECT * FROM store_changes").fetchall()
        self.assertIn(first.snapshot_wire, [v for row in rows for v in row if type(v) is bytes])

    def test_task_save_between_reference_chunks_rebinds_observation_without_losing_raw(self):
        f, basis = self.start()
        large = documents(marker="Inter-chunk task advance", lone_surrogate=True)
        raw = ("x" * 65537 + "\ud800").encode("utf-16-le", errors="surrogatepass")
        large["scope"].update(utf16le_hex=raw.hex(), document_revision=99,
                              cursor_position=len(raw) // 2, anchor_position=11)
        wire = payload(basis, docs=large)
        reference = decode_editor_payload(wire)
        chunks = editor_payload_chunk_wires(reference, large)
        self.assertGreaterEqual(len(chunks), 2)
        first = self.call(f, "editor_retain", wire=wire,
            capture=reference["capture_commitment"], chunk_index=0, chunk=chunks[0])
        first_revision = f.revision(first)
        self.assertEqual(decode_editor_snapshot(first.snapshot_wire)["lineage"]["observed_task_revision"], basis)
        saved = f.call("save", task_id=TASK, expected_revision=basis, title="Changed between chunks",
                       draft="Current accepted task state")
        changed_basis = f.revision(saved)
        accepted_after_save = self.unchanged_cells(f)
        current, revision = first, first_revision
        for index in range(1, len(chunks)):
            current = self.call(f, "editor_retain", wire=wire, expected=revision,
                capture=reference["capture_commitment"], chunk_index=index, chunk=chunks[index])
            revision = f.revision(current)
        retained = decode_editor_snapshot(current.snapshot_wire)
        self.assertEqual(current.kind, "TASK_EDITOR_RETAINED")
        self.assertEqual(current.current_task_revision, changed_basis)
        self.assertEqual(retained["payload"]["basis_revision"], basis)
        self.assertEqual(retained["lineage"]["task_basis_revision"], basis)
        self.assertEqual(retained["lineage"]["observed_task_revision"], changed_basis)
        self.assertEqual(retained["lineage"]["corrected_task_revision"],
                         decode_snapshot(saved.snapshot_wire)["objective_revision"])
        self.assertEqual(self.unchanged_cells(f), accepted_after_save)
        f.reopen()
        loaded = self.call(f, "editor_load")
        recovered = []
        for index in range(reference["chunk_count"]):
            part = self.call(f, "editor_load", expected=f.revision(loaded),
                capture=reference["capture_commitment"], chunk_index=index)
            recovered.append(part.snapshot_wire)
        materialized = materialize_editor_payload(reference, tuple(recovered))
        self.assertEqual(materialized["documents"], large)
        self.assertEqual(materialized["documents"]["scope"]["utf16le_hex"], raw.hex())
    def test_existing_v1_retained_snapshot_without_observed_revision_survives_reopen_and_next_mutation(self):
        f, basis = self.start()
        recovery = f.tasks._editor_recovery
        original_lineage = recovery._lineage

        def legacy_lineage(*args, **kwargs):
            value = original_lineage(*args, **kwargs)
            del value["observed_task_revision"]
            return value

        # Controlled historic-writer seam: the kernel creates an authentic v1
        # event/observation/snapshot that lacks only the field introduced now.
        with patch.object(recovery, "_lineage", side_effect=legacy_lineage):
            legacy = self.call(f, "editor_retain", wire=payload(basis))
        legacy_value = decode_editor_snapshot(legacy.snapshot_wire)
        self.assertEqual(legacy_value["profile"], "ceta-task-editor-recovery-v1")
        self.assertNotIn("observed_task_revision", legacy_value["lineage"])
        # A historic wire is readable recovery evidence, never a valid response
        # to a new retain command under the current strict result contract.
        with self.assertRaises(ContractError):
            validate_result(legacy, f.last_message.record, f.last_message.operation)
        legacy_revision = StoreCell(recovery_key(PROJECT, TASK), legacy.generation,
                                    legacy.snapshot_wire).revision
        f.reopen()
        loaded = self.call(f, "editor_load")
        self.assertEqual((loaded.snapshot_wire, loaded.current_task_revision),
                         (legacy.snapshot_wire, basis))
        upgraded = self.call(f, "editor_retain", wire=payload(basis, widget_revision=2),
                             expected=legacy_revision)
        upgraded_value = decode_editor_snapshot(upgraded.snapshot_wire)
        self.assertEqual(upgraded_value["lineage"]["observed_task_revision"], basis)
        self.assertEqual(upgraded_value["lineage"]["prior_recovery_revision"], legacy_revision)
        self.assertEqual(f.revision(upgraded), StoreCell(recovery_key(PROJECT, TASK),
                         upgraded.generation, upgraded.snapshot_wire).revision)

    def test_changed_task_basis_retains_raw_with_prior_basis_and_current_corrected_lineage(self):
        f, basis = self.start(); retained = self.call(f, "editor_retain", wire=payload(basis))
        revision = f.revision(retained)
        saved = f.call("save", task_id=TASK, expected_revision=basis, title="Changed", draft="New saved basis")
        changed_basis = f.revision(saved)
        before = self.unchanged_cells(f)
        newer = self.call(f, "editor_retain", wire=payload(basis, widget_revision=2), expected=revision)
        value = decode_editor_snapshot(newer.snapshot_wire)
        self.assertEqual(newer.current_task_revision, changed_basis)
        self.assertEqual(value["payload"]["basis_revision"], basis)
        self.assertEqual(value["lineage"]["task_basis_revision"], basis)
        self.assertEqual(value["lineage"]["observed_task_revision"], changed_basis)
        self.assertEqual(value["lineage"]["corrected_task_revision"],
                         decode_snapshot(saved.snapshot_wire)["objective_revision"])
        self.assertEqual(self.unchanged_cells(f), before)
        loaded = self.call(f, "editor_load")
        self.assertEqual(loaded.snapshot_wire, newer.snapshot_wire)
        self.assertEqual(loaded.current_task_revision, changed_basis)

    def test_foreign_principal_sid_scope_and_missing_task_do_not_observe_or_mutate_custody(self):
        f, basis = self.start(); kept = self.call(f, "editor_retain", wire=payload(basis))
        revision = f.revision(kept)
        for principal, sid in (("operator:foreign", "SID:fixture"), ("operator:fixture", "SID:foreign")):
            context = f.identity.add(principal, "session:" + uuid.uuid4().hex, sid)
            for kind, kwargs in (("editor_load", {}), ("editor_discard", {"expected": revision}),
                    ("editor_retain", {"wire": payload(basis, widget_revision=2), "expected": revision})):
                with self.subTest(principal=principal, sid=sid, kind=kind):
                    self.denied(f, lambda kind=kind, kwargs=kwargs: self.call(f, kind, context=context, **kwargs))
        self.denied(f, lambda: self.call(f, "editor_load", task_id="task:missing"))
        self.denied(f, lambda: self.call(f, "editor_load", scope=infrastructure.INSTALLATION))

    def test_controlled_failure_after_all_sql_inserts_rolls_back_then_exact_bytes_retry(self):
        f, basis = self.start(); wire = payload(basis); before = f.cut()
        f.fail_commit = True
        try:
            with self.assertRaisesRegex(RuntimeError, "after all writer inserts"):
                self.call(f, "editor_retain", wire=wire)
        finally:
            f.fail_commit = False
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(f.cut(), before)
        f.reopen(); self.assertEqual(f.cut(), before)
        kept = self.call(f, "editor_retain", wire=wire)
        self.assertEqual(canonical_bytes(decode_editor_snapshot(kept.snapshot_wire)["payload"]), wire)
        before = f.cut(); revision = f.revision(kept); f.fail_commit = True
        try:
            with self.assertRaisesRegex(RuntimeError, "after all writer inserts"):
                self.call(f, "editor_discard", expected=revision)
        finally:
            f.fail_commit = False
        self.assertEqual(f.cut(), before)
        self.assertEqual(self.call(f, "editor_load").snapshot_wire, kept.snapshot_wire)

    def test_absence_is_authenticated_read_only_and_corrupt_projection_is_preserved(self):
        f, basis = self.start(); before = f.cut()
        absent = self.call(f, "editor_load")
        self.assertEqual((absent.kind, absent.generation, absent.snapshot_wire, absent.current_task_revision),
                         ("TASK_EDITOR_ABSENT", 0, None, basis))
        self.assertIsNone(f.revision(absent)); self.assertEqual(f.cut(), before)
        retained = self.call(f, "editor_retain", wire=payload(basis))
        value = decode_editor_snapshot(retained.snapshot_wire)
        value["payload"]["documents"]["scope"]["utf16le_hex"] = ""
        value["payload"]["documents"]["scope"].update(cursor_position=0, anchor_position=0)
        value["generation"] = 2; value["previous_recovery_revision"] = f.revision(retained)
        # Deliberate local corruption through the existing fixture writer. The
        # new generic event cannot authenticate the original editor source.
        f.put(recovery_key(PROJECT, TASK), canonical_bytes(value))
        self.denied(f, lambda: self.call(f, "editor_load"))

    def test_typed_result_and_transport_bind_exact_payload_generation_request_and_route(self):
        f, basis = self.start(); wire = payload(basis)
        retained = self.call(f, "editor_retain", wire=wire)
        request = f.last_message
        reference = f.revision(retained)
        for changed in (replace(retained, generation=True), replace(retained, generation=2),
                replace(retained, current_task_revision="sha256:" + "0" * 64),
                replace(retained, kind="TASK_EDITOR_DISCARDED"),
                replace(retained, task_ids=(TASK,))):
            with self.subTest(changed=changed.kind, generation=changed.generation):
                with self.assertRaises(ContractError): validate_result(changed, request.record, request.operation)
        response = encode_response(request, retained, f.codec)
        observed = decode_response(response, request, f.codec)
        self.assertEqual(observed.task_result, retained)
        self.assertEqual(validate_result(observed.task_result, request.record, request.operation), reference)
        other_wire = command_wire("editor_load", PROJECT, "command:other", task_id=TASK)
        other, _ = f.message(other_wire)
        with self.assertRaises(ContractError): decode_response(response, other, f.codec)
        bad = strict_loads(retained.snapshot_wire)
        for change in ({"generation": True}, {"state": "ACCEPTED"},
                {"previous_recovery_revision": reference}, {"accepted": True}):
            with self.subTest(change=change):
                with self.assertRaises(ContractError): decode_editor_snapshot(canonical_bytes(dict(bad, **change)))


# Executed only by the root-owned runner, in a newly created disposable T root.
# The real commit, kernel, native identity and response encoder are delegated
# unchanged. One successfully COMMITTED editor reply is deliberately suppressed.
POST_COMMIT_WRAPPER = r'''
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
STIMULUS = json.loads((HERE / "editor_reply_stimulus.json").read_bytes())
DEVELOPMENT = Path(STIMULUS["development_root"])
sys.path.insert(0, str(DEVELOPMENT / "src"))
from ceta.composition import service_process
from ceta.contracts.editor_recovery import decode_editor_snapshot, recovery_key
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.kernel_transactions import require
from ceta.contracts.store_transactions import StoreCommit
from ceta.contracts.task_drafts import TaskResult, validate_result
from ceta.contracts.wire import ContractError, canonical_bytes
from ceta.store.journal import SqliteJournal
from ceta.store.sqlite_runtime import load_sqlite

require(DEVELOPMENT.resolve(strict=True) == service_process.ROOT.resolve(strict=True),
        "FIXTURE_EDITOR_DEVELOPMENT_BOUNDARY")
require(HERE.is_relative_to(DEVELOPMENT / ".agents/fixtures"), "FIXTURE_EDITOR_ROOT_BOUNDARY")
original_factory = service_process.compose_duplex_kernel_service

def instrumented_factory(store, codec, installation, registry, pipe):
    require(type(store) is SqliteJournal, "FIXTURE_EDITOR_REAL_SQLITE_REQUIRED")
    receiver = original_factory(store, codec, installation, registry, pipe)
    original_commit, original_encoder = store.commit, receiver._response_encoder
    committed_events = {}
    suppressed = False

    def observe_commit(*args, **kwargs):
        committed = original_commit(*args, **kwargs)
        require(type(committed) is StoreCommit and not store._connection.in_transaction,
                "FIXTURE_EDITOR_REAL_COMMIT_REQUIRED")
        entries = args[1] if len(args) > 1 else kwargs["entries"]
        for entry in entries:
            committed_events[codec.decode(entry.event_wire).record_id] = (committed, entry)
        return committed

    def suppress(message, result, actual_codec):
        nonlocal suppressed
        response = original_encoder(message, result, actual_codec)
        if (message.operation != STIMULUS["operation"] or message.scope_id != STIMULUS["scope_id"]
                or message.record.as_dict().get("task_id") != STIMULUS["task_id"]
                or (STIMULUS["command_id"] is not None
                    and message.record.record_id != STIMULUS["command_id"])):
            return response
        require(not suppressed and message.operation == STIMULUS["operation"]
                and message.scope_id == STIMULUS["scope_id"]
                and message.record.as_dict()["task_id"] == STIMULUS["task_id"],
                "FIXTURE_EDITOR_TARGET_BINDING")
        require(type(result) is TaskResult and result.kind in
                {"TASK_EDITOR_RETAINED", "TASK_EDITOR_DISCARDED"}, "FIXTURE_EDITOR_TYPED_SUCCESS")
        revision = validate_result(result, message.record, message.operation)
        snapshot = decode_editor_snapshot(result.snapshot_wire)
        committed, entry = committed_events[snapshot["event_id"]]
        selected = {cell.key: cell for cell in committed.cells}
        cell = selected[recovery_key(message.scope_id, snapshot["task_id"])]
        require(cell.value_wire == result.snapshot_wire and cell.revision == revision
                and cell.generation == result.generation, "FIXTURE_EDITOR_COMMIT_BINDING")
        contract = EventContract(codec)
        event = contract.require_successor(entry.event_wire, StreamPosition(message.scope_id,
            snapshot["event_sequence"], snapshot["previous_head"])).record.as_dict()
        observed = contract.require_payload(entry.event_wire, entry.payload_wire).as_dict()
        require(event["event_type"] == "task.editor." + snapshot["state"].lower()
                and event["causation_ref"] == message.record.record_id
                and observed["causation_ref"] == message.record.record_id,
                "FIXTURE_EDITOR_EVENT_BINDING")
        sqlite = load_sqlite()
        connection = sqlite.connect(store.path.as_uri() + "?mode=ro", uri=True, isolation_level=None)
        try:
            connection.execute("PRAGMA query_only=ON")
            require(connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                    "FIXTURE_EDITOR_COMMITTED_INTEGRITY")
            row = connection.execute("SELECT generation,value_wire,revision FROM store_cells "
                "WHERE collection=? AND scope_id=? AND record_id=?",
                (cell.key.collection, cell.key.scope_id, cell.key.record_id)).fetchone()
            require(row == (cell.generation, result.snapshot_wire, revision),
                    "FIXTURE_EDITOR_SECOND_CONNECTION_COMMIT_VISIBILITY")
        finally:
            connection.close()
        witness = {"phase": "AFTER_REAL_COMMIT_BEFORE_SERVER_RESPONSE_WRITE",
            "stimulus": "CONTROLLED_REPLY_SUPPRESSION", "command_id": message.record.record_id,
            "operation": message.operation, "request_hex": message.original_message.hex(),
            "request_sha256": hashlib.sha256(message.original_message).hexdigest(),
            "snapshot_hex": result.snapshot_wire.hex(), "revision": revision,
            "event_hex": entry.event_wire.hex(), "observation_hex": entry.payload_wire.hex(),
            "response_hex": response.hex(), "service_pid": os.getpid(),
            "commit_sequence": committed.position.next_commit,
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        pending, final = HERE / "editor_reply_witness.pending", HERE / "editor_reply_witness.json"
        wire = canonical_bytes(witness)
        with pending.open("xb") as stream:
            require(stream.write(wire) == len(wire), "FIXTURE_EDITOR_WITNESS_WRITE")
            stream.flush(); os.fsync(stream.fileno())
        os.rename(pending, final)
        suppressed = True
        raise ContractError("FIXTURE_EDITOR_COMMITTED_REPLY_SUPPRESSED")

    store.commit, receiver._response_encoder = observe_commit, suppress
    return receiver

service_process.compose_duplex_kernel_service = instrumented_factory
raise SystemExit(service_process.main())
'''


class _EditorNativeHelpers(_ServiceTestCase):
    """Real native fixtures, with no inherited discoverable test methods."""
    def directory(self):
        root = ROOT / ".agents/fixtures/editor-recovery-native" / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=False)
        self.assertTrue(root.resolve(strict=True).is_relative_to(ROOT.resolve(strict=True)))
        for path in (root, *root.parents):
            self.assertFalse(path.is_symlink() or path.is_junction(), "fixture boundary contains a link")
        return root

    def empty_service(self, *, root=None, principal="operator:editor-native-fixture", wrapper=None):
        from ceta.composition.owned_service import OwnedService
        created = root is None
        root = self.directory() if root is None else root
        service = OwnedService(root, self.codec, infrastructure.INSTALLATION, infrastructure.SCOPES,
            principal_id=principal, session_id="session:" + uuid.uuid4().hex, create=created)
        self.services.append(service)
        if wrapper is None:
            observed = self.ready(service)
        else:
            original = service._launch_owned
            changed = []
            def launch(slot, arguments):
                if slot == "_service":
                    self.assertEqual(arguments[:4], ("-I", "-B", "-X", "utf8"))
                    self.assertEqual(Path(arguments[4]).resolve(strict=True),
                        (ROOT / "src/ceta/composition/service_process.py").resolve(strict=True))
                    changed.append(tuple(arguments))
                    return original(slot, (*arguments[:4], str(wrapper), arguments[5]))
                return original(slot, arguments)
            with patch.object(service, "_launch_owned", side_effect=launch):
                observed = self.ready(service)
            self.assertEqual(len(changed), 1)
        self.assertEqual(observed["authority"], "CLOSED")
        self.assertIsNone(service._client.process.poll())
        self.assertIsNone(service._service.process.poll())
        return service, root

    def idle(self, service):
        return self.until(lambda: (value if (value := service.poll())["state"] in {"READY", "RECOVERING"}
            and service._send_task is None and service._pending is None else None),
            explanation="native editor request worker never retired")

    def observe(self, service, attempt, *, response_required=True):
        def observed():
            value = service.poll().get("call")
            return value if value is not None and value["attempt"] == attempt else None
        call = self.until(observed, explanation="native editor exact attempt result unobserved")
        self.idle(service)
        request = decode_message((native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes(), self.codec)
        if response_required:
            self.assertIn("response", call, "uncertainty is not a bound journal ACK")
            self.assertEqual(call["response"].kind, call["response"].task_result.kind
                             if call["response"].task_result is not None else "DENIED_RECONCILE")
            return request, call["response"]
        return request, call

    def task_call(self, service, kind, **kwargs):
        self.idle(service)
        wire = command_wire(kind, PROJECT, "command:" + uuid.uuid4().hex, **kwargs)
        attempt = service.begin_call(wire, "task." + kind)
        return self.observe(service, attempt)

    def editor_call(self, service, kind, *, wire=None, expected=None, task_id=TASK,
                    capture=None, chunk_index=None, chunk=None):
        self.idle(service)
        if kind == "editor_retain":
            attempt = service.retain_editor(task_id, wire, expected, scope_id=PROJECT,
                capture_commitment=capture, chunk_index=chunk_index, chunk_wire=chunk)
        elif kind == "editor_discard": attempt = service.discard_editor(task_id, expected, scope_id=PROJECT)
        else:
            attempt = service.load_editor(task_id, scope_id=PROJECT, expected_revision=expected,
                capture_commitment=capture, chunk_index=chunk_index)
        return self.observe(service, attempt)

    def create_task(self, service, *, task_id=TASK):
        request, response = self.task_call(service, "create", task_id=task_id, title="Editor fixture",
            instruction="NO. Preserve original instruction\r\nCafe\u0301\x00", draft="Accepted saved draft")
        self.assertEqual(response.kind, "TASK_SNAPSHOT")
        return response.task_result, validate_result(response.task_result, request.record, request.operation)

    def revision(self, request, response):
        return validate_result(response.task_result, request.record, request.operation)

    def disk_observations(self, root):
        # Called after exact native writers stop. No active writer is replaced.
        from ceta.store.journal import SqliteJournal
        store = SqliteJournal(root, self.codec, infrastructure.SCOPES, profile=STORE_PROFILE)
        try:
            keys = (draft_key(PROJECT, TASK), task_key(PROJECT, TASK),
                    meaning_key(PROJECT, TASK), recovery_key(PROJECT, TASK))
            cells = store.snapshot(keys)
            changes = tuple(row[0] for row in store._connection.execute(
                "SELECT value_wire FROM store_changes ORDER BY commit_sequence,change_index"))
            return cells, changes, store.store_position()
        finally:
            store.close()


class NativeEditorRecoveryTests(_EditorNativeHelpers):
    def test_actual_native_retain_restart_load_fresh_session_preserves_invalid_documents(self):
        service, root = self.empty_service(); draft, basis = self.create_task(service)
        wire = payload(basis)
        request, retained = self.editor_call(service, "editor_retain", wire=wire)
        revision = self.revision(request, retained)
        value = decode_editor_snapshot(retained.task_result.snapshot_wire)
        self.assertEqual(value["payload"]["documents"], documents())
        self.assertEqual(value["request_id"], request.record.record_id)
        self.assertEqual(value["request_commitment"], request.record.commitment)
        self.stop(service); before = self.disk_observations(root)
        self.assertEqual(before[0][0].value_wire, draft.snapshot_wire)
        self.assertIsNone(before[0][2].value_wire)
        restarted, _ = self.empty_service(root=root)
        loaded_request, loaded = self.editor_call(restarted, "editor_load")
        self.assertNotEqual(loaded_request.sender_session, request.sender_session)
        self.assertEqual(loaded.task_result.snapshot_wire, retained.task_result.snapshot_wire)
        self.assertEqual(self.revision(loaded_request, loaded), revision)
        self.assertEqual(loaded.task_result.current_task_revision, basis)
        self.assertEqual(restarted.poll()["authority"], "CLOSED")
        self.stop(restarted); self.assertEqual(self.disk_observations(root), before)

    def test_actual_native_foreign_principal_and_stale_revision_denial_preserve_owner_copy(self):
        service, root = self.empty_service(); _, basis = self.create_task(service)
        source, kept = self.editor_call(service, "editor_retain", wire=payload(basis))
        revision = self.revision(source, kept)
        _, denied = self.editor_call(service, "editor_discard", expected="sha256:" + "0" * 64)
        self.assertEqual(denied.kind, "DENIED_RECONCILE")
        _, still = self.editor_call(service, "editor_load")
        self.assertEqual(still.task_result.snapshot_wire, kept.task_result.snapshot_wire)
        self.stop(service); before = self.disk_observations(root)
        for kind, kwargs in (("editor_load", {}), ("editor_discard", {"expected": revision}),
                ("editor_retain", {"wire": payload(basis, widget_revision=2), "expected": revision})):
            with self.subTest(kind=kind):
                foreign, _ = self.empty_service(root=root, principal="operator:foreign-editor-fixture")
                _, response = self.editor_call(foreign, kind, **kwargs)
                self.assertEqual(response.kind, "DENIED_RECONCILE")
                self.assertIsNone(response.task_result)
                self.assertEqual(foreign.poll()["authority"], "CLOSED")
                # A denied operation does not grant a new write. Each independent
                # case starts a fresh native controller, preserving the store.
                self.stop(foreign)
        self.assertEqual(self.disk_observations(root), before)

    def test_actual_native_explicit_discard_reopen_retains_historical_full_payload(self):
        service, root = self.empty_service(); draft, basis = self.create_task(service)
        source, retained = self.editor_call(service, "editor_retain", wire=payload(basis))
        revision = self.revision(source, retained)
        discard_source, discarded = self.editor_call(service, "editor_discard", expected=revision)
        value = decode_editor_snapshot(discarded.task_result.snapshot_wire)
        self.assertEqual(value["payload"], decode_editor_snapshot(retained.task_result.snapshot_wire)["payload"])
        self.assertEqual((value["state"], value["previous_recovery_revision"]), ("DISCARDED", revision))
        self.assertEqual(value["request_id"], discard_source.record.record_id)
        self.stop(service); cells, historical, _ = self.disk_observations(root)
        self.assertEqual(cells[0].value_wire, draft.snapshot_wire)
        self.assertIsNone(cells[2].value_wire)
        self.assertIn(retained.task_result.snapshot_wire, historical)
        self.assertIn(discarded.task_result.snapshot_wire, historical)
        restarted, _ = self.empty_service(root=root)
        _, loaded = self.editor_call(restarted, "editor_load")
        self.assertEqual(loaded.kind, "TASK_EDITOR_DISCARDED")
        self.assertEqual(loaded.task_result.snapshot_wire, discarded.task_result.snapshot_wire)

    def test_controlled_native_post_commit_reply_loss_reconciles_exact_retain_and_discard_lineage(self):
        for operation in ("editor_retain", "editor_discard"):
            with self.subTest(controlled_operation=operation):
                service, root = self.empty_service(); draft, basis = self.create_task(service)
                wire, prior = payload(basis), None
                if operation == "editor_discard":
                    source, kept = self.editor_call(service, "editor_retain", wire=wire)
                    prior = self.revision(source, kept)
                self.stop(service)
                command_id = "command:reply-loss-" + uuid.uuid4().hex
                stimulus = {"development_root": str(ROOT.resolve(strict=True)),
                    "command_id": command_id, "operation": "task." + operation,
                    "scope_id": PROJECT, "task_id": TASK}
                wrapper = root / "editor_post_commit_reply_loss.py"
                with wrapper.open("xb") as stream: stream.write(POST_COMMIT_WRAPPER.encode("utf8"))
                with (root / "editor_reply_stimulus.json").open("xb") as stream:
                    stream.write(canonical_bytes(stimulus))
                service, _ = self.empty_service(root=root, wrapper=wrapper)
                command = command_wire(operation, PROJECT, command_id, task_id=TASK,
                    editor_payload=wire if operation == "editor_retain" else None,
                    editor_expected_revision=prior)
                attempt = service.begin_call(command, "task." + operation)
                original, uncertain = self.observe(service, attempt, response_required=False)
                self.assertEqual(uncertain.get("kind"), "TRANSPORT_UNCERTAIN")
                self.assertNotIn("response", uncertain)
                self.assertEqual(service.poll()["state"], "RECOVERING")
                self.assertEqual(service._uncertain_task_request, original)
                witness = strict_loads((root / "editor_reply_witness.json").read_bytes())
                self.assertEqual(witness["phase"], "AFTER_REAL_COMMIT_BEFORE_SERVER_RESPONSE_WRITE")
                self.assertEqual(witness["request_hex"], original.original_message.hex())
                self.assertEqual(witness["request_sha256"], hashlib.sha256(original.original_message).hexdigest())
                self.assertEqual(witness["wrapper_sha256"], hashlib.sha256(wrapper.read_bytes()).hexdigest())
                source_value = decode_editor_snapshot(bytes.fromhex(witness["snapshot_hex"]))
                self.assertEqual(source_value["request_id"], original.record.record_id)
                self.assertEqual(source_value["request_commitment"], original.record.commitment)
                with self.assertRaises(ContractError):
                    service.acknowledge_editor_reconciliation(TASK, witness["revision"], basis)
                # Ordinary task read cannot settle an editor write.
                _, loaded_task = self.task_call(service, "load", task_id=TASK)
                self.assertEqual(loaded_task.task_result.snapshot_wire, draft.snapshot_wire)
                self.assertEqual(service._uncertain_task_request, original)
                loaded_source, loaded = self.editor_call(service, "editor_load")
                self.assertEqual(loaded.task_result.snapshot_wire.hex(), witness["snapshot_hex"])
                self.assertEqual(self.revision(loaded_source, loaded), witness["revision"])
                self.assertIsNone(service._uncertain_task_request)
                self.assertEqual(service.poll()["state"], "READY")
                receipts = service._task_reconciliation_history
                self.assertEqual(receipts[-1], (original.original_message, loaded.original_response,
                                              "EXACT_EDITOR_CUSTODY_OBSERVED"))
                self.assertEqual(service.poll()["authority"], "CLOSED")
                self.stop(service); cells, history, _ = self.disk_observations(root)
                self.assertEqual(cells[0].value_wire, draft.snapshot_wire)
                self.assertIsNone(cells[2].value_wire)
                self.assertIn(bytes.fromhex(witness["snapshot_hex"]), history)


class QtEditorRecoveryTests(_EditorNativeHelpers):
    """Actual offscreen Qt documents over fresh native owned receivers."""
    @classmethod
    def setUpClass(cls):
        _ServiceTestCase.setUpClass.__func__(cls)
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        super().setUp()
        self.widgets = []

    def tearDown(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from shiboken6 import isValid
        for widget in self.widgets:
            if isValid(widget) and hasattr(widget, "poll_timer"):
                widget.poll_timer.stop()
        try:
            super().tearDown()
        finally:
            for widget in reversed(self.widgets):
                if isValid(widget): widget.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()

    def session(self, service, *, task_id=TASK):
        from ceta.application.task_operator import TaskOperatorSession
        result = TaskOperatorSession(service, PROJECT)
        result.poll()
        result.load(task_id)
        self.pump(result, lambda: result.created and result._pending is None)
        self.assertEqual(result.status, "READY")
        return result

    def view(self, session, parent=None):
        from ceta.desktop.meaning_view import MeaningView
        view = MeaningView(session, parent)
        self.widgets.append(view)
        view.poll_timer.stop(); view.show(); self.app.processEvents()
        return view

    def task_window(self, session):
        from ceta.desktop.task_view import TaskView
        view = TaskView(session)
        self.widgets.append(view)
        view.poll_timer.stop(); view.show(); self.app.processEvents()
        return view

    def pump(self, session, predicate, *, view=None):
        def observed():
            if view is None: session.poll()
            else: view._poll()
            self.app.processEvents()
            return predicate()
        return self.until(observed, explanation="actual editor session did not reach the asserted custody state")

    def native_idle_session(self, session):
        self.pump(session, lambda: session._pending is None and session._service._send_task is None)

    def fill_invalid(self, view, *, high_revision=False):
        from PySide6.QtGui import QTextCursor
        for index, name in enumerate(SOURCE_FIELDS):
            editor = view.editors[name]
            raw_text = name + "\u00a0Cafe\u0301\U0001f642\u2028soft\u2029paragraph\x00"
            if name == "scope": raw_text += "x" * 16385
            blocked = editor.blockSignals(True)
            try:
                editor.setPlainText(raw_text)
                if high_revision:
                    for _ in range(30):
                        cursor = QTextCursor(editor.document())
                        cursor.movePosition(QTextCursor.MoveOperation.End)
                        cursor.insertText("z"); cursor.deletePreviousChar()
                cursor = editor.textCursor()
                cursor.setPosition(index)
                # Cross the supplementary character using actual UTF-16 units.
                cursor.setPosition(min(22 + index, editor.document().characterCount() - 1),
                                   QTextCursor.MoveMode.KeepAnchor)
                editor.setTextCursor(cursor)
            finally:
                editor.blockSignals(blocked)
        view._edited("scope", view.editors["scope"])
        self.assertTrue(view.has_rejected_edits)
        self.assertFalse(view.propose_button.isEnabled())
        facts = {}
        for name, editor in view.editors.items():
            cursor = editor.textCursor(); native = editor.document()
            facts[name] = {"utf16le_hex": native.toRawText().encode("utf-16-le", errors="surrogatepass").hex(),
                "document_revision": native.revision(), "cursor_position": cursor.position(),
                "anchor_position": cursor.anchor()}
            for exact in ("\u00a0", "\u2028", "\u2029", "\U0001f642"):
                self.assertIn(exact, native.toRawText())
        return facts

    def assert_widget_documents(self, view, saved_documents):
        for name, document in saved_documents.items():
            editor = view.editors[name]; cursor = editor.textCursor()
            self.assertEqual(editor.document().toRawText().encode("utf-16-le", errors="surrogatepass").hex(),
                             document["utf16le_hex"], "Qt raw text differs for " + name)
            self.assertEqual((cursor.position(), cursor.anchor()),
                             (document["cursor_position"], document["anchor_position"]))

    def delete_qt(self, view):
        from PySide6.QtCore import QCoreApplication, QEvent
        from shiboken6 import isValid
        view.poll_timer.stop(); view.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.assertFalse(isValid(view), "the original Qt object was not actually deleted")

    def test_actual_qt_raw_custody_delete_restart_restore_new_document_then_durable_edit(self):
        service, root = self.empty_service(); original, basis = self.create_task(service)
        session = self.session(service); parent = self.task_window(session)
        view = self.view(session, parent)
        accepted = session.meaning_text
        facts = self.fill_invalid(view, high_revision=True)
        self.assertEqual(session.editor_recovery_status(), "QUEUED")
        self.assertIsNone(session.editor_recovery_snapshot())
        self.assertEqual(session.meaning_text, accepted)
        self.pump(session, lambda: session.editor_recovery_status() == "RETAINED"
            and session._pending is None, view=view)
        self.native_idle_session(session)
        stored = session.editor_recovery_snapshot(); first_wire = canonical_bytes(stored)
        for name, expected in facts.items():
            self.assertEqual({key: stored["payload"]["documents"][name][key] for key in expected}, expected)
        self.assertEqual(stored["payload"]["basis_revision"], basis)
        self.assertGreater(stored["payload"]["documents"]["scope"]["document_revision"], 30)
        self.assertFalse(view.return_authorized)
        # Actual Qt deletion is an external lifetime observation, never consent.
        self.delete_qt(view)
        self.assertEqual(session.editor_recovery_status(), "RETAINED")
        self.assertEqual(canonical_bytes(session.editor_recovery_snapshot()), first_wire)
        self.delete_qt(parent)
        self.stop(service); before = self.disk_observations(root)
        self.assertEqual(before[0][0].value_wire, original.snapshot_wire)
        self.assertIsNone(before[0][2].value_wire)
        del view, parent, session
        gc.collect()
        restarted, _ = self.empty_service(root=root)
        new_session = self.session(restarted)
        restored = self.view(new_session)
        self.assertIsNone(new_session.editor_recovery_snapshot())
        self.assertTrue(all(editor.document().toRawText() == "" for editor in restored.editors.values()))
        restored._load_editor()  # explicit load through the actual caller
        self.pump(new_session, lambda: restored._restored_source_facts is not None
            and new_session._pending is None, view=restored)
        self.assertEqual(restored._restored_source_facts, stored["payload"])
        self.assert_widget_documents(restored, stored["payload"]["documents"])
        self.assertEqual(new_session.meaning_text, {name: "" for name in SOURCE_FIELDS})
        self.assertIsNone(new_session.meaning_proposal)
        self.assertFalse(restored.propose_button.isEnabled())
        self.native_idle_session(new_session)
        from PySide6.QtGui import QTextCursor
        editor = restored.editors["scope"]
        cursor = editor.textCursor(); cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.End); cursor.insertText("NEW")
        self.pump(new_session, lambda: new_session.editor_recovery_status() == "RETAINED"
            and new_session.editor_recovery_snapshot()["generation"] > stored["generation"]
            and new_session._pending is None, view=restored)
        second = new_session.editor_recovery_snapshot()
        old_doc, new_doc = stored["payload"]["documents"]["scope"], second["payload"]["documents"]["scope"]
        self.assertNotEqual(new_doc["document_id"], old_doc["document_id"])
        self.assertLess(new_doc["document_revision"], old_doc["document_revision"])
        self.assertGreater(second["payload"]["widget_revision"], stored["payload"]["widget_revision"])
        self.assertTrue(utf16_text_value(new_doc["utf16le_hex"]).endswith("NEW"))
        self.assertEqual(new_session.meaning_text, {name: "" for name in SOURCE_FIELDS})
        self.stop(restarted); cells, history, _ = self.disk_observations(root)
        self.assertEqual(cells[0].value_wire, original.snapshot_wire)
        self.assertIsNone(cells[2].value_wire)
        self.assertIn(first_wire, history)
        self.assertIn(canonical_bytes(second), history)

    def test_actual_taskview_deleted_dialog_retains_pending_capture_and_explicit_recovery(self):
        from ceta.desktop.meaning_view import MeaningView
        from PySide6.QtWidgets import QDialog
        from shiboken6 import isValid
        service, _ = self.empty_service(); self.create_task(service)
        session = self.session(service); task_window = self.task_window(session)
        seen = []
        def controlled_modal_return(dialog):
            # Controlled modal return lets the real caller own a rejected Qt
            # document without entering an unbounded nested event loop.
            dialog.poll_timer.stop(); self.widgets.append(dialog)
            self.fill_invalid(dialog); seen.append(dialog)
            return int(QDialog.DialogCode.Rejected)
        with patch.object(MeaningView, "exec", controlled_modal_return):
            task_window._meaning()
        original, = seen
        original.poll_timer.stop()
        local = session.editor_local_payload()
        self.assertIsNotNone(local)
        self.assertIn(TASK, task_window._meaning_views)
        session.poll()  # reserve actual native retention, without an ACK claim
        self.assertEqual(session.editor_recovery_status(), "SAVING")
        pending = session._pending
        self.delete_qt(original)
        self.assertNotIn(TASK, task_window._meaning_views)
        self.assertIs(session._pending, pending)
        self.assertEqual(session.editor_local_payload(), local)
        task_window._refresh()
        self.assertIn(TASK, [task_window.meaning_recovery_picker.itemText(i)
                            for i in range(task_window.meaning_recovery_picker.count())])
        task_window.meaning_recovery_picker.setCurrentText(TASK)
        task_window._recover_meaning()  # actual caller constructs a fresh dialog
        recovered = task_window._meaning_views[TASK]
        self.widgets.append(recovered); recovered.poll_timer.stop()
        self.assertTrue(isValid(recovered)); self.assertIsNot(recovered, original)
        self.assert_widget_documents(recovered, decode_editor_payload(local)["documents"])
        self.assertFalse(recovered.return_authorized)
        self.pump(session, lambda: session.editor_recovery_status() == "RETAINED"
            and session._pending is None, view=recovered)
        self.assertEqual(session.meaning_text, {name: "" for name in SOURCE_FIELDS})
        self.assertEqual(session.editor_recovery_snapshot()["state"], "RETAINED")

    def test_actual_qt_discard_requires_explicit_consent_and_ack_before_return(self):
        from PySide6.QtWidgets import QMessageBox
        service, root = self.empty_service(); original, _ = self.create_task(service)
        session = self.session(service); view = self.view(session)
        self.fill_invalid(view)
        self.pump(session, lambda: session.editor_recovery_status() == "RETAINED"
            and session._pending is None, view=view)
        self.native_idle_session(session)
        kept = canonical_bytes(session.editor_recovery_snapshot())
        documents_before = {name: editor.document().toRawText() for name, editor in view.editors.items()}
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            view.reject()
        self.assertFalse(view.return_authorized)
        self.assertEqual(session.editor_recovery_snapshot()["state"], "RETAINED")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            view.reject()
        self.assertEqual(session.editor_recovery_status(), "DISCARDING")
        self.assertFalse(view.return_authorized)
        self.assertEqual({name: editor.document().toRawText() for name, editor in view.editors.items()}, documents_before)
        # Even another Return cannot dispose while a bound ACK is pending.
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            view.reject()
        self.assertFalse(view.return_authorized)
        self.pump(session, lambda: session.editor_recovery_status() == "DISCARDED"
            and session._pending is None, view=view)
        tombstone = canonical_bytes(session.editor_recovery_snapshot())
        self.assertEqual(decode_editor_snapshot(tombstone)["payload"], decode_editor_snapshot(kept)["payload"])
        view.reject(); self.assertTrue(view.return_authorized)
        self.stop(service); cells, history, _ = self.disk_observations(root)
        self.assertEqual(cells[0].value_wire, original.snapshot_wire)
        self.assertIsNone(cells[2].value_wire)
        self.assertIn(kept, history); self.assertIn(tombstone, history)

    def test_actual_qt_new_edit_during_discard_keeps_conflict_documents_after_tombstone_ack(self):
        from PySide6.QtGui import QTextCursor
        from PySide6.QtWidgets import QMessageBox
        service, _ = self.empty_service(); self.create_task(service)
        session = self.session(service); view = self.view(session)
        self.fill_invalid(view)
        self.pump(session, lambda: session.editor_recovery_status() == "RETAINED"
            and session._pending is None, view=view)
        self.native_idle_session(session)
        prior = session.editor_local_payload()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            view._discard_editor()
        self.assertEqual(session.editor_recovery_status(), "DISCARDING")
        cursor = view.editors["scope"].textCursor(); cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.End); cursor.insertText("NEWER THAN CONSENT")
        newer = session.editor_local_payload(); self.assertNotEqual(newer, prior)
        self.pump(session, lambda: session._pending is None
            and session.editor_recovery_status() == "CONFLICT", view=view)
        self.assertEqual(session.editor_recovery_snapshot()["state"], "DISCARDED")
        self.assertEqual(session.editor_local_payload(), newer)
        self.assertTrue(view.has_rejected_edits); self.assertFalse(view.return_authorized)
        self.assertTrue(view.editors["scope"].document().toRawText().endswith("NEWER THAN CONSENT"))
        self.assertEqual(session.meaning_text, {name: "" for name in SOURCE_FIELDS})

    def test_actual_qt_stop_keeps_unsubmitted_recovery_distinct_from_durable_custody(self):
        from PySide6.QtWidgets import QMessageBox
        service, root = self.empty_service(); self.create_task(service)
        session = self.session(service); view = self.view(session)
        facts = self.fill_invalid(view)
        self.assertEqual(session.editor_recovery_status(), "QUEUED")
        self.assertIsNone(session.editor_recovery_snapshot())
        session.stop()
        self.pump(session, lambda: session.status == "STOPPED", view=view)
        self.assertEqual(session.editor_recovery_status(), "QUEUED")
        self.assertIsNone(session.editor_recovery_snapshot())
        self.assertEqual(decode_editor_payload(session.editor_local_payload())["documents"]["scope"]["utf16le_hex"],
                         facts["scope"]["utf16le_hex"])
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            view.reject()
        self.assertFalse(view.return_authorized)
        self.assertTrue(view.has_rejected_edits)
        cells, _, _ = self.disk_observations(root)
        self.assertIsNone(cells[3].value_wire, "an unsubmitted queue was misreported as durable retention")

    def test_actual_qt_oversize_lone_surrogate_survives_deletion_service_restart_and_fresh_taskview_discovery(self):
        service, root = self.empty_service(); self.create_task(service)
        session = self.session(service); task_window = self.task_window(session)
        view = self.view(session, task_window)
        oversized = "NO consent\u00a0\U0001f642\u2028\u2029" + "x" * 65537 + "\ud800"
        view.editors["scope"].setPlainText(oversized)
        actual = view.editors["scope"].document().toRawText().encode("utf-16-le", errors="surrogatepass")
        self.assertGreater(len(actual), 131072)
        self.pump(session, lambda: session.editor_recovery_status() == "RETAINED"
            and session._pending is None, view=view)
        stored = session.editor_recovery_snapshot()
        self.assertEqual(stored["payload"]["profile"], EDITOR_REFERENCE_PROFILE)
        self.assertNotIn("utf16le_hex", stored["payload"]["documents"]["scope"])
        self.assertEqual(session.meaning_text, {name: "" for name in SOURCE_FIELDS})
        self.delete_qt(view)
        self.stop(service)
        cells, _, _ = self.disk_observations(root)
        self.assertIsNone(cells[2].value_wire, "raw editor bytes must not enter meaning state")
        self.assertIsNotNone(cells[3].value_wire)

        restarted, _ = self.empty_service(root=root)
        fresh = self.session(restarted)
        fresh_window = self.task_window(fresh)
        # TaskView performs only catalog and metadata reads until the user
        # selects recovery; no private direct recovery load is needed.
        self.pump(fresh, lambda: TASK in fresh.editor_recovery_task_ids
            and fresh._pending is None, view=fresh_window)
        self.assertEqual(fresh_window.meaning_recovery_picker.findText(TASK) >= 0, True)
        fresh_window.meaning_recovery_picker.setCurrentText(TASK)
        fresh_window._recover_meaning()
        recovered = fresh_window._meaning_views[TASK]
        self.widgets.append(recovered)
        self.pump(fresh, lambda: recovered._restored_source_facts is not None
            and fresh._pending is None, view=recovered)
        self.assertEqual(recovered.editors["scope"].document().toRawText().encode("utf-16-le", errors="surrogatepass"),
                         actual)
        self.assertEqual(fresh.editor_recovery_snapshot()["state"], "RETAINED")
        self.assertEqual(fresh.meaning_text, {name: "" for name in SOURCE_FIELDS})

    def test_actual_qt_valid_unsaved_form_survives_delete_restart_without_meaning_acceptance(self):
        service, root = self.empty_service(); self.create_task(service)
        session = self.session(service); task_window = self.task_window(session)
        view = self.view(session, task_window)
        values = {name: "Valid unsaved " + name + ": Cafe\u0301; review before proposal." for name in SOURCE_FIELDS}
        for name, value in values.items():
            editor = view.editors[name]
            blocked = editor.blockSignals(True)
            try:
                editor.setPlainText(value)
            finally:
                editor.blockSignals(blocked)
        view._edited("scope", view.editors["scope"])
        expected = {name: editor.document().toRawText().encode("utf-16-le", errors="surrogatepass")
                    for name, editor in view.editors.items()}
        self.assertFalse(view.has_rejected_edits)
        self.assertEqual(session.meaning_text, values)
        self.pump(session, lambda: session.editor_recovery_status() == "RETAINED"
            and session._pending is None, view=view)
        retained = session.editor_recovery_snapshot()
        self.assertEqual(retained["state"], "RETAINED")
        self.assertEqual({name: bytes.fromhex(item["utf16le_hex"])
                          for name, item in retained["payload"]["documents"].items()}, expected)
        self.delete_qt(view); self.delete_qt(task_window); self.stop(service)
        cells, _, _ = self.disk_observations(root)
        self.assertIsNone(cells[2].value_wire, "valid unsaved raw text entered meaning state")
        self.assertIsNotNone(cells[3].value_wire)

        restarted, _ = self.empty_service(root=root)
        fresh = self.session(restarted); fresh_window = self.task_window(fresh)
        self.pump(fresh, lambda: TASK in fresh.editor_recovery_task_ids
            and fresh._pending is None, view=fresh_window)
        self.assertGreaterEqual(fresh_window.meaning_recovery_picker.findText(TASK), 0)
        fresh_window.meaning_recovery_picker.setCurrentText(TASK)
        fresh_window._recover_meaning()
        recovered = fresh_window._meaning_views[TASK]
        self.widgets.append(recovered)
        self.pump(fresh, lambda: recovered._restored_source_facts is not None
            and fresh._pending is None, view=recovered)
        self.assertEqual({name: editor.document().toRawText().encode("utf-16-le", errors="surrogatepass")
                          for name, editor in recovered.editors.items()}, expected)
        self.assertEqual(fresh.meaning_text, {name: "" for name in SOURCE_FIELDS})
        self.assertIsNone(fresh.meaning_proposal)
        self.assertFalse(recovered.propose_button.isEnabled())

    def test_controlled_native_discard_reply_loss_keeps_actual_dialog_until_exact_load_reconciliation(self):
        from PySide6.QtWidgets import QMessageBox
        service, root = self.empty_service(); original, basis = self.create_task(service)
        _, kept = self.editor_call(service, "editor_retain", wire=payload(basis, docs=documents(lone_surrogate=False)))
        self.stop(service)
        stimulus = {"development_root": str(ROOT.resolve(strict=True)), "command_id": None,
                    "operation": "task.editor_discard", "scope_id": PROJECT, "task_id": TASK}
        wrapper = root / "editor_post_commit_reply_loss.py"
        with wrapper.open("xb") as stream: stream.write(POST_COMMIT_WRAPPER.encode("utf8"))
        with (root / "editor_reply_stimulus.json").open("xb") as stream: stream.write(canonical_bytes(stimulus))
        service, _ = self.empty_service(root=root, wrapper=wrapper)
        session = self.session(service); view = self.view(session)
        view._load_editor()
        self.pump(session, lambda: view._restored_source_facts is not None and session._pending is None, view=view)
        self.native_idle_session(session)
        full = {name: editor.document().toRawText() for name, editor in view.editors.items()}
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes): view._discard_editor()
        self.pump(session, lambda: session.editor_recovery_status() == "UNCERTAIN" and session._pending is None, view=view)
        self.assertEqual(session.status, "RECOVERING")
        self.assertFalse(view.return_authorized)
        self.assertEqual({name: editor.document().toRawText() for name, editor in view.editors.items()}, full)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes): view.reject()
        self.assertFalse(view.return_authorized)
        witness = strict_loads((root / "editor_reply_witness.json").read_bytes())
        request = decode_message(bytes.fromhex(witness["request_hex"]), self.codec)
        self.assertEqual(service._uncertain_task_request, request)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes): view._load_editor()
        self.pump(session, lambda: session.editor_recovery_status() == "DISCARDED" and session._pending is None, view=view)
        self.assertEqual(canonical_bytes(session.editor_recovery_snapshot()).hex(), witness["snapshot_hex"])
        self.assertIsNone(service._uncertain_task_request)
        self.assertEqual(session.status, "READY")
        view.reject(); self.assertTrue(view.return_authorized)
        self.stop(service); cells, history, _ = self.disk_observations(root)
        self.assertEqual(cells[0].value_wire, original.snapshot_wire)
        self.assertIsNone(cells[2].value_wire)
        self.assertIn(kept.task_result.snapshot_wire, history)
        self.assertIn(bytes.fromhex(witness["snapshot_hex"]), history)


if __name__ == "__main__":
    unittest.main()





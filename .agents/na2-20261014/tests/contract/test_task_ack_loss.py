"""Native task COMMIT followed by one deliberately suppressed server reply.

These disposable Windows fixtures use the production owned client, service main,
native authentication, task handler and SQLite commit. A test-owned child wrapper
delegates the original commit and encoder, then raises before response WriteFile
only after witnessing the exact targeted successful commit. This is controlled
native reply-loss evidence, not a spontaneous OS failure, power-loss qualification,
historical uncertain-attempt import or cross-session kernel/effect authority.
No positive owner, normal profile, model, installed service or effect is selected.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from fixture_paths import native_fixture_path
import sys
import time
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
INSTALLATION = "installation:native-task-ack-fixture"
PROJECT = "project:native-task-ack-fixture"
SCOPES = (INSTALLATION, PROJECT)
PRINCIPAL = "operator:native-task-ack-fixture"
TABLE_ORDER = {
    "history_meta": "id",
    "history_scopes": "scope_id",
    "history_events": "scope_id,sequence",
    "store_commits": "sequence",
    "store_changes": "commit_sequence,change_index",
    "store_cells": "collection,scope_id,record_id",
}
TITLE = "Cafe\u0301 exact title"
INSTRUCTION = "NO. Do not delete any repository.\r\nCafe\u0301\tkeep \x00 the exclusions.\r\n"
DRAFT = "Draft e\u0301\tline\r\n\x00NO consent\r\n"

# This constant is parsed separately during syntax validation. It is materialized
# exclusively inside the fresh disposable root at test execution, never in src.
FIXTURE_WRAPPER = r'''
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "stimulus.json").read_bytes())
DEVELOPMENT = Path(MANIFEST["development_root"])
sys.path.insert(0, str(DEVELOPMENT / "src"))

from ceta.composition import service_process
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.kernel_transactions import require, task_key, task_wire
from ceta.contracts.store_transactions import StoreCommit
from ceta.contracts.task_drafts import TaskResult, draft_key, decode_snapshot, validate_result
from ceta.contracts.wire import ContractError, canonical_bytes
from ceta.store.journal import SqliteJournal
from ceta.store.sqlite_runtime import load_sqlite

require(DEVELOPMENT.resolve(strict=True) == service_process.ROOT.resolve(strict=True),
        "FIXTURE_DEVELOPMENT_ROOT_BINDING")
require(HERE.is_relative_to(DEVELOPMENT / ".agents/fixtures"),
        "FIXTURE_DISPOSABLE_ROOT_REQUIRED")
require(MANIFEST["schema"] == "ceta-native-task-ack-stimulus-v1",
        "FIXTURE_STIMULUS_SCHEMA")

TABLE_ORDER = {
    "history_meta": "id",
    "history_scopes": "scope_id",
    "history_events": "scope_id,sequence",
    "store_commits": "sequence",
    "store_changes": "commit_sequence,change_index",
    "store_cells": "collection,scope_id,record_id",
}

def sql_value(value):
    if type(value) is bytes:
        return {"blob_hex": value.hex()}
    require(value is None or type(value) in (str, int), "FIXTURE_SQL_VALUE")
    return value

def read_only_cut(path):
    sqlite = load_sqlite()
    connection = sqlite.connect(path.as_uri() + "?mode=ro", uri=True,
                                isolation_level=None, timeout=5)
    try:
        connection.execute("PRAGMA query_only=ON")
        require(connection.execute("PRAGMA query_only").fetchone() == (1,),
                "FIXTURE_QUERY_ONLY_REQUIRED")
        connection.execute("BEGIN")
        require(connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                "FIXTURE_JOURNAL_INTEGRITY")
        tables = {}
        for name, order in TABLE_ORDER.items():
            cursor = connection.execute('SELECT * FROM "' + name + '" ORDER BY ' + order)
            columns = tuple(item[0] for item in cursor.description)
            tables[name] = [{column: sql_value(value)
                            for column, value in zip(columns, row)}
                           for row in cursor.fetchall()]
        commits = tables["store_commits"]
        require([row["sequence"] for row in commits] == list(range(len(commits))),
                "FIXTURE_COMMIT_SEQUENCE")
        store_position = {"next_commit": len(commits),
                          "head": None if not commits else commits[-1]["head"]}
        cut = {"schema": "ceta-native-task-ack-cut-v1", "query_only": True,
               "tables": tables, "positions": {"store": store_position,
               "scopes": tables["history_scopes"]}}
        connection.execute("COMMIT")
        return cut
    finally:
        connection.close()

def publish_closed_witness(value):
    final = HERE / "post_commit_witness.json"
    pending = HERE / "post_commit_witness.pending"
    wire = canonical_bytes(value)
    with pending.open("xb") as stream:
        require(stream.write(wire) == len(wire), "FIXTURE_WITNESS_SHORT_WRITE")
        stream.flush()
        os.fsync(stream.fileno())
    # Windows rename rejects an existing final target. No old output is replaced.
    os.rename(pending, final)

original_factory = service_process.compose_duplex_kernel_service

def instrumented_factory(store, codec, installation, registry, pipe):
    require(type(store) is SqliteJournal, "FIXTURE_REAL_JOURNAL_REQUIRED")
    receiver = original_factory(store, codec, installation, registry, pipe)
    original_commit = store.commit
    original_encoder = receiver._response_encoder
    observed_commits = {}
    suppressed = False

    def observe_commit(*args, **kwargs):
        # The original guard, expectations, entries and changes pass unchanged.
        committed = original_commit(*args, **kwargs)
        require(type(committed) is StoreCommit and not store._connection.in_transaction,
                "FIXTURE_REAL_COMMIT_RETURN_REQUIRED")
        entries = kwargs.get("entries") if len(args) < 2 else args[1]
        for entry in entries:
            event_id = codec.decode(entry.event_wire).record_id
            require(event_id not in observed_commits, "FIXTURE_DUPLICATE_COMMIT_EVENT")
            observed_commits[event_id] = (committed, entry)
        return committed

    def suppress_target_reply(message, result, actual_codec):
        nonlocal suppressed
        response_wire = original_encoder(message, result, actual_codec)
        if message.record.record_id != MANIFEST["command_id"]:
            return response_wire
        require(not suppressed, "FIXTURE_REPLY_SUPPRESSION_REPEATED")
        require(message.operation == MANIFEST["operation"]
                and message.scope_id == MANIFEST["scope_id"]
                and message.record.as_dict()["task_id"] == MANIFEST["task_id"],
                "FIXTURE_TARGET_REQUEST_BINDING")
        require(type(result) is TaskResult and result.kind == "TASK_SNAPSHOT",
                "FIXTURE_SUCCESSFUL_TASK_WRITE_REQUIRED")
        revision = validate_result(result, message.record, message.operation)
        snapshot = decode_snapshot(result.snapshot_wire)
        require(snapshot["event_id"] in observed_commits, "FIXTURE_TARGET_COMMIT_NOT_OBSERVED")
        committed, entry = observed_commits[snapshot["event_id"]]
        selected = {cell.key: cell for cell in committed.cells}
        draft = selected.get(draft_key(message.scope_id, snapshot["task_id"]))
        kernel_task = selected.get(task_key(message.scope_id, snapshot["task_id"]))
        require(draft is not None and kernel_task is not None
                and draft.value_wire == result.snapshot_wire
                and draft.generation == result.generation and draft.revision == revision
                and kernel_task.value_wire == task_wire(message.scope_id,
                    snapshot["task_id"], snapshot["objective_revision"]),
                "FIXTURE_COMMIT_SNAPSHOT_BINDING")
        contract = EventContract(codec)
        point = StreamPosition(snapshot["scope_id"], snapshot["event_sequence"],
                               snapshot["previous_head"])
        event = contract.require_successor(entry.event_wire, point).record.as_dict()
        payload = contract.require_payload(entry.event_wire, entry.payload_wire).as_dict()
        expected_type = "task.created" if message.operation == "task.create" else "task.draft.saved"
        require(event["record_id"] == snapshot["event_id"]
                and event["event_type"] == expected_type
                and event["causation_ref"] == message.record.record_id
                and event["actor_session"] == message.sender_session
                and payload["causation_ref"] == message.record.record_id
                and payload["observer_session"] == message.sender_session,
                "FIXTURE_COMMIT_EVENT_BINDING")
        cut = read_only_cut(store.path)
        current = store.store_position()
        require(cut["positions"]["store"] == {
                    "next_commit": committed.position.next_commit,
                    "head": committed.position.head}
                and current == committed.position and not store._connection.in_transaction,
                "FIXTURE_COMMITTED_READ_ONLY_VISIBILITY")
        witness = {
            "schema": "ceta-native-task-ack-witness-v1",
            "phase": "AFTER_REAL_COMMIT_BEFORE_SERVER_RESPONSE_WRITE",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "wall_clock_qualification": "UNQUALIFIED_FIXTURE_OBSERVATION",
            "service_pid": os.getpid(), "receiver_generation": receiver.receiver_generation,
            "operation": message.operation, "scope_id": message.scope_id,
            "task_id": snapshot["task_id"], "sender_session": message.sender_session,
            "message_id": message.message_id,
            "correlation_ref": json.loads(message.original_message)["correlation_ref"],
            "request_sha256": hashlib.sha256(message.original_message).hexdigest(),
            "command_id": message.record.record_id,
            "command_commitment": message.record.commitment,
            "command_original_hex": message.record.original_wire.hex(),
            "snapshot_hex": result.snapshot_wire.hex(),
            "snapshot_sha256": hashlib.sha256(result.snapshot_wire).hexdigest(),
            "generation": result.generation, "revision": revision,
            "event_hex": entry.event_wire.hex(), "payload_hex": entry.payload_wire.hex(),
            "response_hex": response_wire.hex(),
            "response_sha256": hashlib.sha256(response_wire).hexdigest(),
            "commit_position": {"next_commit": committed.position.next_commit,
                                "head": committed.position.head},
            "commit_history": [
                {"before": {"scope_id": item.before.scope_id,
                            "next_sequence": item.before.next_sequence, "head": item.before.head},
                 "after": {"scope_id": item.after.scope_id,
                           "next_sequence": item.after.next_sequence, "head": item.after.head},
                 "event_ids": list(item.event_ids)} for item in committed.history],
            "commit_cells": [
                {"key": cell.key.as_dict(), "generation": cell.generation,
                 "value_hex": None if cell.value_wire is None else cell.value_wire.hex(),
                 "revision": cell.revision} for cell in committed.cells],
            "durable_cut": cut, "suppression_count": 1,
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "manifest_sha256": hashlib.sha256((HERE / "stimulus.json").read_bytes()).hexdigest(),
        }
        publish_closed_witness(witness)
        suppressed = True
        # The server finally invalidates/disconnects this real request context.
        # Neither authentication nor authorization is changed by this stimulus.
        raise ContractError("FIXTURE_POST_COMMIT_REPLY_SUPPRESSED")

    store.commit = observe_commit
    receiver._response_encoder = suppress_target_reply
    return receiver

service_process.compose_duplex_kernel_service = instrumented_factory
raise SystemExit(service_process.main())
'''


class NativeTaskAckLossTests(unittest.TestCase):
    """Two new native definitions; no imported/inherited test methods."""

    @classmethod
    def setUpClass(cls):
        if sys.platform != "win32" or sys.version_info[:2] != (3, 12):
            raise AssertionError("Requires the declared Windows Python3.12 interpreter")
        sys.path.insert(0, str(ROOT / "src"))
        from ceta.contracts.wire import RecordCodec, strict_loads
        cls.codec = RecordCodec(strict_loads(
            (ROOT / "contracts/schemas/records.schema.json").read_bytes()))

    def setUp(self):
        self.services = []

    def tearDown(self):
        failures = []
        for service in reversed(self.services):
            stop_observed = False
            try:
                self._stop(service)
                stop_observed = True
            except BaseException as error:
                failures.append(repr(error))
            try:
                state = service.snapshot()
                self._preserve(service._root,
                    "fixture_cleanup_" + service._controller.name + ".json", {
                        "schema": "ceta-native-task-ack-cleanup-v1",
                        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                        "stop_observed": stop_observed, "state": state["state"],
                        "authority": state["authority"], "generation": state["generation"],
                        "spool": str(service._spool),
                        "client_diagnostics_hex": None if service._client is None
                            else service._client.diagnostic_bytes.hex(),
                        "service_diagnostics_hex": None if service._service is None
                            else service._service.diagnostic_bytes.hex(),
                    })
            except BaseException as error:
                failures.append("fixture cleanup evidence unavailable: " + repr(error))
        if failures:
            self.fail("exact owned fixture cleanup unresolved: " + repr(failures))

    def _until(self, predicate, explanation, seconds=25):
        deadline = time.monotonic() + seconds
        while True:
            observed = predicate()
            if observed:
                return observed
            if time.monotonic() >= deadline:
                self.fail(explanation)
            time.sleep(0.005)

    def _directory(self):
        base = ROOT / ".agents/fixtures/task-ack-loss-29"
        for path in (base, *base.parents):
            self.assertFalse(path.is_symlink() or path.is_junction(),
                             "fixture path crosses a linked directory")
        root = base / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=False)
        self.assertTrue(root.resolve(strict=True).is_relative_to(
            ROOT.resolve(strict=True) / ".agents/fixtures"))
        return root

    def _preserve(self, root, role, value):
        path = root / role
        wire = json.dumps(value, ensure_ascii=True, sort_keys=True,
                          indent=2).encode("utf8") + b"\n"
        with path.open("xb") as stream:
            self.assertEqual(stream.write(wire), len(wire))
        return path

    def _service(self, root, *, create):
        from ceta.composition.owned_service import OwnedService
        service = OwnedService(root, self.codec, INSTALLATION, SCOPES, create=create,
                               principal_id=PRINCIPAL, call_seconds=8.0)
        self.services.append(service)
        return service

    def _ready(self, service):
        service.start()

        def observed():
            value = service.poll()
            self.assertNotIn(value["state"], {"RECOVERING", "STOPPING", "STOPPED"},
                             "native startup failed: " + value["detail"])
            with service._lock:
                workers_retired = not service._workers
            return value if value["state"] == "READY" and workers_retired else None

        value = self._until(observed, "real selected native service never reached READY")
        self.assertEqual(value["authority"], "CLOSED")
        self.assertIsNone(service._client.process.poll())
        self.assertIsNone(service._service.process.poll())
        return value

    def _start_fault_service(self, root, *, kind, command_id, task_id):
        wrapper = root / "post_commit_reply_loss.py"
        with wrapper.open("xb") as stream:
            raw = FIXTURE_WRAPPER.encode("utf8")
            self.assertEqual(stream.write(raw), len(raw))
        manifest = {
            "schema": "ceta-native-task-ack-stimulus-v1",
            "development_root": str(ROOT.resolve(strict=True)),
            "operation": "task." + kind, "scope_id": PROJECT,
            "command_id": command_id, "task_id": task_id,
        }
        self._preserve(root, "stimulus.json", manifest)
        service = self._service(root, create=True)
        original = service._launch_owned
        changed_launches = []

        def launch(slot, arguments):
            if slot == "_service":
                self.assertEqual(len(arguments), 6)
                self.assertEqual(arguments[:4], ("-I", "-B", "-X", "utf8"))
                self.assertEqual(Path(arguments[4]).resolve(strict=True),
                    (ROOT / "src/ceta/composition/service_process.py").resolve(strict=True))
                modified = (*arguments[:4], str(wrapper), arguments[5])
                changed_launches.append({"slot": slot, "original_arguments": list(arguments),
                                         "fixture_arguments": list(modified)})
                return original(slot, modified)
            return original(slot, arguments)

        with patch.object(service, "_launch_owned", side_effect=launch):
            ready = self._ready(service)
        self.assertEqual(len(changed_launches), 1)
        self._preserve(root, "launch_observation.json", {
            "schema": "ceta-native-task-ack-launch-v1", "authority": ready["authority"],
            "generation": ready["generation"], "launches": changed_launches,
            "client_pid": service._client.process.pid,
            "client_creation_time": service._client.process.creation_time,
            "client_image_sha256": service._client.process.image_sha256,
            "service_pid": service._service.process.pid,
            "service_creation_time": service._service.process.creation_time,
            "service_image_sha256": service._service.process.image_sha256,
            "wrapper_sha256": hashlib.sha256(wrapper.read_bytes()).hexdigest(),
            "manifest_sha256": hashlib.sha256((root / "stimulus.json").read_bytes()).hexdigest(),
        })
        return service

    def _idle(self, service):
        return self._until(
            lambda: (service.poll()["state"] in {"READY", "RECOVERING"}
                     and service._pending is None and service._send_task is None),
            "previous request/send worker was not observed retired")

    def _command(self, kind, *, command_id=None, pretty=False, **values):
        from ceta.contracts.task_drafts import command_wire
        wire = command_wire(kind, PROJECT, command_id or "command:" + uuid.uuid4().hex,
                            **values)
        if pretty:
            altered = json.dumps(json.loads(wire), indent=3).encode("utf8")
            self.assertNotEqual(altered, wire)
            wire = altered
        return wire

    def _call(self, service, kind, **values):
        self._idle(service)
        wire = self._command(kind, **values)
        attempt = service.begin_call(wire, "task." + kind)

        def observed():
            value = service.poll()
            call = value["call"]
            return call if (call is not None and call["attempt"] == attempt
                            and service._pending is None and service._send_task is None) else None

        call = self._until(observed, "exact native query/write result was not observed")
        self.assertIn("response", call, "native transport uncertainty is not a task result")
        self.assertEqual(service.snapshot()["authority"], "CLOSED")
        return attempt, call["response"]

    def _lost_call(self, service, root, kind, wire):
        from ceta.contracts.local_ipc import decode_message
        from ceta.contracts.local_results import decode_response
        self._idle(service)
        attempt = service.begin_call(wire, "task." + kind)
        captured = service._uncertain_task_request
        self.assertIsNotNone(captured)
        self.assertEqual(captured.record.original_wire, wire)

        def observed():
            value = service.poll()
            call = value["call"]
            return call if (value["state"] == "RECOVERING" and call is not None
                            and call["attempt"] == attempt
                            and call["kind"] == "TRANSPORT_UNCERTAIN"
                            and service._pending is None and service._send_task is None) else None

        call = self._until(observed, "actual native client did not report the lost target reply")
        # This field comes from call_uncertain; a local worker/deadline fallback
        # alone is insufficient to establish the actual client failure path.
        self.assertIn("error_code", call)
        self.assertIsInstance(call["error_code"], str)
        self.assertNotIn("response", call)
        self.assertEqual(service.snapshot()["authority"], "CLOSED")
        self.assertIsNone(service._client.process.poll())
        self.assertIsNone(service._service.process.poll())
        self.assertEqual(service._uncertain_task_request, captured)
        request_path = service._spool / (attempt + ".request.json")
        self.assertEqual(native_fixture_path(request_path).read_bytes(), captured.original_message)
        self.assertEqual(decode_message(native_fixture_path(request_path).read_bytes(), self.codec), captured)
        self.assertFalse((native_fixture_path(service._spool / (attempt + ".response.json"))).exists())
        marker = root / "post_commit_witness.json"
        self._until(lambda: marker.is_file(), "closed post-COMMIT witness was not published")
        self.assertFalse((root / "post_commit_witness.pending").exists())
        witness = json.loads(marker.read_bytes())
        self.assertEqual(witness["schema"], "ceta-native-task-ack-witness-v1")
        self.assertEqual(witness["phase"], "AFTER_REAL_COMMIT_BEFORE_SERVER_RESPONSE_WRITE")
        self.assertEqual(witness["suppression_count"], 1)
        self.assertEqual(witness["service_pid"], service._service.process.pid)
        self.assertEqual(witness["receiver_generation"], service.generation)
        self.assertEqual((witness["operation"], witness["scope_id"], witness["task_id"]),
                         (captured.operation, captured.scope_id,
                          captured.record.as_dict()["task_id"]))
        self.assertEqual((witness["command_id"], witness["command_commitment"]),
                         (captured.record.record_id, captured.record.commitment))
        self.assertEqual(witness["command_original_hex"], wire.hex())
        self.assertEqual((witness["message_id"], witness["correlation_ref"]),
                         (captured.message_id, json.loads(captured.original_message)["correlation_ref"]))
        self.assertEqual(witness["sender_session"], captured.sender_session)
        self.assertEqual(witness["request_sha256"],
                         hashlib.sha256(captured.original_message).hexdigest())
        self.assertEqual(witness["wrapper_sha256"],
                         hashlib.sha256((root / "post_commit_reply_loss.py").read_bytes()).hexdigest())
        self.assertEqual(witness["manifest_sha256"],
                         hashlib.sha256((root / "stimulus.json").read_bytes()).hexdigest())
        prepared_reply = bytes.fromhex(witness["response_hex"])
        self.assertEqual(witness["response_sha256"], hashlib.sha256(prepared_reply).hexdigest())
        suppressed_result = decode_response(prepared_reply, captured, self.codec)
        self.assertEqual(suppressed_result.kind, "TASK_SNAPSHOT")
        self.assertEqual(suppressed_result.task_result.snapshot_wire.hex(), witness["snapshot_hex"])
        self.assertEqual(suppressed_result.task_result.generation, witness["generation"])
        self._preserve(root, "uncertain_attempt_observation.json", {
            "schema": "ceta-native-task-ack-uncertainty-v1",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "attempt": attempt, "request_path": str(request_path),
            "request_sha256": hashlib.sha256(native_fixture_path(request_path).read_bytes()).hexdigest(),
            "client_error_code": call["error_code"], "state": service.state,
            "response_file_present": False, "witness_path": str(marker),
        })
        return attempt, captured, witness, suppressed_result

    def _read_only_cut(self, root):
        from ceta.store.sqlite_runtime import load_sqlite
        sqlite = load_sqlite()
        connection = sqlite.connect((root / "history.sqlite3").as_uri() + "?mode=ro",
                                    uri=True, isolation_level=None, timeout=5)
        try:
            connection.execute("PRAGMA query_only=ON")
            self.assertEqual(connection.execute("PRAGMA query_only").fetchone(), (1,))
            connection.execute("BEGIN")
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
            tables = {}
            for name, order in TABLE_ORDER.items():
                cursor = connection.execute('SELECT * FROM "' + name + '" ORDER BY ' + order)
                columns = tuple(item[0] for item in cursor.description)
                rows = []
                for row in cursor.fetchall():
                    result = {}
                    for column, value in zip(columns, row):
                        if type(value) is bytes:
                            result[column] = {"blob_hex": value.hex()}
                        else:
                            self.assertTrue(value is None or type(value) in (str, int))
                            result[column] = value
                    rows.append(result)
                tables[name] = rows
            commits = tables["store_commits"]
            self.assertEqual([row["sequence"] for row in commits], list(range(len(commits))))
            value = {"schema": "ceta-native-task-ack-cut-v1", "query_only": True,
                     "tables": tables, "positions": {
                         "store": {"next_commit": len(commits),
                                   "head": None if not commits else commits[-1]["head"]},
                         "scopes": tables["history_scopes"]}}
            connection.execute("COMMIT")
            return value
        finally:
            connection.close()

    def _blob(self, value):
        self.assertIsInstance(value, dict)
        self.assertEqual(set(value), {"blob_hex"})
        return bytes.fromhex(value["blob_hex"])

    def _cell(self, cut, key):
        matches = [row for row in cut["tables"]["store_cells"]
                   if (row["collection"], row["scope_id"], row["record_id"])
                   == (key.collection, key.scope_id, key.record_id)]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def _assert_committed(self, root, request, witness, response, *, count, changes):
        from ceta.contracts.events import EventContract, StreamPosition
        from ceta.contracts.kernel_transactions import task_key, task_wire
        from ceta.contracts.task_drafts import (
            catalog_key, decode_catalog, decode_snapshot, draft_key, validate_result)
        cut = self._read_only_cut(root)
        self.assertEqual(cut, witness["durable_cut"],
                         "independent read-only observation differs from committed child witness")
        self.assertEqual(cut["positions"]["store"], witness["commit_position"])
        self.assertEqual(cut["positions"]["store"]["next_commit"], count)
        self.assertEqual(len(cut["tables"]["history_events"]), count)
        self.assertEqual(len(cut["tables"]["store_commits"]), count)
        self.assertEqual(len(cut["tables"]["store_changes"]), changes)
        self.assertEqual(len(cut["tables"]["store_cells"]), 3)
        snapshot = decode_snapshot(response.task_result.snapshot_wire)
        self.assertEqual(witness["snapshot_sha256"],
                         hashlib.sha256(response.task_result.snapshot_wire).hexdigest())
        self.assertEqual((snapshot["request_id"], snapshot["request_commitment"]),
                         (request.record.record_id, request.record.commitment))
        self.assertEqual(snapshot["state"], "CREATED")
        self.assertTrue(all(value is None for value in snapshot["meaning"].values()))
        self.assertEqual(snapshot["principal_id"], PRINCIPAL)
        self.assertEqual(snapshot["updated_session"], request.sender_session)
        self.assertEqual(snapshot["objective_generation"], count)
        revision = validate_result(response.task_result, request.record, request.operation)
        draft = self._cell(cut, draft_key(PROJECT, snapshot["task_id"]))
        kernel = self._cell(cut, task_key(PROJECT, snapshot["task_id"]))
        catalog = self._cell(cut, catalog_key(PROJECT, snapshot["owner_binding"]))
        self.assertEqual((draft["generation"], draft["revision"]), (count, revision))
        self.assertEqual(self._blob(draft["value_wire"]), response.task_result.snapshot_wire)
        self.assertEqual(kernel["generation"], count)
        self.assertEqual(self._blob(kernel["value_wire"]),
                         task_wire(PROJECT, snapshot["task_id"], snapshot["objective_revision"]))
        self.assertEqual(catalog["generation"], 1)
        self.assertEqual(decode_catalog(self._blob(catalog["value_wire"]),
                                       PROJECT, snapshot["owner_binding"]),
                         (snapshot["task_id"],))
        contract = EventContract(self.codec)
        event_wire, payload_wire = bytes.fromhex(witness["event_hex"]), bytes.fromhex(witness["payload_hex"])
        parsed = contract.require_successor(event_wire,
            StreamPosition(PROJECT, snapshot["event_sequence"], snapshot["previous_head"]))
        event = parsed.record.as_dict()
        payload = contract.require_payload(event_wire, payload_wire).as_dict()
        self.assertEqual(event["record_id"], snapshot["event_id"])
        self.assertEqual(event["sequence"], count - 1)
        self.assertEqual(event["event_type"],
                         "task.created" if request.operation == "task.create" else "task.draft.saved")
        self.assertEqual((event["causation_ref"], payload["causation_ref"]),
                         (request.record.record_id, request.record.record_id))
        self.assertEqual((event["actor_id"], event["actor_session"]), (PRINCIPAL, request.sender_session))
        self.assertIsNone(payload["observed_at"])
        matching = [row for row in cut["tables"]["history_events"]
                    if self.codec.decode(self._blob(row["event_wire"])).as_dict()["causation_ref"]
                    == request.record.record_id]
        self.assertEqual(len(matching), 1, "the old command caused duplicate events")
        self.assertEqual(self._blob(matching[0]["event_wire"]), event_wire)
        self.assertEqual(self._blob(matching[0]["payload_wire"]), payload_wire)
        project_position = next(row for row in cut["positions"]["scopes"] if row["scope_id"] == PROJECT)
        self.assertEqual((project_position["next_sequence"], project_position["head"]), (count, parsed.head))
        installation_position = next(row for row in cut["positions"]["scopes"] if row["scope_id"] == INSTALLATION)
        self.assertEqual((installation_position["next_sequence"], installation_position["head"]), (0, None))
        self.assertEqual(len(witness["commit_history"]), 1)
        history = witness["commit_history"][0]
        self.assertEqual(history["event_ids"], [snapshot["event_id"]])
        self.assertEqual(history["before"]["next_sequence"], count - 1)
        self.assertEqual(history["after"], project_position)
        self.assertEqual(len(witness["commit_cells"]), 3 if request.operation == "task.create" else 2)
        self._preserve(root, "post_commit_parent_cut.json", cut)
        return cut, snapshot

    def _stop(self, service):
        service.request_stop("reason:native-task-ack-test-stop")
        observed = self._until(
            lambda: (value if (value := service.poll())["state"] == "STOPPED" else None),
            "owned native processes/jobs/workers/cleanup did not reach STOPPED")
        self.assertEqual(observed["authority"], "CLOSED")
        with service._lock:
            self.assertEqual(service._workers, [])
            self.assertEqual(service._launches_in_progress, 0)
            self.assertFalse(service._service_launch_pending)
        for channel in (service._client, service._service):
            if channel is not None:
                self.assertTrue(channel.observed_exited())
        return observed

    def test_native_committed_create_lost_reply_loads_exact_attempt_without_replay_in_same_controller(self):
        from ceta.contracts.task_drafts import decode_snapshot
        from ceta.contracts.wire import ContractError
        root = self._directory()
        command_id, task_id = "command:lost-create-" + uuid.uuid4().hex, "task:lost-create"
        service = self._start_fault_service(root, kind="create", command_id=command_id, task_id=task_id)
        initial = self._read_only_cut(root)
        self.assertEqual(initial["positions"]["store"], {"next_commit": 0, "head": None})
        self.assertEqual(initial["tables"]["history_events"], [])
        self.assertEqual(initial["tables"]["store_cells"], [])
        self._preserve(root, "initial_parent_cut.json", initial)
        wire = self._command("create", command_id=command_id, pretty=True,
                             task_id=task_id, title=TITLE, instruction=INSTRUCTION, draft=DRAFT)
        attempt, request, witness, suppressed = self._lost_call(service, root, "create", wire)
        committed, snapshot = self._assert_committed(
            root, request, witness, suppressed, count=1, changes=3)
        for name, text in (("title_hex", TITLE), ("instruction_hex", INSTRUCTION), ("draft_hex", DRAFT)):
            self.assertEqual(snapshot[name], text.encode("utf8").hex())
        with self.assertRaises(ContractError):
            service.begin_call(wire, "task.create")
        self.assertEqual(service._task_reconciliation_history, [])
        _, listing = self._call(service, "list")
        self.assertEqual(listing.task_result.task_ids, (task_id,))
        self.assertEqual(service.state, "RECOVERING")
        self.assertEqual(service._uncertain_task_request, request)
        _, absent = self._call(service, "load", task_id="task:unrelated-never-created")
        self.assertEqual(absent.kind, "TASK_ABSENT")
        self.assertEqual(service.state, "RECOVERING")
        self.assertEqual(service._uncertain_task_request, request)
        self.assertEqual(service._task_reconciliation_history, [])
        self.assertEqual(self._read_only_cut(root), committed)
        _, loaded = self._call(service, "load", task_id=task_id)
        self.assertEqual(loaded.task_result, suppressed.task_result)
        self.assertEqual(decode_snapshot(loaded.task_result.snapshot_wire), snapshot)
        self.assertEqual(service.state, "READY")
        self.assertIsNone(service._uncertain_task_request)
        self.assertEqual(service._task_reconciliation_history, [
            (request.original_message, loaded.original_response, "EXACT_TASK_WRITE_OBSERVED")])
        self.assertEqual((native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes(),
                         request.original_message)
        self.assertFalse((native_fixture_path(service._spool / (attempt + ".response.json"))).exists())
        self.assertEqual(len(tuple(service._spool.glob("*.request.json"))), 4)
        self.assertEqual(self._read_only_cut(root), committed)
        self._preserve(root, "same_controller_reconciliation.json", {
            "schema": "ceta-native-task-ack-reconciliation-v1", "classification": "EXACT_TASK_WRITE_OBSERVED",
            "attempt": attempt, "original_request_sha256": hashlib.sha256(request.original_message).hexdigest(),
            "loaded_response_hex": loaded.original_response.hex(), "state": service.state,
            "authority": service.snapshot()["authority"], "historical_attempt_import": False,
        })
        self._stop(service)
        final = self._read_only_cut(root)
        self.assertEqual(final, committed, "reconciliation or Stop replayed/wrote durable task state")
        self._preserve(root, "final_parent_cut.json", final)

    def test_native_committed_save_lost_reply_survives_new_controller_and_session_without_replay(self):
        from ceta.contracts.store_transactions import StoreCell
        from ceta.contracts.task_drafts import decode_snapshot, draft_key
        root = self._directory()
        command_id, task_id = "command:lost-save-" + uuid.uuid4().hex, "task:lost-save"
        service = self._start_fault_service(root, kind="save", command_id=command_id, task_id=task_id)
        _, created = self._call(service, "create", task_id=task_id,
                                title=TITLE, instruction=INSTRUCTION, draft=DRAFT)
        self.assertEqual(created.kind, "TASK_SNAPSHOT")
        created_snapshot = decode_snapshot(created.task_result.snapshot_wire)
        first = self._read_only_cut(root)
        self.assertEqual(first["positions"]["store"]["next_commit"], 1)
        self._preserve(root, "initial_parent_cut.json", first)
        basis = StoreCell(draft_key(PROJECT, task_id), created.task_result.generation,
                          created.task_result.snapshot_wire).revision
        title, draft = "Edited Cafe\u0301", "Changed \t draft\r\n\x00No automatic replay."
        wire = self._command("save", command_id=command_id, pretty=True, task_id=task_id,
                             expected_revision=basis, title=title, draft=draft)
        attempt, request, witness, suppressed = self._lost_call(service, root, "save", wire)
        committed, snapshot = self._assert_committed(
            root, request, witness, suppressed, count=2, changes=5)
        self.assertEqual(snapshot["instruction_hex"], INSTRUCTION.encode("utf8").hex())
        self.assertEqual(snapshot["instruction_hex"], created_snapshot["instruction_hex"])
        self.assertEqual((snapshot["title_hex"], snapshot["draft_hex"]),
                         (title.encode("utf8").hex(), draft.encode("utf8").hex()))
        self.assertEqual(snapshot["owner_binding"], created_snapshot["owner_binding"])
        self.assertEqual(service._task_reconciliation_history, [])
        old_session, old_generation, old_spool = service._session, service.generation, service._spool
        old_request_path = old_spool / (attempt + ".request.json")
        self._stop(service)
        self.assertEqual(service._uncertain_task_request, request)
        self.assertEqual(service._task_reconciliation_history, [])
        self.assertEqual(native_fixture_path(old_request_path).read_bytes(), request.original_message)
        self.assertEqual(self._read_only_cut(root), committed)

        # A fresh instance uses the production entry point without the wrapper.
        # It reads durable content but does not import/settle old controller work.
        restarted = self._service(root, create=False)
        self.assertNotEqual(restarted._session, old_session)
        self.assertNotEqual(restarted._spool, old_spool)
        self.assertEqual(list(restarted._spool.iterdir()), [])
        self.assertIsNone(restarted._uncertain_task_request)
        self.assertEqual(restarted._task_reconciliation_history, [])
        self._ready(restarted)
        self.assertNotEqual(restarted.generation, old_generation)
        self.assertEqual(list(restarted._spool.iterdir()), [])
        self.assertEqual(list(restarted.snapshot()["positions"]), committed["positions"]["scopes"])
        self.assertEqual(self._read_only_cut(root), committed)
        _, listing = self._call(restarted, "list")
        self.assertEqual(listing.task_result.task_ids, (task_id,))
        _, loaded = self._call(restarted, "load", task_id=task_id)
        self.assertEqual(loaded.task_result, suppressed.task_result)
        loaded_snapshot = decode_snapshot(loaded.task_result.snapshot_wire)
        self.assertEqual(loaded_snapshot, snapshot)
        self.assertEqual((loaded_snapshot["request_id"], loaded_snapshot["request_commitment"]),
                         (request.record.record_id, request.record.commitment))
        self.assertEqual(loaded_snapshot["updated_session"], old_session)
        self.assertNotEqual(loaded_snapshot["updated_session"], restarted._session)
        self.assertEqual(restarted.state, "READY")
        self.assertIsNone(restarted._uncertain_task_request)
        self.assertEqual(restarted._task_reconciliation_history, [],
                         "fresh controller must not manufacture historical-attempt settlement")
        self.assertEqual(service._uncertain_task_request, request)
        self.assertEqual(service._task_reconciliation_history, [])
        self.assertEqual(native_fixture_path(old_request_path).read_bytes(), request.original_message)
        self.assertFalse((native_fixture_path(old_spool / (attempt + ".response.json"))).exists())
        self.assertEqual(len(tuple(old_spool.glob("*.request.json"))), 2)
        self.assertEqual(len(tuple(restarted._spool.glob("*.request.json"))), 2)
        self.assertEqual(self._read_only_cut(root), committed)
        self._preserve(root, "restart_content_observation.json", {
            "schema": "ceta-native-task-ack-restart-v1",
            "classification": "EXACT_COMMITTED_CONTENT_OBSERVED_OLD_ATTEMPT_NOT_IMPORTED",
            "attempt": attempt, "original_request_sha256": hashlib.sha256(request.original_message).hexdigest(),
            "old_session": old_session, "new_session": restarted._session,
            "old_generation": old_generation, "new_generation": restarted.generation,
            "old_spool": str(old_spool), "new_spool": str(restarted._spool),
            "loaded_response_hex": loaded.original_response.hex(),
            "fresh_history_entries": 0, "old_uncertain_request_still_retained": True,
            "authority": restarted.snapshot()["authority"],
        })
        self._stop(restarted)
        final = self._read_only_cut(root)
        self.assertEqual(final, committed,
                         "fresh startup, authenticated reads or Stop replayed/wrote durable task state")
        self.assertEqual(native_fixture_path(old_request_path).read_bytes(), request.original_message)
        self._preserve(root, "final_parent_cut.json", final)

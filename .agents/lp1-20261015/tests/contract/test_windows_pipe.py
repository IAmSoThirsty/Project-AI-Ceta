"""Real disposable Windows ingress clients, not authority/effect qualification.

The clients use the direct base Python executable, server-owned registrations,
synthetic records and temporary v2 store fixtures. No normal profile, key,
device, installed service or original B063/B068 acceptance is exercised.
"""
import base64
import ctypes
from ctypes import wintypes
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.kernel_transactions import PeerIdentity
from ceta.contracts.local_ipc import decode_message, encode_message
from ceta.contracts.wire import (ContractError, MAX_WIRE_BYTES, RecordCodec,
                                 canonical_bytes, strict_loads)
from test_all_records import example
from test_kernel_transactions import INSTALLATION, PROJECT, KernelFixture

if sys.platform == "win32":
    from ceta.identity import windows_pipe as native_pipe
    from ceta.composition.ipc_service import compose_local_kernel_service
    from ceta.identity.owners import WindowsIdentityOwners
    from ceta.identity.windows_pipe import WindowsPeerRegistry, WindowsPipeServer


# This owned client waits for explicit test instructions; it does not open a
# pipe until the parent has registered its actual PID and retained lifetime.
CLIENT_SOURCE = r'''
import base64, ctypes, json, os, sys, time
from ctypes import wintypes
sys.path.insert(0, sys.argv[1])
from ceta.identity.windows_pipe import WindowsServerBinding, send_pipe_message
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.WaitNamedPipeW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD)
k.WaitNamedPipeW.restype = wintypes.BOOL
k.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
k.CreateFileW.restype = wintypes.HANDLE
k.WriteFile.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                       ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
k.WriteFile.restype = wintypes.BOOL
k.CloseHandle.argtypes = (wintypes.HANDLE,)
k.CloseHandle.restype = wintypes.BOOL
print(json.dumps({"ready": os.getpid()}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    if request["mode"] == "exit":
        break
    if request["mode"] == "fatal_revert":
        # A proxy belongs only to this disposable process. No real impersonation
        # is performed and no application global or parent API is replaced.
        from ceta.identity.windows_pipe import _Api, _message_facts
        api = _Api()
        class FailedRevertProbe:
            def __init__(self):
                self.token_open_calls = 0
            def __getattr__(self, name):
                return getattr(api, name)
            def ImpersonateNamedPipeClient(self, pipe):
                return True
            def OpenThreadToken(self, *args):
                self.token_open_calls += 1
                if self.token_open_calls == 1:
                    return api.OpenThreadToken(*args)
                ctypes.set_last_error(1008)
                return False
            def RevertToSelf(self):
                return False
        _message_facts(FailedRevertProbe(), None)
        raise RuntimeError("fatal reversion unexpectedly returned")
    try:
        if request["mode"] == "send":
            binding = WindowsServerBinding(request["server_pid"],
                expected_creation_time=request["server_creation"],
                expected_image_sha256=request["server_image_sha256"])
            try:
                result = send_pipe_message(request["pipe"], base64.b64decode(request["wire"]),
                                           timeout_seconds=2.0, expected_server=binding)
                answer = {"sent": True, "returned_none": result is None}
            finally:
                binding.close()
        else:
            # SQOS is explicit even for deliberately anonymous denial probes.
            k.WaitNamedPipeW(request["pipe"], 2000)
            flags = 0x00100000 | (0 if request.get("anonymous") else 0x00020000)
            handle = k.CreateFileW(request["pipe"], 0x40000000, 0, None, 3, flags, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                for part in request.get("parts", []):
                    data = base64.b64decode(part)
                    buffer = ctypes.create_string_buffer(data)
                    written = wintypes.DWORD()
                    if not k.WriteFile(handle, buffer, len(data), ctypes.byref(written), None):
                        raise ctypes.WinError(ctypes.get_last_error())
                    if written.value != len(data):
                        raise RuntimeError("client partial WriteFile")
                time.sleep(request.get("hold_seconds", 0))
                answer = {"sent": True}
            finally:
                k.CloseHandle(handle)
    except Exception as error:
        answer = {"sent": False, "error_type": type(error).__name__, "error": str(error)[:300]}
    print(json.dumps(answer), flush=True)
'''


def trusted_server_values(pid, *, held_handle=None):
    """Fixture owner reads a known process, never the pipe-reported destination.

    This also avoids assuming a venv launcher path is the executing image.
    Calls occur only during the root-coordinated native test run. A selected
    child uses its already-held Popen handle, never a fresh lookup by PID.
    """
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    class FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessId.argtypes = (wintypes.HANDLE,)
    kernel.GetProcessId.restype = wintypes.DWORD
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetProcessTimes.argtypes = (wintypes.HANDLE, *([ctypes.POINTER(FileTime)] * 4))
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD,
        wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    process = kernel.OpenProcess(0x1000 | 0x00100000, False, pid) if held_handle is None else held_handle
    if not process:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if kernel.GetProcessId(process) != pid or kernel.WaitForSingleObject(process, 0) != 258:
            raise AssertionError("trusted selected process handle is not its expected live PID")
        times = [FileTime() for _ in range(4)]
        if not kernel.GetProcessTimes(process, *(ctypes.byref(value) for value in times)):
            raise ctypes.WinError(ctypes.get_last_error())
        path = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(path))
        if not kernel.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(length)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {"server_pid": pid,
                "server_creation": times[0].low | times[0].high << 32,
                "server_image_sha256": hashlib.sha256(Path(path.value).read_bytes()).hexdigest()}
    finally:
        if held_handle is None and not kernel.CloseHandle(process):
            raise ctypes.WinError(ctypes.get_last_error())


class DisposableClient:
    def __init__(self, executable):
        self.process = subprocess.Popen([executable, "-I", "-B", "-c", CLIENT_SOURCE,
            str(ROOT / "src")], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf8",
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.answers = queue.Queue()
        self.errors = []
        def output():
            for line in self.process.stdout:
                self.answers.put(json.loads(line))
            self.answers.put({"eof": True})
        def errors():
            for line in self.process.stderr:
                self.errors.append(line)
        self.output_thread = threading.Thread(target=output, daemon=True)
        self.error_thread = threading.Thread(target=errors, daemon=True)
        self.output_thread.start()
        self.error_thread.start()
        try:
            ready = self.answers.get(timeout=10)
        except BaseException:
            self.close()
            raise
        if ready != {"ready": self.process.pid}:
            self.close()
            raise AssertionError("disposable client failed to initialize: " + repr(ready))

    def command(self, command):
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()

    def answer(self):
        return self.answers.get(timeout=10)

    def close(self):
        if self.process.poll() is None:
            try:
                self.command({"mode": "exit"})
                self.process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait(timeout=3)
        self.output_thread.join(timeout=3)
        self.error_thread.join(timeout=3)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()


@unittest.skipUnless(sys.platform == "win32", "Real Windows named-pipe fixture required")
class WindowsPipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.version_info[:2] != (3, 12):
            raise AssertionError("Native fixture requires the declared Unicode15 Python3.12 interpreter")
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)
        cls.executable = sys._base_executable
        cls.image_sha256 = hashlib.sha256(Path(cls.executable).read_bytes()).hexdigest()
        cls.server_values = trusted_server_values(os.getpid())

    def setUp(self):
        self.clients, self.receivers, self.fixtures = [], [], []
        self.registry = WindowsPeerRegistry()
        self.pipe_name = r"\\.\pipe\CETA-" + uuid.uuid4().hex
        self.session = "session:pipe-fixture"
        self.principal = "worker:pipe-fixture"
        self.calls = []
        self.handler = self.capture
        self.server = WindowsPipeServer(self.pipe_name, self.registry,
            lambda message, context: self.handler(message, context), self.codec)
        self.generation = self.server.receiver_generation

    def tearDown(self):
        self.server.close()
        for client in self.clients:
            client.close()
        for receiver in self.receivers:
            receiver.join(timeout=3)
            self.assertFalse(receiver.is_alive(), "bounded native receive leaked a thread")
        self.registry.close()
        for fixture in self.fixtures:
            fixture.store.close()

    def capture(self, message, context):
        self.registry.require_message(context, message)
        peer = self.registry.authenticate(context)
        self.calls.append((message, context, peer))
        return peer

    def client(self, *, registered=True, principal=None, session=None,
               allowed_operations=("kernel.prepare",), allowed_scopes=(PROJECT,)):
        client = DisposableClient(self.executable)
        self.clients.append(client)
        if registered:
            selected = trusted_server_values(client.process.pid, held_handle=int(client.process._handle))
            client.selected_creation = selected["server_creation"]
            client.registration = self.registry.register(client.process.pid, principal or self.principal,
                session or self.session, allowed_operations=allowed_operations,
                allowed_scopes=allowed_scopes, expected_image_sha256=self.image_sha256,
                expected_creation_time=selected["server_creation"])
        return client

    def message(self, *, record_wire=None, **changes):
        if record_wire is None:
            value = example(self.schema["$defs"]["ActionProposal"])
            value.update(record_id="proposal:pipe-fixture", scope_id=PROJECT)
            record_wire = canonical_bytes(value)
        now = time.time_ns() // 1_000_000
        values = dict(message_id="message:" + uuid.uuid4().hex, sender_session=self.session,
            receiver_generation=self.generation, operation="kernel.prepare",
            issued_at_ms=now - 1000, expires_at_ms=now + 15_000)
        values.update(changes)
        return encode_message(record_wire, self.codec, **values)

    def receive(self, client, command, *, timeout=2.0, server=None):
        results = queue.Queue()
        target = self.server if server is None else server
        def run():
            try:
                results.put((True, target.receive_once(timeout)))
            except BaseException as error:
                results.put((False, error))
        receiver = threading.Thread(target=run, daemon=True)
        self.receivers.append(receiver)
        receiver.start()
        client.command(dict(command, pipe=self.pipe_name))
        client_answer = client.answer()
        success, result = results.get(timeout=10)
        receiver.join(timeout=3)
        self.assertFalse(receiver.is_alive())
        return success, result, client_answer

    def send(self, client, wire, *, expected_server_values=None, **changes):
        binding = self.server_values if expected_server_values is None else expected_server_values
        return self.receive(client, dict(binding, mode="send", wire=base64.b64encode(wire).decode("ascii")), **changes)

    def raw(self, client, *parts, anonymous=False, hold_seconds=0, **changes):
        return self.receive(client, {"mode": "raw", "parts": [base64.b64encode(part).decode("ascii") for part in parts],
            "anonymous": anonymous, "hold_seconds": hold_seconds}, **changes)

    def denied(self, outcome, code=None):
        success, result, _ = outcome
        self.assertFalse(success, "malformed/unauthorized ingress reached a successful handler")
        self.assertIsInstance(result, ContractError)
        if code is not None:
            self.assertEqual(result.code, code)
        self.assertEqual(self.calls, [])

    def test_registered_os_peer_reaches_handler_and_context_expires_after_dispatch(self):
        client = self.client()
        wire = self.message()
        success, peer, answer = self.send(client, wire)
        self.assertTrue(success)
        self.assertEqual(peer, PeerIdentity(self.principal, self.session))
        self.assertEqual(client.registration.pid, client.process.pid)
        self.assertEqual(client.registration.image_sha256, self.image_sha256)
        self.assertGreater(client.registration.process_creation, 0)
        self.assertEqual(client.registration.process_creation, client.selected_creation)
        self.assertEqual(answer, {"sent": True, "returned_none": True})
        self.assertEqual(self.calls[0][0].original_message, wire)
        with self.assertRaises(ContractError):
            self.registry.authenticate(self.calls[0][1])
        with self.assertRaises(ContractError):
            self.registry.require_message(self.calls[0][1], self.calls[0][0])

    def test_real_application_composition_denies_unfinished_preparation_without_store_change(self):
        self.server.close()
        fixture = KernelFixture(self.schema)
        self.fixtures.append(fixture)
        client = self.client(principal=fixture.owners.worker.principal_id,
                             session=fixture.owners.worker.session_id)
        self.server = compose_local_kernel_service(fixture.store, fixture.codec, INSTALLATION,
            self.registry, self.pipe_name)
        self.generation = self.server.receiver_generation
        before = fixture.cut()
        wire = self.message(record_wire=fixture.proposal_wire, sender_session=fixture.owners.worker.session_id)
        self.denied(self.send(client, wire), "TRUSTED_PREPARATION_OWNER_UNAVAILABLE")
        self.assertEqual(fixture.cut(), before)
        # Replay is consumed before the application denial; retry grants no authority.
        self.denied(self.send(client, wire), "IPC_MESSAGE_REPLAY")
        self.assertEqual(fixture.cut(), before)

    def test_unregistered_same_account_child_cannot_impersonate_registered_session(self):
        self.client()  # A different real process owns the declared session.
        unrelated = self.client(registered=False)
        self.denied(self.send(unrelated, self.message()))

    def test_registered_peer_wrong_sender_session_is_denied(self):
        self.denied(self.send(self.client(), self.message(sender_session="session:forged")), "IPC_SESSION_BINDING")

    def test_old_receiver_generation_is_denied(self):
        self.denied(self.send(self.client(), self.message(receiver_generation="service:old")), "IPC_STALE_RECEIVER")

    def test_registered_peer_cannot_select_other_scope(self):
        record = example(self.schema["$defs"]["ActionProposal"])
        record["scope_id"] = "project:other"
        self.denied(self.send(self.client(), self.message(record_wire=canonical_bytes(record))), "IPC_CALLER_SCOPE_DENIED")

    def test_registered_peer_cannot_select_other_route(self):
        permit = canonical_bytes(example(self.schema["$defs"]["OperationPermit"]))
        value = strict_loads(permit)
        value["scope_id"] = PROJECT
        wire = self.message(record_wire=canonical_bytes(value), operation="kernel.consume")
        self.denied(self.send(self.client(), wire), "IPC_CALLER_SCOPE_DENIED")

    def test_replay_is_denied_and_fresh_request_reuses_retained_server(self):
        client = self.client()
        wire = self.message()
        self.assertTrue(self.send(client, wire)[0])
        self.calls.clear()
        self.denied(self.send(client, wire), "IPC_MESSAGE_REPLAY")
        self.assertTrue(self.send(client, self.message())[0])
        self.assertEqual(len(self.calls), 1)

    def test_oversized_declared_frame_is_denied_before_body(self):
        # One tiny byte keeps the header and remaining data in the same native
        # message; denial must be the declared allocation bound, not short-frame.
        self.denied(self.raw(self.client(), (MAX_WIRE_BYTES + 1).to_bytes(4, "big") + b"{"),
                    "IPC_MESSAGE_SIZE_OR_CODEC")

    def test_trailing_bytes_in_one_windows_message_are_denied(self):
        wire = self.message()
        self.denied(self.raw(self.client(), len(wire).to_bytes(4, "big") + wire + b"x"),
                    "WINDOWS_PIPE_SHORT_OR_TRAILING_MESSAGE")

    def test_partial_header_and_partial_body_disconnections_are_denied(self):
        client = self.client()
        for frame in (b"\x00\x00", (1000).to_bytes(4, "big") + b"{"):
            with self.subTest(bytes=len(frame)):
                self.denied(self.raw(client, frame))

    def test_split_windows_messages_do_not_reconstruct_a_complete_request(self):
        wire = self.message()
        self.denied(self.raw(self.client(), len(wire).to_bytes(4, "big"), wire),
                    "WINDOWS_PIPE_HEADER_OR_SHORT_MESSAGE")

    def test_duplicate_json_and_caller_identity_flags_are_denied_by_native_receiver(self):
        client = self.client()
        wire = self.message()
        malicious = (wire[:-1] + b',"version":1}', canonical_bytes(dict(strict_loads(wire), authenticated=True, pid=client.process.pid)))
        for message in malicious:
            with self.subTest(length=len(message)):
                self.denied(self.raw(client, len(message).to_bytes(4, "big") + message))

    def test_anonymous_sqos_connection_cannot_supply_registered_identity(self):
        wire = self.message()
        self.denied(self.raw(self.client(), len(wire).to_bytes(4, "big") + wire, anonymous=True))

    def test_occupied_name_does_not_replace_original_acquired_instance(self):
        with self.assertRaises(ContractError):
            WindowsPipeServer(self.pipe_name, self.registry, self.capture, self.codec)
        self.assertTrue(self.send(self.client(), self.message())[0])

    def test_same_name_reconstruction_has_new_generation_and_rejects_old_valid_envelope(self):
        client = self.client()
        old_wire, old_generation = self.message(), self.generation
        self.server.close()
        self.server = WindowsPipeServer(self.pipe_name, self.registry,
            lambda message, context: self.handler(message, context), self.codec)
        self.generation = self.server.receiver_generation
        self.assertNotEqual(self.generation, old_generation)
        with self.assertRaises(AttributeError):
            self.server.receiver_generation = old_generation
        self.denied(self.send(client, old_wire), "IPC_STALE_RECEIVER")
        self.assertTrue(self.send(client, self.message())[0])

    def test_safe_sender_rejects_wrong_destination_process_before_handler_dispatch(self):
        client = self.client()
        other_process = self.client(registered=False)
        values = trusted_server_values(other_process.process.pid, held_handle=int(other_process.process._handle))
        outcome = self.send(client, self.message(), expected_server_values=values, timeout=0.5)
        self.denied(outcome)
        self.assertFalse(outcome[2]["sent"])
        self.assertEqual(outcome[2]["error_type"], "ContractError")
        self.assertIn("WINDOWS_PIPE_DESTINATION_MISMATCH", outcome[2]["error"])

    def test_safe_sender_rejects_wrong_expected_creation_before_handler_dispatch(self):
        values = dict(self.server_values, server_creation=self.server_values["server_creation"] + 1)
        outcome = self.send(self.client(), self.message(), expected_server_values=values, timeout=0.5)
        self.denied(outcome)
        self.assertFalse(outcome[2]["sent"])
        self.assertEqual(outcome[2]["error_type"], "ContractError")
        self.assertIn("WINDOWS_SERVER_CREATION_MISMATCH", outcome[2]["error"])

    def test_failed_reversion_terminates_only_disposable_child_with_exit125(self):
        client = self.client(registered=False)
        client.command({"mode": "fatal_revert"})
        self.assertEqual(client.process.wait(timeout=5), 125)
        self.assertEqual(self.calls, [])

    def test_connection_timeout_and_empty_disconnect_do_not_dispatch(self):
        with self.assertRaises(ContractError):
            self.server.receive_once(0.05)
        self.denied(self.raw(self.client()))
        self.assertTrue(self.send(self.clients[-1], self.message())[0])

    def test_connected_silent_client_hits_bounded_receive_timeout(self):
        self.denied(self.raw(self.client(), hold_seconds=0.3, timeout=0.05))

    def test_expired_or_future_envelope_does_not_dispatch(self):
        client = self.client()
        now = time.time_ns() // 1_000_000
        for issued, expires in ((now - 2000, now - 1000), (now + 10_000, now + 20_000)):
            with self.subTest(issued=issued):
                self.denied(self.send(client, self.message(issued_at_ms=issued, expires_at_ms=expires)), "IPC_MESSAGE_EXPIRED_OR_FUTURE")

    def test_wrong_executable_image_pin_is_rejected_at_registration(self):
        client = self.client(registered=False)
        with self.assertRaises(ContractError):
            self.registry.register(client.process.pid, self.principal, self.session,
                allowed_operations=("kernel.prepare",), allowed_scopes=(PROJECT,),
                expected_image_sha256="0" * 64,
                expected_creation_time=trusted_server_values(client.process.pid,
                    held_handle=int(client.process._handle))["server_creation"])

    def test_peer_registration_rejects_mismatched_parent_selected_creation(self):
        client = self.client(registered=False)
        selected = trusted_server_values(client.process.pid, held_handle=int(client.process._handle))
        with self.assertRaises(ContractError) as caught:
            self.registry.register(client.process.pid, self.principal, self.session,
                allowed_operations=("kernel.prepare",), allowed_scopes=(PROJECT,),
                expected_image_sha256=self.image_sha256,
                expected_creation_time=selected["server_creation"] + 1)
        self.assertEqual(caught.exception.code, "WINDOWS_PEER_CREATION_MISMATCH")
        self.denied(self.send(client, self.message()), "WINDOWS_PIPE_CLIENT_UNREGISTERED")

    def test_active_context_cannot_bind_different_envelope_or_another_thread(self):
        other = decode_message(self.message(), self.codec)
        checks = []
        def handler(message, context):
            self.registry.authenticate(context)
            changed_record = message.record.as_dict()
            changed_record["record_id"] = "proposal:substituted-inner-record"
            parsed_record = self.codec.decode(canonical_bytes(changed_record))
            for candidate in (other, replace(message, original_message=message.original_message + b" "),
                              replace(message, operation="kernel.resolve_consumption"),
                              replace(message, record=parsed_record)):
                with self.assertRaises(ContractError):
                    self.registry.require_message(context, candidate)
                checks.append("message-denied")
            result = queue.Queue()
            def foreign_thread():
                try:
                    self.registry.authenticate(context)
                except ContractError:
                    result.put("thread-denied")
                else:
                    result.put("unexpected-allow")
            thread = threading.Thread(target=foreign_thread, daemon=True)
            thread.start()
            checks.append(result.get(timeout=3))
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            return "checked"
        self.handler = handler
        self.assertEqual(self.send(self.client(), self.message())[:2], (True, "checked"))
        self.assertEqual(checks, ["message-denied", "message-denied", "message-denied", "message-denied", "thread-denied"])

    def test_retained_client_lifetime_is_rechecked_inside_active_dispatch(self):
        client = self.client()
        def handler(message, context):
            self.registry.authenticate(context)
            client.process.terminate()
            client.process.wait(timeout=3)
            with self.assertRaises(ContractError):
                self.registry.authenticate(context)
            return "exited-peer-denied"
        self.handler = handler
        self.assertEqual(self.send(client, self.message())[:2], (True, "exited-peer-denied"))

    def test_final_authentication_rechecks_monotonic_and_wall_expiry_after_real_peer_validation(self):
        fixture = KernelFixture(self.schema)
        self.fixtures.append(fixture)
        before = fixture.cut()
        checks = []
        def handler(message, context):
            real_peer = self.registry._pipe_peer
            real_clock = native_pipe.time
            for axis in ("monotonic", "wall"):
                for operation in ("authenticate", "require_message"):
                    crossed = {"value": False}
                    def query_then_cross(pipe, deadline):
                        result = real_peer(pipe, deadline)
                        crossed["value"] = True
                        return result
                    class ObservedClock:
                        def __getattr__(self, name):
                            return getattr(real_clock, name)
                        def monotonic(self):
                            observed = real_clock.monotonic()
                            return observed + 3600 if crossed["value"] and axis == "monotonic" else observed
                        def time_ns(self):
                            return message.expires_at_ms * 1_000_000 if crossed["value"] and axis == "wall" else real_clock.time_ns()
                    # Both patches are scoped to this serial native handler and
                    # restore even when the assertion or real query fails.
                    with patch.object(self.registry, "_pipe_peer", query_then_cross), \
                         patch.object(native_pipe, "time", ObservedClock()):
                        with self.assertRaises(ContractError) as caught:
                            if operation == "authenticate":
                                self.registry.authenticate(context)
                            else:
                                self.registry.require_message(context, message)
                        expected = "WINDOWS_REQUEST_CONTEXT_EXPIRED" if axis == "monotonic" else "IPC_MESSAGE_EXPIRED_OR_FUTURE"
                        self.assertEqual(caught.exception.code, expected)
                        self.assertTrue(crossed["value"], "denial must follow the real final peer query")
                    checks.append((axis, operation))
                    self.assertEqual(fixture.cut(), before)
            return "final-freshness-denied"
        self.handler = handler
        outcome = self.send(self.client(), self.message())
        self.assertEqual(outcome[:2], (True, "final-freshness-denied"))
        self.assertEqual(checks, [(axis, operation) for axis in ("monotonic", "wall")
                                 for operation in ("authenticate", "require_message")])
        self.assertEqual(fixture.cut(), before)

    def test_fabricated_context_never_supplies_identity_or_message_binding(self):
        owners = WindowsIdentityOwners(self.registry)
        message = decode_message(self.message(), self.codec)
        for context in (object(), {"authenticated": True, "pid": 1, "principal_id": self.principal}, None):
            with self.subTest(kind=type(context).__name__), self.assertRaises(ContractError):
                owners.authenticate(context)
            with self.assertRaises(ContractError):
                owners.require_message(context, message)

    def token_query_fixture(self, wire, expected_class):
        class QueryOnly:
            def GetTokenInformation(self, token, information_class, buffer, count, needed):
                if information_class != expected_class:
                    raise AssertionError("unexpected token information class")
                needed._obj.value = len(wire)
                if buffer is None:
                    ctypes.set_last_error(122)
                    return False
                if count < len(wire):
                    raise AssertionError("token fixture allocation was not bounded correctly")
                ctypes.memmove(buffer, wire, len(wire))
                return True
        return QueryOnly()

    def test_restriction_flag_accepts_only_exact_one_or_four_byte_boolean_layouts(self):
        prior_error = ctypes.get_last_error()
        try:
            for wire, flag in ((b"\x00", 0), (b"\x01", 1),
                               (b"\x00\x00\x00\x00", 0), (b"\x01\x00\x00\x00", 1)):
                with self.subTest(layout=len(wire), flag=flag):
                    self.assertEqual(native_pipe._restriction_flag(self.token_query_fixture(wire, 21), None), flag)
            # The observed class21 exception cannot relax other DWORD scalars.
            with self.assertRaises(ContractError) as caught:
                native_pipe._scalar(self.token_query_fixture(b"\x01", 12), None, 12)
            self.assertEqual(caught.exception.code, "WINDOWS_TOKEN_SCALAR")
        finally:
            ctypes.set_last_error(prior_error)

    def test_restriction_flag_rejects_unsupported_layouts_and_nonboolean_values(self):
        prior_error = ctypes.get_last_error()
        try:
            for size in (2, 3, 5, 8):
                with self.subTest(size=size), self.assertRaises(ContractError) as caught:
                    native_pipe._restriction_flag(self.token_query_fixture(b"\x00" * size, 21), None)
                self.assertEqual(caught.exception.code, "WINDOWS_TOKEN_RESTRICTION_LAYOUT")
            for wire in (b"\x02", b"\xff", b"\x02\x00\x00\x00", b"\xff\xff\xff\xff"):
                with self.subTest(wire=wire.hex()), self.assertRaises(ContractError) as caught:
                    native_pipe._restriction_flag(self.token_query_fixture(wire, 21), None)
                self.assertEqual(caught.exception.code, "WINDOWS_TOKEN_RESTRICTION_FLAG")
        finally:
            ctypes.set_last_error(prior_error)

    def test_effective_token_rejects_identification_anonymous_and_delegation_levels(self):
        prior_error = ctypes.get_last_error()
        try:
            for level in (0, 1, 3):
                statistics = native_pipe.TOKEN_STATISTICS()
                statistics.token_type, statistics.impersonation_level = 2, level
                with self.subTest(level=level), self.assertRaises(ContractError) as caught:
                    native_pipe._token_facts(self.token_query_fixture(bytes(statistics), 10), None, 2)
                self.assertEqual(caught.exception.code, "WINDOWS_IMPERSONATION_LEVEL_UNSUPPORTED")
        finally:
            ctypes.set_last_error(prior_error)

    def test_token_query_rejects_changed_returned_length_instead_of_parsing_padding(self):
        prior_error = ctypes.get_last_error()
        query = self.token_query_fixture(b"\x01\x00\x00\x00", 12)
        class ChangedLength:
            def GetTokenInformation(self, token, information_class, buffer, count, needed):
                result = query.GetTokenInformation(token, information_class, buffer, count, needed)
                if buffer is not None:
                    needed._obj.value = 1
                return result
        try:
            with self.assertRaises(ContractError) as caught:
                native_pipe._scalar(ChangedLength(), None, 12)
            self.assertEqual(caught.exception.code, "WINDOWS_TOKEN_QUERY_SIZE")
        finally:
            ctypes.set_last_error(prior_error)

    def owned_image_fixture(self):
        # Synthetic immutable bytes exercise the real image-hash I/O mechanism;
        # this is not a claim that the fixture is a runnable executable.
        directory = ROOT / ".agents/fixtures/native-image-23" / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=False)
        path = directory / "owned-image-read-fixture.bin"
        wire = (b"CETA bounded native image fixture\x00" * 40_000) + b"tail"
        path.write_bytes(wire)
        api = native_pipe._Api()
        handle = api.CreateFileW(str(path), 0x0001 | 0x0080, 0x0001, None, 3,
                                0x00200000 | 0x40000000, None)
        if handle in (None, 0, native_pipe.INVALID_HANDLE):
            raise ctypes.WinError(ctypes.get_last_error())
        return api, handle, wire

    def test_actual_overlapped_image_hash_uses_explicit_offsets_and_restarts_at_zero(self):
        api, handle, wire = self.owned_image_fixture()
        offsets = []
        class ObservedApi:
            def __getattr__(self, name):
                return getattr(api, name)
            def ReadFile(self, selected, buffer, count, transferred, overlapped):
                self_offset = overlapped._obj.offset | overlapped._obj.offset_high << 32
                offsets.append(self_offset)
                return api.ReadFile(selected, buffer, count, transferred, overlapped)
        try:
            first = native_pipe._file_hash(ObservedApi(), handle, time.monotonic() + 5)
            self.assertEqual(first[0], hashlib.sha256(wire).hexdigest())
            self.assertEqual(offsets, [0, 1024 * 1024])
            offsets.clear()
            second = native_pipe._file_hash(ObservedApi(), handle, time.monotonic() + 5)
            self.assertEqual(second, first)
            self.assertEqual(offsets, [0, 1024 * 1024])
        finally:
            api.close_handle(handle)

    def test_image_deadline_expired_before_read_issues_no_native_read(self):
        api, handle, _ = self.owned_image_fixture()
        reads = []
        class ObservedApi:
            def __getattr__(self, name):
                return getattr(api, name)
            def ReadFile(self, *args):
                reads.append(True)
                return api.ReadFile(*args)
        try:
            with self.assertRaises(ContractError) as caught:
                native_pipe._file_hash(ObservedApi(), handle, time.monotonic() - 1)
            self.assertEqual(caught.exception.code, "WINDOWS_PIPE_TIMEOUT")
            self.assertEqual(reads, [])
        finally:
            api.close_handle(handle)

    def test_owned_image_timeout_cancels_and_drains_before_releasing_io_storage(self):
        api, handle, _ = self.owned_image_fixture()
        actual_clock = native_pipe.time
        crossed, actions = {"value": False}, []
        class ObservedClock:
            def __getattr__(self, name):
                return getattr(actual_clock, name)
            def monotonic(self):
                return actual_clock.monotonic() + (3600 if crossed["value"] else 0)
        class OwnedIoProxy:
            def __getattr__(self, name):
                return getattr(api, name)
            def ReadFile(self, selected, buffer, count, transferred, overlapped):
                self.buffer, self.overlapped = buffer, overlapped._obj
                result = api.ReadFile(selected, buffer, count, transferred, overlapped)
                error = ctypes.get_last_error()
                if not result and error != native_pipe.ERROR_IO_PENDING:
                    return result
                actions.append("real-read-issued")
                # Completion may already have won. Observe it through the same
                # owned event; only this proxy's first wait is reported late.
                ctypes.set_last_error(native_pipe.ERROR_IO_PENDING)
                return False
            def WaitForSingleObject(self, event, milliseconds):
                observed = api.WaitForSingleObject(event, milliseconds)
                if not crossed["value"]:
                    if observed != native_pipe.WAIT_OBJECT_0:
                        raise AssertionError("owned image read did not complete before controlled observation")
                    crossed["value"] = True
                    actions.append("controlled-late-wait")
                    return native_pipe.WAIT_TIMEOUT
                return observed
            def CancelIoEx(self, selected, overlapped):
                actions.append("cancel-requested")
                return api.CancelIoEx(selected, overlapped)
            def GetOverlappedResult(self, selected, overlapped, transferred, wait):
                result = api.GetOverlappedResult(selected, overlapped, transferred, wait)
                if result:
                    if transferred._obj.value <= 0:
                        raise AssertionError("real owned read completion had no bytes")
                    actions.append("actual-completion-drained")
                return result
            def close_handle(self, event):
                if actions[-1:] != ["actual-completion-drained"]:
                    raise AssertionError("I/O event/storage released before actual completion drain")
                actions.append("event-closed")
                return api.close_handle(event)
        proxy = OwnedIoProxy()
        try:
            with patch.object(native_pipe, "time", ObservedClock()):
                with self.assertRaises(ContractError) as caught:
                    native_pipe._file_hash(proxy, handle, actual_clock.monotonic() + 5)
                self.assertEqual(caught.exception.code, "WINDOWS_PIPE_TIMEOUT")
            self.assertEqual(actions, ["real-read-issued", "controlled-late-wait", "cancel-requested",
                                      "actual-completion-drained", "event-closed"])
            self.assertIsNotNone(proxy.buffer)
            self.assertIsNotNone(proxy.overlapped)
        finally:
            api.close_handle(handle)

    def test_real_image_read_completion_after_deadline_does_not_renew_request(self):
        api, handle, _ = self.owned_image_fixture()
        actual_clock, crossed = native_pipe.time, {"value": False}
        class ObservedClock:
            def __getattr__(self, name):
                return getattr(actual_clock, name)
            def monotonic(self):
                return actual_clock.monotonic() + (3600 if crossed["value"] else 0)
        class CompletedReadProxy:
            def __getattr__(self, name):
                return getattr(api, name)
            def GetOverlappedResult(self, *args):
                result = api.GetOverlappedResult(*args)
                if result:
                    crossed["value"] = True
                return result
        try:
            with patch.object(native_pipe, "time", ObservedClock()):
                with self.assertRaises(ContractError) as caught:
                    native_pipe._file_hash(CompletedReadProxy(), handle, actual_clock.monotonic() + 5)
                self.assertEqual(caught.exception.code, "WINDOWS_PIPE_TIMEOUT")
                self.assertTrue(crossed["value"])
        finally:
            api.close_handle(handle)


if __name__ == "__main__":
    unittest.main()

"""P00/D01 native outer-process child-retirement regression.

This fixture starts a real disposable OwnedService inside a plain Python outer
process.  The outer process duplicates the exact live client/service process
handles into this test process before a controlled ``os._exit``.  The test
then observes those already-pinned handles, not a PID lookup, and checks the
launcher PENDING fence.  A separately created unowned control process must
remain alive across the outer process exit.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import queue
import struct
import subprocess
import sys
import threading
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.application.lifecycle import LauncherCustodyIncomplete, LauncherShutdownCustody
from ceta.supervisor.service import controlled_environment


WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
SYNCHRONIZE = 0x00100000
PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_SAME_ACCESS = 0x00000002
CREATE_NO_WINDOW = 0x08000000
OUTER_EXIT_CODE = 86


OUTER = r'''
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import sys
import time

root, parent_pid, source = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(source))
from ceta.application.lifecycle import LauncherShutdownCustody
from ceta.composition.owned_service import OwnedService
from ceta.contracts.wire import RecordCodec, strict_loads

kernel = C.WinDLL("kernel32", use_last_error=True, winmode=0x800)
kernel.GetCurrentProcess.argtypes = []
kernel.GetCurrentProcess.restype = W.HANDLE
kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
kernel.OpenProcess.restype = W.HANDLE
kernel.DuplicateHandle.argtypes = [W.HANDLE, W.HANDLE, W.HANDLE, C.POINTER(W.HANDLE), W.DWORD, W.BOOL, W.DWORD]
kernel.DuplicateHandle.restype = W.BOOL
kernel.CloseHandle.argtypes = [W.HANDLE]
kernel.CloseHandle.restype = W.BOOL


def copy_exact_handle(raw):
    target = kernel.OpenProcess(0x0040, False, parent_pid)
    if not target:
        raise OSError(C.get_last_error(), "OpenProcess(PROCESS_DUP_HANDLE)")
    copied = W.HANDLE()
    try:
        if not kernel.DuplicateHandle(kernel.GetCurrentProcess(), W.HANDLE(raw), target,
                                      C.byref(copied), 0, False, 0x00000002):
            raise OSError(C.get_last_error(), "DuplicateHandle")
        if not copied.value:
            raise RuntimeError("DUPLICATE_HANDLE_ZERO")
        return int(copied.value)
    finally:
        if not kernel.CloseHandle(target):
            raise OSError(C.get_last_error(), "CloseHandle(parent)")


def report(channel):
    process = channel.process
    if process is None or process._process is None or process.poll() is not None:
        raise RuntimeError("OWNED_CHILD_NOT_LIVE_FOR_PINNING")
    return {
        "handle": copy_exact_handle(process._process),
        "pid": process.pid,
        "creation_time": process.creation_time,
        "image_sha256": process.image_sha256,
    }

try:
    schema = strict_loads((Path(sys.argv[4]) / "contracts/schemas/records.schema.json").read_bytes())
    codec = RecordCodec(schema)
    installation = "installation:outer-native-retirement"
    scopes = (installation, "project:outer-native-retirement")
    custody = LauncherShutdownCustody(root)
    custody.reserve_launch()
    custody.mark_start_requested()
    service = OwnedService(root, codec, installation, scopes, create=True,
                           principal_id="operator:outer-native-retirement",
                           session_id="session:outer-native-retirement")
    service.start()
    deadline = time.monotonic() + 15
    while True:
        observed = service.poll()
        if observed["state"] == "READY":
            break
        if observed["state"] == "RECOVERING":
            raise RuntimeError("OUTER_SERVICE_RECOVERING:" + observed["detail"])
        if time.monotonic() >= deadline:
            raise RuntimeError("OUTER_SERVICE_READY_TIMEOUT:" + observed["state"])
        time.sleep(0.005)
    custody.mark_start_returned()
    children = [report(service._client), report(service._service)]
    if len({entry["handle"] for entry in children}) != 2:
        raise RuntimeError("OWNED_CHILD_HANDLE_IDENTITY_COLLISION")
    print(json.dumps({"state": "READY", "children": children,
                      "custody": custody.record}, sort_keys=True), flush=True)
    sys.stdin.buffer.read(1)
    os._exit(86)
except BaseException as error:
    print(json.dumps({"state": "ERROR", "type": type(error).__name__,
                      "message": str(error)}, sort_keys=True), flush=True)
    os._exit(70)
'''


@unittest.skipUnless(sys.platform == "win32" and struct.calcsize("P") == 8,
                     "real Windows x64 required")
class OuterProcessChildRetirementTests(unittest.TestCase):
    """Actual outer death must retire only the actual product-owned children."""

    @classmethod
    def setUpClass(cls):
        cls._kernel = C.WinDLL("kernel32", use_last_error=True, winmode=0x800)
        declarations = {
            "WaitForSingleObject": ([W.HANDLE, W.DWORD], W.DWORD),
            "CloseHandle": ([W.HANDLE], W.BOOL),
            "GetProcessId": ([W.HANDLE], W.DWORD),
            "GetProcessTimes": ([W.HANDLE, C.POINTER(W.FILETIME), C.POINTER(W.FILETIME),
                                  C.POINTER(W.FILETIME), C.POINTER(W.FILETIME)], W.BOOL),
            "TerminateProcess": ([W.HANDLE, W.UINT], W.BOOL),
        }
        for name, (arguments, result) in declarations.items():
            function = getattr(cls._kernel, name)
            function.argtypes, function.restype = arguments, result

    def setUp(self):
        self._outer = None
        self._unowned = None
        self._pinned = []
        self._readers = []
        self.root = ROOT / ".agents/fixtures/outer-native-child-retirement" / uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=False)

    def tearDown(self):
        failures = []
        if self._outer is not None:
            try:
                if self._outer.poll() is None:
                    # Failure-only containment for the exact Popen outer fixture.
                    # The normal path uses the fixture's controlled os._exit.
                    self._outer.terminate()
                self._outer.wait(timeout=8)
            except BaseException as error:
                failures.append("outer=" + repr(error))
            for stream in (self._outer.stdin, self._outer.stdout, self._outer.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except BaseException as error:
                    failures.append("outer-stream=" + repr(error))
        for thread in self._readers:
            thread.join(timeout=5)
            if thread.is_alive():
                failures.append("outer-reader-unresolved")
        for child in self._pinned:
            try:
                if self._kernel.WaitForSingleObject(child["handle"], 0) != WAIT_OBJECT_0:
                    # Failure-only cleanup uses the exact duplicated child
                    # handle; it never selects a process by PID or image name.
                    if not self._kernel.TerminateProcess(child["handle"], 126):
                        raise OSError(C.get_last_error(), "TerminateProcess(exact duplicated child handle)")
                    if self._kernel.WaitForSingleObject(child["handle"], 8000) != WAIT_OBJECT_0:
                        raise AssertionError("exact owned child did not exit during cleanup")
            except BaseException as error:
                failures.append("owned-child=" + repr(error))
            finally:
                if not self._kernel.CloseHandle(child["handle"]):
                    failures.append("owned-child-close=" + str(C.get_last_error()))
        if self._unowned is not None:
            try:
                if self._unowned.poll() is None:
                    # Exact Popen owner only; this control process was never a
                    # member of an OwnedService Windows job.
                    self._unowned.terminate()
                self._unowned.wait(timeout=8)
            except BaseException as error:
                failures.append("unowned-control=" + repr(error))
            for stream in (self._unowned.stdin, self._unowned.stdout, self._unowned.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except BaseException as error:
                    failures.append("unowned-stream=" + repr(error))
        if failures:
            self.fail("fixture cleanup remains unresolved: " + repr(failures))

    def _read_line(self, process, *, seconds):
        received = queue.Queue(maxsize=1)

        def read():
            try:
                received.put(("line", process.stdout.readline()))
            except BaseException as error:
                received.put(("error", error))

        thread = threading.Thread(target=read, name="outer-native-retirement-reader", daemon=True)
        thread.start()
        self._readers.append(thread)
        try:
            kind, value = received.get(timeout=seconds)
        except queue.Empty:
            self.fail("outer fixture did not publish readiness within bounded interval")
        if kind == "error":
            raise value
        if not value:
            stderr = process.stderr.read() if process.stderr is not None else ""
            self.fail("outer fixture ended before readiness: " + stderr)
        return value

    def _creation_time(self, handle):
        created, exited, kernel, user = (W.FILETIME() for _ in range(4))
        self.assertTrue(self._kernel.GetProcessTimes(
            handle, C.byref(created), C.byref(exited), C.byref(kernel), C.byref(user)))
        return (created.dwHighDateTime << 32) | created.dwLowDateTime

    def _wait_exact_exit(self, child, *, seconds=15):
        result = self._kernel.WaitForSingleObject(child["handle"], int(seconds * 1000))
        self.assertEqual(result, WAIT_OBJECT_0,
                         "exact duplicated owned child handle did not report termination")

    def test_actual_outer_exit_retires_exact_owned_children_preserves_pending_fence_and_spares_unowned_control(self):
        """Outer exit closes product job handles; pinned children prove the result."""
        environment = controlled_environment(self.root)
        # This is ordinary Popen, deliberately not WindowsOwnedProcess and not a
        # parent kill-on-close job. It cannot mask product-owned job behavior.
        self._unowned = subprocess.Popen(
            [sys.executable, "-B", "-I", "-c", "import time; time.sleep(60)"],
            cwd=str(ROOT), env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW, text=True)
        self._outer = subprocess.Popen(
            [sys.executable, "-B", "-I", "-c", OUTER, str(self.root), str(os.getpid()),
             str(ROOT / "src"), str(ROOT)],
            cwd=str(ROOT), env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW, text=True)

        message = json.loads(self._read_line(self._outer, seconds=25))
        self.assertEqual(message["state"], "READY", message)
        self.assertEqual(message["custody"]["state"], "PENDING")
        self.assertEqual(message["custody"]["publication_state"], "POSSIBLE_PUBLICATION")
        self.assertEqual(len(message["children"]), 2)
        self.assertEqual(len({entry["handle"] for entry in message["children"]}), 2)
        self.assertEqual(len({entry["pid"] for entry in message["children"]}), 2)
        expected_image = hashlib.sha256(Path(sys._base_executable).read_bytes()).hexdigest()
        for child in message["children"]:
            self.assertIsInstance(child["handle"], int)
            self.assertGreater(child["handle"], 0)
            self.assertEqual(self._kernel.GetProcessId(child["handle"]), child["pid"])
            self.assertEqual(self._creation_time(child["handle"]), child["creation_time"])
            self.assertEqual(self._kernel.WaitForSingleObject(child["handle"], 0), WAIT_TIMEOUT)
            self.assertEqual(child["image_sha256"], expected_image)
            self._pinned.append(child)
        self.assertIsNone(self._unowned.poll(), "unowned control failed before outer exit")

        self._outer.stdin.write("x")
        self._outer.stdin.flush()
        self._outer.stdin.close()
        self.assertEqual(self._outer.wait(timeout=15), OUTER_EXIT_CODE)

        restart = LauncherShutdownCustody(self.root)
        try:
            with self.assertRaises(LauncherCustodyIncomplete) as caught:
                restart.reserve_launch()
            self.assertEqual(caught.exception.record["state"], "PENDING")
            self.assertEqual(caught.exception.record["publication_state"], "POSSIBLE_PUBLICATION")
        finally:
            restart.close()
        for child in self._pinned:
            self._wait_exact_exit(child)
        self.assertIsNone(self._unowned.poll(),
                          "unowned control was affected by product-owned outer job retirement")


if __name__ == "__main__":
    unittest.main()
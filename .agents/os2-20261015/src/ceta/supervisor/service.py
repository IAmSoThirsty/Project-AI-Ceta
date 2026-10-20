"""Bounded control channels for trusted, job-owned development processes.

Only explicitly selected child ends are inherited. Native launch/control calls
still rely on ordinary Windows scheduling and driver behavior; no universal
kernel/driver time bound or same-account security isolation is established.
One caller owns each channel, with at most one submitted work command outstanding.
The authority request itself travels through the authenticated native transport.
"""
import ctypes as C
import os
from pathlib import Path
import sys
import threading

from ceta.contracts.kernel_transactions import require
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
from .windows_jobs import WindowsOwnedProcess

DWORD = C.c_uint32
BOOL = C.c_int32
HANDLE = C.c_void_p
MAX_CONTROL = 4096


class OwnedChannelError(ContractError):
    """A failed construction still exposes every retained native owner."""
    def __init__(self, code, channel, failure, cleanup_errors=()):
        super().__init__(code)
        self.owned_channel = channel
        self.owned_process = channel.process
        self.launch_error = channel._launch_error
        self.primary_error = failure
        self.cleanup_errors = tuple(cleanup_errors)

    def close_cleanup(self):
        self.owned_channel.close()


class _Attributes(C.Structure):
    _fields_ = [("length", DWORD), ("descriptor", C.c_void_p), ("inherit", BOOL)]


class _ControlApi:
    def __init__(self):
        require(sys.platform == "win32" and C.sizeof(HANDLE) == 8, "WINDOWS_X64_REQUIRED")
        library = C.WinDLL("kernel32.dll", use_last_error=True, winmode=0x800)
        p = C.POINTER
        for name, restype, args in (
            ("CreatePipe", BOOL, [p(HANDLE), p(HANDLE), p(_Attributes), DWORD]),
            ("SetHandleInformation", BOOL, [HANDLE, DWORD, DWORD]),
            ("PeekNamedPipe", BOOL, [HANDLE, C.c_void_p, DWORD, p(DWORD), p(DWORD), p(DWORD)]),
            ("ReadFile", BOOL, [HANDLE, C.c_void_p, DWORD, p(DWORD), C.c_void_p]),
            ("WriteFile", BOOL, [HANDLE, C.c_void_p, DWORD, p(DWORD), C.c_void_p]),
            ("CloseHandle", BOOL, [HANDLE]),
        ):
            function = getattr(library, name)
            function.restype, function.argtypes = restype, args
            setattr(self, name, function)

    def close(self, handle):
        if handle and not self.CloseHandle(handle):
            raise ContractError("CONTROL_HANDLE_CLOSE_FAILED")

    def pipe(self, *, child_reads):
        read, write = HANDLE(), HANDLE()
        attributes = _Attributes(C.sizeof(_Attributes), None, True)
        require(self.CreatePipe(C.byref(read), C.byref(write), C.byref(attributes), 65536),
                "CONTROL_PIPE_CREATE_FAILED")
        parent, child = (write.value, read.value) if child_reads else (read.value, write.value)
        if not self.SetHandleInformation(parent, 1, 0):
            error = ContractError("CONTROL_PARENT_INHERITANCE_DENIED")
            error.control_handles = []
            for handle in (read.value, write.value):
                try:
                    self.close(handle)
                except BaseException:
                    error.control_handles.append(handle)
            raise error
        return parent, child


def controlled_environment(temporary_root):
    """No inherited user PATH, Python hooks or credential environment."""
    system_root = os.environ.get("SystemRoot")
    require(type(system_root) is str and Path(system_root).is_absolute(), "SYSTEM_ROOT_REQUIRED")
    return {"SystemRoot": system_root, "WINDIR": system_root,
            "PATH": str(Path(system_root) / "System32"),
            "TEMP": str(temporary_root), "TMP": str(temporary_root),
            "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}


class OwnedChannel:
    """Process-lifetime observations and a tiny parent-selected control protocol."""
    def __init__(self, executable, arguments, *, cwd, environment):
        self._api = _ControlApi()
        self._input = self._output = self._error = None
        self._buffers = {"output": b"", "error": b""}
        self.diagnostic_bytes = b""
        self.process = None
        self._child_handles, self._launch_error = [], None
        self._process_closed, self._closed = False, False
        self._write_lock = threading.RLock()
        self._write_active = False
        failure = None
        try:
            self._input, child_input = self._api.pipe(child_reads=True); self._child_handles.append(child_input)
            self._output, child_output = self._api.pipe(child_reads=False); self._child_handles.append(child_output)
            self._error, child_error = self._api.pipe(child_reads=False); self._child_handles.append(child_error)
            self.process = WindowsOwnedProcess.launch(executable, arguments, cwd=cwd,
                environment=environment, standard_handles=(child_input, child_output, child_error))
        except BaseException as error:
            failure = error
            self.process = getattr(error, "owned_process", None)
            if callable(getattr(error, "close_cleanup", None)):
                self._launch_error = error
            self._child_handles.extend(getattr(error, "control_handles", ()))
        cleanup_errors = self._close_child_handles()
        if failure is not None and self.process is None:
            cleanup_errors.extend(self._close_parent_handles())
        if failure is not None or cleanup_errors:
            primary = failure if failure is not None else cleanup_errors[0]
            code = "CONTROL_LAUNCH_FAILED" if failure is not None else "CONTROL_LAUNCH_FINALIZATION_UNRESOLVED"
            raise OwnedChannelError(code, self, primary, cleanup_errors) from primary

    def _close_child_handles(self):
        errors = []
        for handle in tuple(self._child_handles):
            try:
                self._api.close(handle)
                self._child_handles.remove(handle)
            except BaseException as error:
                errors.append(error)
        return errors

    def _close_parent_handles(self):
        errors = []
        for name in ("_input", "_output", "_error"):
            try:
                self._api.close(getattr(self, name))
                setattr(self, name, None)
            except BaseException as error:
                errors.append(error)
        return errors

    def observed_exited(self):
        if self.process is None or self._process_closed or getattr(self.process, "lifetime_closed", False):
            return True
        return self.process.poll() is not None and self.process.active_process_count() == 0

    def terminate(self, exit_code=124):
        if (self.process is not None and not self._process_closed
                and not getattr(self.process, "lifetime_closed", False)):
            self.process.terminate(exit_code)

    def send(self, value):
        wire = canonical_bytes(value) + b"\n"
        require(len(wire) <= MAX_CONTROL, "CONTROL_MESSAGE_TOO_LARGE")
        with self._write_lock:
            require(not self._process_closed and not self._closed, "CONTROL_CHANNEL_CLOSED")
            require(not self._write_active, "CONTROL_WRITE_PENDING")
            self._write_active = True
            handle, process = self._input, self.process
        try:
            require(process.poll() is None, "CONTROL_PROCESS_EXITED")
            buffer, count = C.create_string_buffer(wire, len(wire)), DWORD()
            # The controller runs this synchronous native call in a retained
            # worker. Neither its state lock nor this lease lock spans the call.
            require(self._api.WriteFile(handle, buffer, len(wire), C.byref(count), None)
                    and count.value == len(wire), "CONTROL_WRITE_FAILED")
        finally:
            with self._write_lock:
                self._write_active = False

    def _read(self, name, handle):
        available = DWORD()
        if not self._api.PeekNamedPipe(handle, None, 0, None, C.byref(available), None):
            if C.get_last_error() == 109: return []
            raise ContractError("CONTROL_PEEK_FAILED")
        if available.value:
            size = min(available.value, MAX_CONTROL * 16)
            buffer, count = C.create_string_buffer(size), DWORD()
            require(self._api.ReadFile(handle, buffer, size, C.byref(count), None)
                    and 0 < count.value <= size, "CONTROL_READ_FAILED")
            self._buffers[name] += buffer.raw[:count.value]
        lines = []
        for _ in range(16):
            if b"\n" not in self._buffers[name]: break
            line, self._buffers[name] = self._buffers[name].split(b"\n", 1)
            require(len(line) <= MAX_CONTROL, "CONTROL_LINE_TOO_LARGE")
            if name == "output":
                value = strict_loads(line)
                require(type(value) is dict, "CONTROL_OBJECT_REQUIRED")
                lines.append(value)
            else:
                # Diagnostic bytes remain bounded and are never treated as data
                # or printed into the product's user-facing result.
                require(len(self.diagnostic_bytes) + len(line) + 1 <= 65536, "CONTROL_DIAGNOSTIC_CAPACITY")
                self.diagnostic_bytes += line + b"\n"
                lines.append({"event": "diagnostic", "bytes": len(line)})
        require(len(self._buffers[name]) <= MAX_CONTROL * 16, "CONTROL_BUFFER_EXHAUSTED")
        return lines

    def poll(self):
        if self._process_closed or self.process is None:
            return []
        return self._read("output", self._output) + self._read("error", self._error)

    def close(self):
        with self._write_lock:
            require(not self._write_active, "CONTROL_WRITE_PENDING")
            self._close_idle()

    def _close_idle(self):
        # close() rejects an unobserved primary/descendant lifetime; retain handles
        # for later polling rather than abandoning an in-flight process.
        if self._closed:
            return
        if not self._process_closed:
            if self.process is not None:
                self.process.close()
            self._process_closed = True
        errors = []
        if self._launch_error is not None:
            try:
                self._launch_error.close_cleanup()
                self._launch_error = None
            except BaseException as error:
                errors.append(error)
        errors.extend(self._close_child_handles())
        errors.extend(self._close_parent_handles())
        if errors:
            raise ContractError("CONTROL_CLEANUP_PENDING") from errors[0]
        self._closed = True

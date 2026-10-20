"""Bounded owned-child debug evidence. No native calls occur on import."""
from dataclasses import dataclass
from typing import Protocol
import hashlib
import threading
import time

EXCEPTION = 1
CREATE_THREAD = 2
CREATE_PROCESS = 3
EXIT_THREAD = 4
EXIT_PROCESS = 5
LOAD_DLL = 6
UNLOAD_DLL = 7
OUTPUT_DEBUG_STRING = 8
RIP = 9
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
BREAKPOINT = 0x80000003
DEBUG_ONLY_THIS_PROCESS = 0x00000002
BASE_AC7_FLAGS = 0x08080404


class CaptureError(RuntimeError):
    """The exact collector and owner remain attached when custody is pending."""


def retain(primary, *, capture=None, owner=None, secondary=None):
    data = BaseException.__dict__['__dict__'].__get__(primary)
    if capture is not None:
        dict.__setitem__(data, 'loader_capture', capture)
    if owner is not None:
        dict.__setitem__(data, 'owned_process', owner)
    if secondary is not None:
        prior = dict.get(data, 'loader_capture_secondary', ())
        if type(prior) is not tuple:
            prior = ()
        dict.__setitem__(data, 'loader_capture_secondary', prior + (secondary,))


def require(condition, reason):
    if not condition:
        raise CaptureError(reason)


@dataclass(frozen=True, slots=True)
class Limits:
    seconds: float = 15.0
    events: int = 1024
    debug_bytes: int = 1_048_576
    per_debug_string: int = 16_384
    stdio_bytes: int = 1_048_576

    def __post_init__(self):
        require(type(self.seconds) in (int, float) and 0 < self.seconds <= 30,
                'CAPTURE_DEADLINE_INVALID')
        for name, maximum in (('events', 4096), ('debug_bytes', 4_194_304),
                              ('per_debug_string', 65_535), ('stdio_bytes', 4_194_304)):
            value = getattr(self, name)
            require(type(value) is int and 0 < value <= maximum, 'CAPTURE_BOUND_INVALID:' + name)
        require(self.per_debug_string <= self.debug_bytes, 'CAPTURE_STRING_BOUND_EXCEEDS_TOTAL')


@dataclass(frozen=True, slots=True)
class OwnedIdentity:
    pid: int
    creation_time: int
    image_sha256: str

    def __post_init__(self):
        require(type(self.pid) is int and self.pid > 0, 'CAPTURE_PID_INVALID')
        require(type(self.creation_time) is int and self.creation_time > 0, 'CAPTURE_CREATION_INVALID')
        require(type(self.image_sha256) is str and len(self.image_sha256) == 64
                and all(c in '0123456789abcdef' for c in self.image_sha256), 'CAPTURE_IMAGE_PIN_INVALID')


@dataclass(frozen=True, slots=True)
class Event:
    code: int
    pid: int
    tid: int
    data: dict
    native_bytes: bytes


class DebugPort(Protocol):
    """Actual Win32 implementation is Win32DebugPort, not a fixture service."""
    def wait(self, milliseconds: int) -> bool: ...
    def current(self, debug_limit: int) -> Event: ...
    def continue_current(self, status: int) -> None: ...
    def read_stdio(self, limit: int) -> tuple[bytes, bytes]: ...
    def pending(self) -> dict: ...


class Collector:
    """Consumes only events belonging to one freshly created exact owner.

    Windows debugger process/thread event handles are OS-owned until their exit
    event is continued. The native port alone retires image/DLL file handles.
    This collector never attaches, opens a numeric PID, or infers a failed DLL.
    """
    def __init__(self, port: DebugPort, identity: OwnedIdentity, limits: Limits,
                 *, clock=time.monotonic, thread_id=threading.get_ident):
        require(type(identity) is OwnedIdentity and type(limits) is Limits, 'CAPTURE_TYPED_INPUT_REQUIRED')
        self.port, self.identity, self.limits = port, identity, limits
        self.clock, self.thread_id = clock, thread_id
        self.creator_thread = thread_id()
        self.events = []
        self.stdout = bytearray()
        self.stderr = bytearray()
        self.debug_count = 0
        self.initial_breakpoint_continued = False
        self.created = False
        self.exit_code = None
        self.exit_continued = False
        self.finished = False
        self.started = False
        self.failure = None

    def _thread(self):
        require(self.thread_id() == self.creator_thread, 'CAPTURE_CREATOR_THREAD_REQUIRED')

    def _drain_stdio(self):
        remaining = self.limits.stdio_bytes - len(self.stdout) - len(self.stderr)
        require(remaining > 0, 'CAPTURE_STDIO_BOUND_EXHAUSTED')
        output, errors = self.port.read_stdio(remaining)
        require(type(output) is bytes and type(errors) is bytes
                and len(output) + len(errors) <= remaining, 'CAPTURE_STDIO_RESPONSE_INVALID')
        self.stdout.extend(output)
        self.stderr.extend(errors)

    def run(self):
        self._thread()
        require(not self.started, 'CAPTURE_SINGLE_ATTEMPT_REQUIRED')
        self.started = True
        started = self.clock()
        deadline = started + self.limits.seconds
        try:
            while not self.exit_continued:
                self._thread()
                require(self.clock() < deadline, 'CAPTURE_DEADLINE_EXHAUSTED')
                require(len(self.events) < self.limits.events, 'CAPTURE_EVENT_BOUND_EXHAUSTED')
                self._drain_stdio()
                milliseconds = max(1, min(100, int((deadline - self.clock()) * 1000)))
                if not self.port.wait(milliseconds):
                    continue
                event = self.port.current(min(self.limits.per_debug_string,
                                              self.limits.debug_bytes - self.debug_count))
                require(type(event) is Event and event.pid == self.identity.pid
                        and type(event.tid) is int and event.tid > 0, 'CAPTURE_FOREIGN_EVENT')
                require(event.code in range(1, 10), 'CAPTURE_UNKNOWN_EVENT')
                if not self.created:
                    require(event.code == CREATE_PROCESS, 'CAPTURE_CREATE_EVENT_MISSING')
                status = DBG_CONTINUE
                if event.code == CREATE_PROCESS:
                    require(not self.created, 'CAPTURE_DUPLICATE_CREATE_EVENT')
                    require(event.data['creation_time'] == self.identity.creation_time,
                            'CAPTURE_CREATION_IDENTITY_MISMATCH')
                    require(event.data['pid_from_handle'] == self.identity.pid,
                            'CAPTURE_PROCESS_HANDLE_MISMATCH')
                    self.created = True
                elif event.code == EXCEPTION:
                    status = DBG_EXCEPTION_NOT_HANDLED
                    if event.data['exception_code'] == BREAKPOINT and event.data['first_chance'] is True \
                            and not self.initial_breakpoint_continued:
                        status = DBG_CONTINUE
                        self.initial_breakpoint_continued = True
                elif event.code == OUTPUT_DEBUG_STRING:
                    captured = event.data.get('captured_bytes', 0)
                    require(type(captured) is int and 0 <= captured <= self.limits.per_debug_string,
                            'CAPTURE_DEBUG_RESPONSE_INVALID')
                    self.debug_count += captured
                    require(self.debug_count <= self.limits.debug_bytes, 'CAPTURE_DEBUG_BOUND_EXHAUSTED')
                elif event.code == EXIT_PROCESS:
                    require(type(event.data['exit_code']) is int, 'CAPTURE_EXIT_STATUS_INVALID')
                    self.exit_code = event.data['exit_code']
                row = dict(index=len(self.events), elapsed_seconds=self.clock() - started,
                           event_code=event.code, pid=event.pid, tid=event.tid,
                           data=event.data, native_event_hex=event.native_bytes.hex(),
                           continue_status=status, continued=False)
                self.events.append(row)
                self.port.continue_current(status)
                row['continued'] = True
                if event.code == EXIT_PROCESS:
                    self.exit_continued = True
            drains=0
            while True:
                self._drain_stdio()
                eof=self.port.pending()['pipe_eof']
                require(type(eof) is list and len(eof)==2 and all(type(item) is bool for item in eof),
                        'CAPTURE_PIPE_EOF_OBSERVATION_INVALID')
                if all(eof):break
                drains+=1
                require(drains<4096 and self.clock()<deadline,'CAPTURE_STDIO_RETIREMENT_PENDING')
            self.finished = True
            return self.report()
        except BaseException as primary:
            self.failure = primary
            retain(primary, capture=self)
            raise

    def report(self):
        self._thread()
        return dict(identity=dict(pid=self.identity.pid, creation_time=self.identity.creation_time,
                                  image_sha256=self.identity.image_sha256),
                    events=self.events, native_exit_code=self.exit_code,
                    exit_event_continued=self.exit_continued, finished=self.finished,
                    initial_breakpoint_policy='Continue one first-chance breakpoint; pass other exceptions unhandled',
                    initial_breakpoint_continued=self.initial_breakpoint_continued,
                    debugger_changes_timing=True, failed_module=None, failure_attribution='UNKNOWN',
                    attribution_limit='Debug events and module order do not identify a failed DLL initializer.',
                    debug_bytes=self.debug_count, stdout_bytes=len(self.stdout), stderr_bytes=len(self.stderr),
                    stdout_sha256=hashlib.sha256(self.stdout).hexdigest(),
                    stderr_sha256=hashlib.sha256(self.stderr).hexdigest(),
                    native_pending=self.port.pending())

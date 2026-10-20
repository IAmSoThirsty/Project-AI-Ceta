"""Own the real kernel/store service and client in disposable Windows jobs.

This development composition opens only an explicitly selected fixture root.
The controller's retained request/result files are transport observations, not
another authority store. Unknown results remain available for reconciliation.
No normal profile, production entrypoint, model, resource effect or consent owner
is selected. Positive authority remains closed in the existing composition.
"""
import base64
from dataclasses import dataclass, replace
import hashlib
import math
from pathlib import Path
import re
import sys
import threading
import time
import uuid

from ceta.contracts.kernel_transactions import require
from ceta.contracts.events import StreamPosition
from ceta.contracts.local_ipc import decode_message, encode_message, OPERATIONS, SubmissionUncertain
from ceta.contracts.local_results import decode_response
from ceta.contracts.task_drafts import command_wire, decode_snapshot, validate_result
from ceta.contracts.task_meaning import decode_proposal
from ceta.contracts.editor_recovery import EDITOR_MUTATIONS, decode_editor_chunk, decode_editor_snapshot
from ceta.contracts.wire import ContractError, MAX_WIRE_BYTES, RecordCodec, canonical_bytes
from ceta.supervisor.service import OwnedChannel, controlled_environment

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class TerminationAttempt:
    number: int
    requested_at_ns: int
    outcome: str
    error_type: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class TerminationObservation:
    """Controller observations, never an effect-reconciliation receipt."""
    owner_ref: str
    owner_kind: str
    process_id: int | None
    process_creation_time: int | None
    image_sha256: str | None
    attempt_limit: int
    attempts: tuple[TerminationAttempt, ...] = ()
    request_in_progress: bool = False
    exit_observed: bool | None = None
    observed_at_ns: int | None = None
    observation_error_type: str | None = None
    observation_error_code: str | None = None
    cleanup_complete: bool = False
    cleanup_error_type: str | None = None
    cleanup_error_code: str | None = None


class _ShutdownSettlementWitness:
    """Opaque, process-local proof emitted only by its owning service.

    This is intentionally not a wire contract or a dataclass.  A public
    ``ShutdownObservation`` can describe an observed state but cannot mint
    this capability, and serializing it would sever the exact service/object
    identity that made the observation meaningful.
    """

    __slots__ = ("__service", "__seal", "__basis")

    def __init__(self, service, seal, basis):
        self.__service = service
        self.__seal = seal
        self.__basis = basis

    def __reduce__(self):
        raise TypeError("OWNED_SERVICE_SETTLEMENT_WITNESS_NOT_SERIALIZABLE")

    def __reduce_ex__(self, protocol):
        del protocol
        raise TypeError("OWNED_SERVICE_SETTLEMENT_WITNESS_NOT_SERIALIZABLE")

    def __copy__(self):
        raise TypeError("OWNED_SERVICE_SETTLEMENT_WITNESS_NOT_COPYABLE")

    def __deepcopy__(self, memo):
        del memo
        raise TypeError("OWNED_SERVICE_SETTLEMENT_WITNESS_NOT_COPYABLE")

    def __repr__(self):
        return "<OwnedService shutdown settlement witness>"


class OwnedService:
    _TERMINATION_ATTEMPT_LIMIT = 3

    def __init__(self, profile_root, codec, installation_scope_id, scopes, *, create=False,
                 startup_seconds=15.0, call_seconds=4.0, principal_id="operator:development", session_id=None):
        root = Path(profile_root)
        require(root.is_absolute() and root.is_dir()
                and root.resolve(strict=True).is_relative_to(ROOT / ".agents/fixtures"),
                "SERVICE_DEVELOPMENT_ROOT_REQUIRED")
        for path in (root, *root.parents):
            require(not path.is_symlink() and not path.is_junction(), "SERVICE_ROOT_LINK_REJECTED")
        require(type(codec) is RecordCodec and type(scopes) is tuple and 1 <= len(scopes) <= 8
                and len(set(scopes)) == len(scopes) and installation_scope_id in scopes,
                "SERVICE_CONFIGURATION_INVALID")
        require(type(create) is bool and type(startup_seconds) in (int, float)
                and 0 < startup_seconds <= 60 and type(call_seconds) in (int, float)
                and 0 < call_seconds <= 10, "SERVICE_TIMING_INVALID")
        self._root, self._codec, self._installation, self._scopes = root, codec, installation_scope_id, scopes
        self._create, self._startup_seconds, self._call_seconds = create, startup_seconds, call_seconds
        self._controller = root / ("controller-" + uuid.uuid4().hex)
        self._controller.mkdir(exist_ok=False)
        self._spool, self._temporary = self._controller / "requests", self._controller / "temporary"
        self._spool.mkdir(); self._temporary.mkdir()
        self._environment = controlled_environment(self._temporary)
        from ceta.contracts.store_transactions import identifier
        identifier(principal_id)
        if session_id is not None: identifier(session_id)
        # These logical bindings are trusted composition inputs. The request
        # envelope cannot register or select its own peer identity.
        self._principal, self._session = principal_id, session_id or "session:" + uuid.uuid4().hex
        self._pipe = r"\\.\pipe\CETA-" + uuid.uuid4().hex
        self._lock = threading.RLock()
        self._client = self._service = None
        self._client_ready = False
        self._generation = None
        self._state, self._detail, self._positions = "STOPPED", "Not started.", ()
        self._pending, self._last = None, None
        self._started_deadline = None
        self._closed_channels = set()
        self._launches_in_progress = 0
        self._service_launch_pending = False
        self._start_claimed = False
        self._launch_slots = set()
        self._workers = []
        self._send_task = None
        self._uncertain_task_request = None
        self._observed_task_snapshot = None
        self._observed_meaning_snapshot = None
        self._observed_editor_snapshot = None
        self._task_reconciliation_history = []
        # Each entry retains the exact process object as well as its channel.
        # Object identity cannot be recycled while this single-use owner lives.
        self._termination_owners = {}
        # An initial STOPPED state alone is never a terminal proof.  Track
        # publication independently so the pre-start case cannot be confused
        # with a failed or interrupted launch after native ownership began.
        self._native_owner_published = False
        self._shutdown_witness_seal = object()
        self._shutdown_settlement_witness = None
        self._shutdown_settlement_basis = None

    @property
    def termination_observations(self):
        with self._lock:
            return tuple(entry["observation"] for entry in self._termination_owners.values())

    def _invalidate_shutdown_witness(self):
        """Forget a pre-start observation before native publication can begin."""
        self._shutdown_settlement_witness = None
        self._shutdown_settlement_basis = None

    def _prestart_no_publication(self):
        """Whether this exact controller has never had an owned native launch."""
        return (not self._start_claimed and not self._native_owner_published
                and self._client is None and self._service is None
                and not self._workers and self._launches_in_progress == 0
                and not self._service_launch_pending and not self._launch_slots
                and not self._termination_owners and not self._closed_channels
                and self._pending is None and self._send_task is None
                and self._generation is None and getattr(self, "_unresolved_launch", None) is None)

    def _native_retirement_complete(self):
        """Require exact retained-owner exit and cleanup, independent of state text."""
        if (not self._start_claimed or not self._native_owner_published
                or self._state != "STOPPED" or self._workers
                or self._launches_in_progress != 0 or self._service_launch_pending
                or self._launch_slots or getattr(self, "_unresolved_launch", None) is not None
                or not self._termination_owners):
            return False
        return all(observation.exit_observed is True
                   and observation.cleanup_complete is True
                   and not observation.request_in_progress
                   for observation in (entry["observation"] for entry in self._termination_owners.values()))

    def shutdown_settlement_witness(self):
        """Return one opaque proof of actual native settlement, else ``None``.

        The result is a process-local capability only.  It exists for either
        the untouched pre-start controller (where no native owner could have
        been published) or a stopped controller whose complete retained native
        owner set has explicit exit and cleanup observations.  It makes no
        claim about task/effect reconciliation or durable application custody.
        """
        with self._lock:
            self._retire_workers()
            if self._prestart_no_publication():
                basis = "PRESTART_NO_PUBLICATION"
            elif self._native_retirement_complete():
                basis = "NATIVE_RETIREMENT_COMPLETE"
            else:
                return None
            if (self._shutdown_settlement_witness is None
                    or self._shutdown_settlement_basis != basis):
                self._shutdown_settlement_witness = _ShutdownSettlementWitness(
                    self, self._shutdown_witness_seal, basis)
                self._shutdown_settlement_basis = basis
            return self._shutdown_settlement_witness

    @staticmethod
    def _termination_error(error):
        try:
            name = type(error).__name__
            error_type = name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", name) else "ERROR_TYPE_REJECTED"
            if isinstance(error, ContractError):
                code = error.code
                if type(code) is not str or re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}(?::[0-9]{1,10})?", code) is None:
                    code = "SERVICE_TERMINATION_ERROR_CODE_REJECTED"
                return error_type, code
            if isinstance(error, OSError):
                number = error.errno
                code = ("OS_ERROR_" + str(number) if type(number) is int and -(2 ** 31) <= number < 2 ** 32
                        else "OS_ERROR")
                return error_type, code
            return error_type, None
        except BaseException:
            # A diagnostic accessor is not allowed to replace the initiating
            # exception or prevent the retained attempt from being finalized.
            return "ERROR_DIAGNOSTIC_UNAVAILABLE", None

    def _termination_entry(self, owner, kind):
        # Called with the controller lock. These are the captured native owners,
        # not selectors inferred from a process name, port or PID.
        process = getattr(owner, "process", owner)
        if process is None:
            return None
        key = id(process)
        entry = self._termination_owners.get(key)
        if entry is None:
            pid, created = getattr(process, "pid", None), getattr(process, "creation_time", None)
            image = getattr(process, "image_sha256", None)
            observed = TerminationObservation(
                "termination-owner:" + uuid.uuid4().hex, kind,
                pid if type(pid) is int and pid > 0 else None,
                created if type(created) is int and created > 0 else None,
                image if type(image) is str and re.fullmatch(r"[0-9a-fA-F]{64}", image) else None,
                self._TERMINATION_ATTEMPT_LIMIT)
            entry = {"process": process, "owner": owner, "observation": observed}
            self._termination_owners[key] = entry
        return entry

    def _request_termination(self, owner, kind):
        with self._lock:
            entry = self._termination_entry(owner, kind)
            if entry is None:
                return None
            observed = entry["observation"]
            if getattr(entry["process"], "lifetime_closed", False):
                # Native close requires prior primary-exit and empty-job
                # observation; residual channel/startup cleanup remains separate.
                entry["observation"] = replace(observed, exit_observed=True, observed_at_ns=time.time_ns())
                return None
            if observed.cleanup_complete or observed.exit_observed is True or observed.request_in_progress:
                return None
            if len(observed.attempts) >= observed.attempt_limit:
                self._detail = "Owned termination retry limit reached; ownership is retained."
                return None
            attempt = TerminationAttempt(len(observed.attempts) + 1, time.time_ns(), "REQUESTING")
            entry["observation"] = replace(observed, attempts=observed.attempts + (attempt,),
                                           request_in_progress=True)
        failure = None
        try:
            # One explicit Stop requests at most one attempt for each owner.
            # No controller lock spans the native termination call.
            owner.terminate(124)
        except BaseException as error:
            failure = error
        finally:
            with self._lock:
                current = entry["observation"]
                if failure is None:
                    completed = replace(attempt, outcome="REQUESTED")
                else:
                    error_type, error_code = self._termination_error(failure)
                    completed = replace(attempt, outcome="FAILED" if isinstance(failure, Exception)
                                        else "INTERRUPTED", error_type=error_type, error_code=error_code)
                    self._detail = "Owned termination remains pending; ownership is retained."
                entry["observation"] = replace(current, attempts=current.attempts[:-1] + (completed,),
                                               request_in_progress=False)
        # Concrete native failures remain visible and retryable. Preserve an
        # interruption/unexpected exception after servicing all other owners.
        return failure if failure is not None and not isinstance(failure, (ContractError, OSError)) else None

    def _observe_termination(self, owner, kind, *, exited=None, error=None,
                             cleanup_complete=None, cleanup_error=None):
        with self._lock:
            entry = self._termination_entry(owner, kind)
            if entry is None:
                return
            updates = {"observed_at_ns": time.time_ns()}
            if error is not None:
                error_type, error_code = self._termination_error(error)
                updates.update(exit_observed=None, observation_error_type=error_type,
                               observation_error_code=error_code)
            elif exited is not None:
                updates.update(exit_observed=exited, observation_error_type=None, observation_error_code=None)
            if cleanup_complete is not None:
                updates.update(cleanup_complete=cleanup_complete, cleanup_error_type=None, cleanup_error_code=None)
            if cleanup_error is not None:
                error_type, error_code = self._termination_error(cleanup_error)
                updates.update(cleanup_complete=False, cleanup_error_type=error_type, cleanup_error_code=error_code)
            entry["observation"] = replace(entry["observation"], **updates)

    def _reserve_worker(self, kind, **bindings):
        # Called under the controller lock, before a thread can be published.
        task = dict(kind=kind, thread=None, done=False, launch_uncertain=False, **bindings)
        self._workers.append(task)
        return task

    def _worker_failed(self, task):
        # Called under the controller lock. A received result has stronger
        # evidence than a later local transport failure for the same attempt.
        if task["kind"] == "send":
            if self._send_task is not task or self._pending is not task["pending"]:
                return
            self._last = {"attempt": task["attempt"], "kind": "TRANSPORT_UNCERTAIN"}
            if self._state not in {"STOPPING", "STOPPED"}:
                self._state, self._detail = "RECOVERING", "Dispatch result uncertain; exact request retained; inspect preservation before retrying."
        elif self._state not in {"STOPPING", "STOPPED"}:
            self._state, self._detail = "RECOVERING", "Startup failed; cleanup ownership retained."

    def _start_worker(self, task, operation):
        def running():
            try:
                operation()
            except BaseException:
                with self._lock:
                    self._worker_failed(task)
            finally:
                with self._lock:
                    if task["kind"] == "launch_service":
                        self._service_launch_pending = False
                    task["done"] = True
        try:
            thread = threading.Thread(target=running, name="ceta-owned-" + task["kind"], daemon=True)
            with self._lock:
                task["thread"] = thread
            thread.start()
        except BaseException as error:
            with self._lock:
                # Only construction failure proves this worker was not offered
                # to start(). Every start exception can precede an observable
                # bootstrap; neither its class nor a missing ident proves that
                # the target cannot subsequently run.
                absent = task["thread"] is None
                if absent:
                    task["done"] = True
                    if task["kind"] == "launch_service":
                        self._service_launch_pending = False
                else:
                    task["launch_uncertain"] = True
                self._worker_failed(task)
            if task["kind"] == "send":
                raise SubmissionUncertain(task["attempt"]) from error
            if not isinstance(error, Exception):
                raise
            raise ContractError("SERVICE_BACKGROUND_START_FAILED") from error

    def _retire_workers(self):
        # A finally flag is not a thread-exit observation. Never join live work
        # while holding the controller lock or occupying the Qt callback.
        for task in tuple(self._workers):
            thread = task["thread"]
            if task["done"] and (thread is None or not thread.is_alive()):
                self._workers.remove(task)
                if self._send_task is task:
                    self._send_task = None

    @property
    def state(self):
        with self._lock:
            return self._state

    @property
    def generation(self):
        with self._lock:
            return self._generation

    def start(self):
        with self._lock:
            require(not self._start_claimed and self._state == "STOPPED"
                    and self._client is None and self._service is None,
                    "SERVICE_ALREADY_STARTED_OR_OWNERSHIP_RETAINED")
            # A stopped instance is never restarted. A new controller instance
            # selects a fresh native generation only after previous ownership is
            # settled. This also rejects an older start before its launch seam.
            self._invalidate_shutdown_witness()
            self._start_claimed = True
            self._state, self._detail = "STARTING", "Starting owned client; authority remains closed."
            self._started_deadline = time.monotonic() + self._startup_seconds
            task = self._reserve_worker("launch_client")
        self._start_worker(task, lambda: self._launch_owned("_client",
            ("-I", "-B", "-X", "utf8", str(ROOT / "src/ceta/composition/client_process.py"), str(self._spool))))
        return self.snapshot()

    def _launch_owned(self, slot, arguments):
        with self._lock:
            require(self._state == "STARTING" and getattr(self, slot) is None
                    and slot not in self._launch_slots,
                    "SERVICE_LAUNCH_CANCELLED_OR_OWNER_RETAINED")
            self._launch_slots.add(slot)
            self._launches_in_progress += 1
        channel, failure = None, None
        try:
            # No controller lock spans native launch. A concurrent STOP disables
            # dispatch and waits for this explicit publication obligation.
            channel = OwnedChannel(sys._base_executable, arguments,
                                   cwd=str(ROOT), environment=self._environment)
        except BaseException as error:
            failure = error
            channel = getattr(error, "owned_channel", None)
        with self._lock:
            if channel is not None:
                setattr(self, slot, channel)
                self._native_owner_published = True
            elif failure is not None:
                # Compatibility for an owner-bearing launch seam: retain the
                # complete cleanup interface, including residual startup handles.
                if callable(getattr(failure, "close_cleanup", None)):
                    self._unresolved_launch = failure
                if getattr(failure, "owned_process", None) is not None:
                    self._native_owner_published = True
            self._launches_in_progress -= 1
            self._launch_slots.remove(slot)
            stopping = self._state == "STOPPING"
            if failure is not None and self._state not in {"STOPPING", "STOPPED"}:
                self._state, self._detail = "RECOVERING", "Startup failed; cleanup ownership retained."
        if stopping:
            # This includes an owner published after the first termination pass.
            self.request_stop("reason:late-launch-stop")
        if failure is not None:
            raise failure
        return channel

    def _launch_service(self):
        client = self._client.process
        config = {"profile": "ceta-owned-service-v1", "root": str(self._root),
            "installation": self._installation, "scopes": list(self._scopes), "create": self._create,
            "pipe": self._pipe, "client_pid": client.pid, "client_creation": client.creation_time,
            "client_image": client.image_sha256, "principal": self._principal, "session": self._session}
        argument = base64.b64encode(canonical_bytes(config)).decode("ascii")
        self._launch_owned("_service",
            ("-I", "-B", "-X", "utf8", str(ROOT / "src/ceta/composition/service_process.py"), argument))
        with self._lock:
            if self._state == "STARTING":
                self._detail = "Inspecting preserved store and authenticating the owned client."

    def begin_call(self, record_wire, operation, *, reason_ref=None):
        with self._lock:
            require(self._state in {"READY", "RECOVERING"} and self._generation is not None
                    and self._pending is None and self._send_task is None, "SERVICE_NOT_READY_OR_CALL_PENDING")
            require(self._state == "READY" or operation in {"kernel.recover_permit", "kernel.resolve_consumption", "kernel.recover_preparation", "task.load", "task.list", "task.meaning_load", "task.editor_load"},
                    "SERVICE_RECONCILIATION_REQUIRED")
            if operation in {"task.create", "task.save", "task.meaning_propose"} or operation in EDITOR_MUTATIONS:
                require(self._uncertain_task_request is None, "SERVICE_TASK_RECONCILIATION_REQUIRED")
                require(len(self._task_reconciliation_history) < 256, "SERVICE_TASK_RECONCILIATION_CAPACITY")
            require(self._service.process.poll() is None and self._client.process.poll() is None,
                    "SERVICE_OWNED_PROCESS_NOT_LIVE")
            attempt = uuid.uuid4().hex
            now = time.time_ns() // 1_000_000
            wire = encode_message(record_wire, self._codec, message_id="message:" + attempt,
                correlation_ref="attempt:" + attempt, sender_session=self._session,
                receiver_generation=self._generation, operation=operation, issued_at_ms=now,
                expires_at_ms=now + 10000, reason_ref=reason_ref)
            request = decode_message(wire, self._codec)
            require(request.scope_id in self._scopes, "SERVICE_SCOPE_DENIED")
            path = self._spool / (attempt + ".request.json")
            # Retain original bytes before publishing background preservation.
            # A return reserves an attempt; it does not acknowledge disk or IPC.
            self._pending = {"attempt": attempt, "request": request,
                "prior_recovering": self._state == "RECOVERING",
                "deadline": time.monotonic() + self._call_seconds + 1.0, "request_path": str(path), "request_wire": wire}
            if operation in {"task.create", "task.save", "task.meaning_propose"} or operation in EDITOR_MUTATIONS:
                self._uncertain_task_request = request
                self._observed_task_snapshot = None
                self._observed_meaning_snapshot = None
                self._observed_editor_snapshot = None
            self._last = None
            self._state, self._detail = "ACTIVE", "Awaiting the authenticated service result."
            selected = self._service.process
            command = {"profile": "ceta-owned-call-v1", "attempt": attempt,
                    "request_sha256": hashlib.sha256(wire).hexdigest(), "pipe": self._pipe,
                    "server_pid": selected.pid, "server_creation": selected.creation_time,
                    "server_image": selected.image_sha256, "timeout_ms": math.ceil(self._call_seconds * 1000)}
            task = self._reserve_worker("send", attempt=attempt, pending=self._pending,
                                        client=self._client, command=command, admitted=False)
            self._send_task = task
        self._start_worker(task, lambda: self._send_call(task))
        return attempt

    def _editor_scope(self, task_id, scope_id):
        from ceta.contracts.store_transactions import identifier
        identifier(task_id)
        with self._lock:
            if scope_id is not None:
                identifier(scope_id)
                require(scope_id in self._scopes, "SERVICE_SCOPE_DENIED")
                return scope_id
            observed = ((self._observed_task_snapshot, 3), (self._observed_meaning_snapshot, 4),
                        (self._observed_editor_snapshot, 4))
            scopes = {entry[index] for entry, index in observed if entry is not None and entry[0] == task_id}
            if not scopes and len(self._scopes) == 1:
                return self._scopes[0]
            require(len(scopes) == 1, "SERVICE_EDITOR_SCOPE_REQUIRED")
            return next(iter(scopes))

    def retain_editor(self, task_id, payload_wire, expected_revision, *, scope_id=None,
                      capture_commitment=None, chunk_index=None, chunk_wire=None):
        """Reserve raw-custody submission; observe its TaskResult through poll."""
        scope = self._editor_scope(task_id, scope_id)
        wire = command_wire("editor_retain", scope, "task-command:" + uuid.uuid4().hex,
            task_id=task_id, editor_payload=payload_wire, editor_expected_revision=expected_revision,
            editor_capture_commitment=capture_commitment, editor_chunk_index=chunk_index,
            editor_chunk=chunk_wire)
        return self.begin_call(wire, "task.editor_retain")

    def load_editor(self, task_id, *, scope_id=None, expected_revision=None,
                    capture_commitment=None, chunk_index=None):
        scope = self._editor_scope(task_id, scope_id)
        wire = command_wire("editor_load", scope, "task-command:" + uuid.uuid4().hex, task_id=task_id,
            editor_expected_revision=expected_revision, editor_capture_commitment=capture_commitment,
            editor_chunk_index=chunk_index)
        return self.begin_call(wire, "task.editor_load")

    def discard_editor(self, task_id, expected_revision, *, scope_id=None):
        """Explicit authenticated discard only; no window-destruction caller."""
        scope = self._editor_scope(task_id, scope_id)
        wire = command_wire("editor_discard", scope, "task-command:" + uuid.uuid4().hex,
            task_id=task_id, editor_expected_revision=expected_revision)
        return self.begin_call(wire, "task.editor_discard")

    def _send_call(self, task):
        # File I/O is owned background work too. It must finish successfully
        # before control dispatch; neither the GUI nor the Stop lock waits here.
        path = Path(task["pending"]["request_path"])
        # The logical path was bounded when this owned attempt was created.
        # Extended spelling changes only native I/O, not custody or admission.
        io_path = Path("\\\\?\\" + str(path)) if sys.platform == "win32" else path
        with io_path.open("xb") as stream:
            stream.write(task["pending"]["request_wire"])
        with self._lock:
            if (self._send_task is not task or self._pending is not task["pending"]
                    or self._state in {"STOPPING", "STOPPED"}):
                self._worker_failed(task)
                return
            expired = time.monotonic() >= task["pending"]["deadline"]
            if not expired:
                # This bounded claim is logical dispatch admission, not proof
                # that physical WriteFile entry precedes a concurrent Stop.
                task["admitted"] = True
        if expired:
            with self._lock:
                self._worker_failed(task)
            self.request_stop("reason:dispatch-timeout")
            return
        # Exact captured channel/lifetime/command; no lock spans native I/O.
        # A concurrent Stop terminates these owned jobs and retains this task
        # until the actual thread exits. It cannot cancel a prior kernel COMMIT.
        task["client"].send(task["command"])

    def request_stop(self, reason_ref="reason:operator-stop"):
        require(type(reason_ref) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}", reason_ref),
                "SERVICE_STOP_REASON_REQUIRED")
        with self._lock:
            # Host dispatch is disabled here before any termination request.
            # This is not a claim that a kernel COMMIT already in flight lost a
            # race; such work remains unresolved until store/effect observation.
            if self._state == "STOPPED" and self._launches_in_progress == 0 and not self._workers:
                return self.snapshot()
            self._state, self._detail = "STOPPING", "Dispatch disabled; owned termination requested."
            if any(task["launch_uncertain"] and not task["done"] for task in self._workers):
                self._detail = "Dispatch disabled; worker launch remains unobserved; ownership retained."
            targets = [(channel, kind) for channel, kind in
                       ((self._client, "CLIENT_CHANNEL"), (self._service, "SERVICE_CHANNEL"))
                       if channel is not None]
            unresolved = getattr(self, "_unresolved_launch", None)
            owner = None if unresolved is None else getattr(unresolved, "owned_process", None)
            if owner is not None:
                targets.append((owner, "LAUNCH_PROCESS"))
        primary = None
        seen = set()
        for owner, kind in targets:
            try:
                process = getattr(owner, "process", owner)
                if process is None or id(process) in seen:
                    continue
                seen.add(id(process))
                failure = self._request_termination(owner, kind)
            except BaseException as error:
                failure = error
            if failure is not None and primary is None:
                primary = failure
        if primary is not None:
            raise primary
        return self.snapshot()

    def _client_event(self, value):
        event = value.get("event")
        if event == "ready":
            require(set(value) == {"event", "pid"} and value["pid"] == self._client.process.pid
                    and not self._client_ready, "SERVICE_CLIENT_READY_BINDING")
            self._client_ready = True
            return
        if event == "diagnostic":
            self._detail = "Owned client reported a diagnostic; result is not established."
            return
        require(self._pending is not None and value.get("attempt") == self._pending["attempt"],
                "SERVICE_CALL_BINDING")
        attempt = self._pending["attempt"]
        if event == "call_result":
            require(set(value) == {"event", "attempt", "response_sha256"}, "SERVICE_RESULT_FIELDS")
            path = self._spool / (attempt + ".response.json")
            io_path = Path("\\\\?\\" + str(path)) if sys.platform == "win32" else path
            require(not io_path.is_symlink() and not io_path.is_junction(), "SERVICE_RESULT_LINK_REJECTED")
            with io_path.open("rb") as stream: wire = stream.read(MAX_WIRE_BYTES + 1)
            require(hashlib.sha256(wire).hexdigest() == value["response_sha256"], "SERVICE_RESULT_FILE_BINDING")
            response = decode_response(wire, self._pending["request"], self._codec)
            pending = self._pending
            request = pending["request"]
            if request.operation in {"task.create", "task.save", "task.meaning_propose"} and response.kind != "DENIED_RECONCILE":
                self._uncertain_task_request = None
            if request.operation in EDITOR_MUTATIONS and response.kind != "DENIED_RECONCILE":
                require(self._uncertain_task_request == request, "SERVICE_EDITOR_REQUEST_CUSTODY")
                self._uncertain_task_request = None
            if request.operation == "task.editor_load" and response.task_result is not None:
                result = response.task_result
                revision = validate_result(result, request.record, request.operation)
                if result.kind == "TASK_EDITOR_CHUNK":
                    # A chunk is a bounded raw-custody read. It is not a
                    # recovery projection and must never replace its observed
                    # revision/state used for reconciliation.
                    decode_editor_chunk(result.snapshot_wire)
                    editor = None
                else:
                    editor = None if result.kind == "TASK_EDITOR_ABSENT" else decode_editor_snapshot(result.snapshot_wire)
                    self._observed_editor_snapshot = (request.record.as_dict()["task_id"], revision,
                        result.current_task_revision, response.original_response, request.scope_id,
                        "ABSENT" if editor is None else editor["state"])
                uncertain = self._uncertain_task_request
                if (editor is not None and uncertain is not None and uncertain.operation in EDITOR_MUTATIONS
                    and uncertain.scope_id == editor["scope_id"]
                    and uncertain.record.as_dict()["task_id"] == editor["task_id"]
                    and editor["request_id"] == uncertain.record.record_id
                    and editor["request_commitment"] == uncertain.record.commitment):
                    require((editor["state"] == "RETAINED") == (uncertain.operation == "task.editor_retain"),
                            "SERVICE_EDITOR_RECOVERY_KIND")
                    require(len(self._task_reconciliation_history) < 256, "SERVICE_TASK_RECONCILIATION_CAPACITY")
                    self._task_reconciliation_history.append((uncertain.original_message, response.original_response,
                        "EXACT_EDITOR_CUSTODY_OBSERVED"))
                    self._uncertain_task_request = None
                    pending["prior_recovering"] = False
            if request.operation == "task.meaning_load" and response.task_result is not None:
                result = response.task_result
                revision = validate_result(result, request.record, request.operation)
                proposal = None if result.kind == "TASK_MEANING_ABSENT" else decode_proposal(result.snapshot_wire)
                self._observed_meaning_snapshot = (request.record.as_dict()["task_id"], revision,
                    result.current_task_revision, response.original_response, request.scope_id,
                    "ABSENT" if proposal is None else "PRESENT")
                uncertain = self._uncertain_task_request
                if (proposal is not None and uncertain is not None and uncertain.operation == "task.meaning_propose"
                    and uncertain.scope_id == proposal["scope_id"]
                    and uncertain.record.as_dict()["task_id"] == proposal["task_id"]
                    and proposal["request_id"] == uncertain.record.record_id and proposal["request_commitment"] == uncertain.record.commitment):
                    require(len(self._task_reconciliation_history) < 256, "SERVICE_TASK_RECONCILIATION_CAPACITY")
                    self._task_reconciliation_history.append((uncertain.original_message, response.original_response,
                        "EXACT_MEANING_PROPOSAL_OBSERVED"))
                    self._uncertain_task_request = None; pending["prior_recovering"] = False
            if request.operation == "task.load" and response.task_result is not None:
                revision = validate_result(response.task_result, request.record, request.operation)
                snapshot = None if response.task_result.kind == "TASK_ABSENT" else decode_snapshot(response.task_result.snapshot_wire)
                self._observed_task_snapshot = (request.record.as_dict()["task_id"], revision, response.original_response,
                    request.scope_id, "ABSENT" if snapshot is None else "PRESENT")
                uncertain = self._uncertain_task_request
                if (snapshot is not None and uncertain is not None and uncertain.operation in {"task.create", "task.save"}
                        and uncertain.record.as_dict()["task_id"] == snapshot["task_id"]
                        and uncertain.scope_id == snapshot["scope_id"]
                        and snapshot["request_id"] == uncertain.record.record_id
                        and snapshot["request_commitment"] == uncertain.record.commitment):
                    require(len(self._task_reconciliation_history) < 256, "SERVICE_TASK_RECONCILIATION_CAPACITY")
                    self._task_reconciliation_history.append((uncertain.original_message, response.original_response,
                        "EXACT_TASK_WRITE_OBSERVED"))
                    self._uncertain_task_request = None
                    pending["prior_recovering"] = False
            self._last = {"attempt": attempt, "kind": response.kind, "response": response}
            self._pending = None
            if self._state not in {"STOPPING", "STOPPED"}:
                task_read_recovering = (request.operation in {"task.load", "task.list", "task.meaning_load", "task.editor_load"}
                                       and pending.get("prior_recovering", False))
                self._state = "RECOVERING" if (response.kind == "DENIED_RECONCILE" or task_read_recovering
                    or self._uncertain_task_request is not None) else "READY"
                self._detail = "Service result observed; effect authority remains closed." if response.kind != "DENIED_RECONCILE" \
                    else "Service denial observed; possible committed state requires reconciliation."
                if self._state == "RECOVERING" and response.kind != "DENIED_RECONCILE":
                    self._detail = "Current data observed; original uncertain work still requires reconciliation."
        elif event == "call_uncertain":
            require(set(value) == {"event", "attempt", "code"}, "SERVICE_RESULT_FIELDS")
            self._last = {"attempt": attempt, "kind": "TRANSPORT_UNCERTAIN", "error_code": value["code"]}
            self._pending = None
            if self._state not in {"STOPPING", "STOPPED"}:
                self._state, self._detail = "RECOVERING", "Transport result uncertain; no retry or refund."
        else: require(False, "SERVICE_CLIENT_EVENT_UNAVAILABLE")

    def _service_event(self, value):
        event = value.get("event")
        if event == "ready":
            require(set(value) == {"event", "pid", "generation", "positions", "authority"}
                    and value["pid"] == self._service.process.pid and self._generation is None
                    and value["authority"] == "CLOSED" and type(value["generation"]) is str
                    and re.fullmatch(r"[0-9a-f]{64}", value["generation"]), "SERVICE_READY_BINDING")
            positions = value["positions"]
            require(type(positions) is list and len(positions) == len(self._scopes), "SERVICE_READY_POSITIONS")
            accepted = []
            for position in positions:
                require(type(position) is dict and set(position) == {"scope_id", "next_sequence", "head"},
                        "SERVICE_READY_POSITIONS")
                accepted.append(StreamPosition(**position))
            require(tuple(position.scope_id for position in accepted) == self._scopes,
                    "SERVICE_READY_SCOPE_BINDING")
            self._generation, self._positions = value["generation"], tuple(dict(position) for position in positions)
            if self._state == "STARTING":
                self._state, self._detail = "READY", "Store inspected; authenticated service available; effect authority closed."
        elif event in {"startup_denied", "transport_denied", "diagnostic"}:
            if event == "startup_denied" and self._state not in {"STOPPING", "STOPPED"}:
                self._state = "RECOVERING"
            self._detail = "Service denied startup/transport or reported a diagnostic; no completed effect."
        else: require(False, "SERVICE_EVENT_UNAVAILABLE")

    def poll(self):
        with self._lock:
            self._retire_workers()
            observed_channels = ((self._client, self._client_event), (self._service, self._service_event))
        for channel, handle in observed_channels:
            if channel is not None and id(channel) not in self._closed_channels:
                try:
                    for value in channel.poll():
                        with self._lock:
                            handle(value)
                except (ContractError, OSError):
                    with self._lock:
                        if self._state not in {"STOPPING", "STOPPED"}:
                            self._state = "RECOVERING"
                        self._detail = "Control/result evidence unavailable; ownership and drafts preserved."
        with self._lock:
            launch_service = (self._state == "STARTING" and self._client_ready
                              and self._service is None and not self._service_launch_pending)
            if launch_service:
                self._service_launch_pending = True
                task = self._reserve_worker("launch_service")
        if launch_service:
            try:
                self._start_worker(task, self._launch_service)
            except (ContractError, OSError):
                with self._lock:
                    if self._state not in {"STOPPING", "STOPPED"}:
                        self._state = "RECOVERING"
                    self._detail = "Service startup failed; ownership and preserved state retained."
        with self._lock:
            startup_expired = self._state == "STARTING" and time.monotonic() >= self._started_deadline
            call_expired = (self._pending is not None and time.monotonic() >= self._pending["deadline"]
                            and self._state not in {"STOPPING", "STOPPED"})
            if call_expired:
                self._last = {"attempt": self._pending["attempt"], "kind": "TRANSPORT_UNCERTAIN"}
        if startup_expired:
            self.request_stop("reason:startup-timeout")
        if call_expired:
            self.request_stop("reason:call-timeout")
        with self._lock:
            channels = tuple((channel, kind) for channel, kind in
                             ((self._client, "CLIENT_CHANNEL"), (self._service, "SERVICE_CHANNEL"))
                             if channel is not None)
            primary = None
            if self._state == "STOPPING":
                self._retire_workers()
                stopped = not self._workers and self._launches_in_progress == 0 and not self._service_launch_pending
                for channel, kind in channels:
                    if id(channel) in self._closed_channels: continue
                    entry = self._termination_entry(channel, kind)
                    if self._workers or (entry is not None and entry["observation"].request_in_progress):
                        stopped = False
                        continue
                    try:
                        exited = channel.observed_exited()
                        require(type(exited) is bool, "SERVICE_TERMINATION_OBSERVATION_INVALID")
                        self._observe_termination(channel, kind, exited=exited)
                    except BaseException as error:
                        self._observe_termination(channel, kind, error=error)
                        stopped = False
                        exited = False
                        if not isinstance(error, (ContractError, OSError)) and primary is None:
                            primary = error
                    if exited:
                        try:
                            channel.close(); self._closed_channels.add(id(channel))
                            self._observe_termination(channel, kind, cleanup_complete=True)
                        except BaseException as error:
                            self._observe_termination(channel, kind, cleanup_error=error)
                            stopped = False
                            if not isinstance(error, (ContractError, OSError)) and primary is None:
                                primary = error
                    else:
                        stopped = False
                    if not stopped:
                        self._detail = "Owned cleanup remains pending; residual handles retained."
                unresolved = getattr(self, "_unresolved_launch", None)
                if unresolved is not None and not self._workers:
                    owner = getattr(unresolved, "owned_process", None)
                    entry = None if owner is None else self._termination_entry(owner, "LAUNCH_PROCESS")
                    observing = True
                    try:
                        if entry is not None and entry["observation"].request_in_progress:
                            stopped = False
                        else:
                            exited = (owner is None or getattr(owner, "lifetime_closed", False)
                                      or (owner.poll() is not None and owner.active_process_count() == 0))
                            if owner is not None:
                                self._observe_termination(owner, "LAUNCH_PROCESS", exited=bool(exited))
                            if exited:
                                observing = False
                                unresolved.close_cleanup(); del self._unresolved_launch
                                if owner is not None:
                                    self._observe_termination(owner, "LAUNCH_PROCESS", cleanup_complete=True)
                            else:
                                stopped = False
                    except BaseException as error:
                        if owner is not None:
                            if observing:
                                self._observe_termination(owner, "LAUNCH_PROCESS", error=error)
                            else:
                                self._observe_termination(owner, "LAUNCH_PROCESS", cleanup_error=error)
                        stopped = False
                        if not isinstance(error, (ContractError, OSError)) and primary is None:
                            primary = error
                if not stopped and any(len(entry["observation"].attempts) >= entry["observation"].attempt_limit
                                       and entry["observation"].exit_observed is not True
                                       for entry in self._termination_owners.values()):
                    self._detail = "Owned termination retry limit reached; ownership is retained."
                if stopped:
                    if self._pending is not None:
                        self._last = {"attempt": self._pending["attempt"], "kind": "TRANSPORT_UNCERTAIN"}
                        # Keep exact bytes after shutdown too: failed worker
                        # start/preservation may never have created a disk file.
                        # This single-use controller cannot dispatch again.
                    self._state, self._detail = "STOPPED", "Owned processes and job members exited; command/effect reconciliation remains separate."
            elif self._state not in {"STOPPED", "RECOVERING"}:
                if any(c.observed_exited() for c, _ in channels):
                    self._state, self._detail = "RECOVERING", "Owned process exit observed; uncertain work is preserved."
        if primary is not None:
            raise primary
        return self.snapshot()

    def snapshot(self):
        with self._lock:
            return {"state": self._state, "detail": self._detail, "generation": self._generation,
                    "positions": self._positions, "call": self._last, "authority": "CLOSED",
                    "pending_attempt": None if self._pending is None else self._pending["attempt"]}

    def acknowledge_task_reconciliation(self, task_id, revision):
        """Explicit local task edit decision; never settles kernel/effect uncertainty.

        Only an actually decoded task.load result can select the next CAS basis.
        The original request and current response remain retained, without a
        claim about an earlier write that a newer revision may have superseded.
        """
        with self._lock:
            observed = self._observed_task_snapshot
            require(self._pending is None and self._state in {"READY", "RECOVERING"}
                    and observed is not None and observed[:2] == (task_id, revision), "SERVICE_TASK_OBSERVATION_REQUIRED")
            if self._state == "RECOVERING":
                uncertain = self._uncertain_task_request
                require(uncertain is not None and uncertain.record.as_dict()["task_id"] == task_id,
                        "SERVICE_TASK_RECONCILIATION_NOT_MATCHED")
                require(uncertain.scope_id == observed[3], "SERVICE_TASK_RECONCILIATION_SCOPE")
                # Selecting a raw task basis cannot settle a different semantic
                # write. It can let the view catch up before meaning recovery.
                if uncertain.operation == "task.meaning_propose" or uncertain.operation in EDITOR_MUTATIONS: return
                require(uncertain.operation in {"task.create", "task.save"}, "SERVICE_TASK_RECONCILIATION_KIND")
                require(observed[4] != "ABSENT" or uncertain.operation == "task.create", "SERVICE_TASK_ABSENCE_REQUIRES_CREATE")
                require(len(self._task_reconciliation_history) < 256, "SERVICE_TASK_RECONCILIATION_CAPACITY")
                self._task_reconciliation_history.append((uncertain.original_message, observed[2],
                    "CURRENT_TASK_CAS_SELECTED_PRIOR_WRITE_HISTORY_UNRESOLVED"))
                self._uncertain_task_request = None
                self._state, self._detail = "READY", "Current task revision selected explicitly; prior write evidence retained; effect authority closed."

    def acknowledge_meaning_reconciliation(self, task_id, revision, task_revision):
        """Select only an actual meaning observation, retaining prior uncertainty."""
        with self._lock:
            observed = self._observed_meaning_snapshot
            require(self._pending is None and self._state in {"READY", "RECOVERING"}
                and observed is not None and observed[:3] == (task_id, revision, task_revision), "SERVICE_MEANING_OBSERVATION_REQUIRED")
            if self._state == "RECOVERING":
                uncertain = self._uncertain_task_request
                require(uncertain is not None and uncertain.operation == "task.meaning_propose"
                    and uncertain.scope_id == observed[4] and uncertain.record.as_dict()["task_id"] == task_id,
                    "SERVICE_MEANING_RECONCILIATION_NOT_MATCHED")
                require(observed[5] != "ABSENT" or uncertain.record.as_dict()["meaning_expected_revision"] is None,
                    "SERVICE_MEANING_ABSENCE_REQUIRES_CREATE")
                require(len(self._task_reconciliation_history) < 256, "SERVICE_TASK_RECONCILIATION_CAPACITY")
                self._task_reconciliation_history.append((uncertain.original_message, observed[3],
                    "CURRENT_MEANING_CAS_SELECTED_PRIOR_WRITE_HISTORY_UNRESOLVED"))
                self._uncertain_task_request = None
                self._state, self._detail = "READY", "Current interpretation revision selected; prior write evidence retained."

    def acknowledge_editor_reconciliation(self, task_id, revision, current_task_revision):
        """Explicitly select an actual current recovery CAS; retain uncertainty."""
        with self._lock:
            observed = self._observed_editor_snapshot
            require(self._pending is None and self._state in {"READY", "RECOVERING"}
                and observed is not None and observed[:3] == (task_id, revision, current_task_revision),
                "SERVICE_EDITOR_OBSERVATION_REQUIRED")
            if self._state == "RECOVERING":
                uncertain = self._uncertain_task_request
                require(uncertain is not None and uncertain.operation in EDITOR_MUTATIONS
                    and uncertain.scope_id == observed[4] and uncertain.record.as_dict()["task_id"] == task_id,
                    "SERVICE_EDITOR_RECONCILIATION_NOT_MATCHED")
                require(observed[5] != "ABSENT" or (uncertain.operation == "task.editor_retain"
                    and uncertain.record.as_dict()["editor_expected_revision"] is None),
                    "SERVICE_EDITOR_ABSENCE_REQUIRES_CREATE")
                require(len(self._task_reconciliation_history) < 256, "SERVICE_TASK_RECONCILIATION_CAPACITY")
                self._task_reconciliation_history.append((uncertain.original_message, observed[3],
                    "CURRENT_EDITOR_CAS_SELECTED_PRIOR_WRITE_HISTORY_UNRESOLVED"))
                self._uncertain_task_request = None
                self._state, self._detail = "READY", "Current editor recovery selected; prior custody evidence retained."


def owned_service_shutdown_settlement_witness_is_current(service, witness):
    """Return whether ``witness`` is the current opaque proof for ``service``.

    This deliberately rejects structural lookalikes.  Shutdown coordination
    must hold the exact capability emitted by an exact :class:`OwnedService`,
    and the controller must still satisfy the observation predicate which
    originally made that capability available.  It performs no durable write,
    process operation, or publication.
    """
    if type(service) is not OwnedService or type(witness) is not _ShutdownSettlementWitness:
        return False
    try:
        with service._lock:
            if service._shutdown_settlement_witness is not witness:
                return False
            if service._shutdown_settlement_basis == "PRESTART_NO_PUBLICATION":
                return service._prestart_no_publication()
            if service._shutdown_settlement_basis == "NATIVE_RETIREMENT_COMPLETE":
                return service._native_retirement_complete()
            return False
    except BaseException:
        # Terminal settlement is a fail-closed assertion.  A malformed or
        # concurrently damaged controller can never be promoted to proof.
        return False

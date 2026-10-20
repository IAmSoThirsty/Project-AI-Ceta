"""Retain application ownership until service and compiler exit are observed.

The launcher custody record below is deliberately narrower than product state.
It lives beside the selected development profile only to fence a subsequent
launcher after an abnormal outer-process exit.  It is neither an authority
writer nor a surviving supervisor: the outer process still retains the actual
``PendingShutdownOwner`` until it observes terminal settlement.
"""
from dataclasses import dataclass, replace
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid

from ceta.contracts.wire import ContractError, MAX_WIRE_BYTES, canonical_bytes, strict_loads


@dataclass(frozen=True)
class ShutdownObservation:
    state: str
    requested: bool
    service_state: str | None
    session_state: str | None
    context_pending: bool
    diagnostic_codes: tuple[str, ...]
    reconciliation: str = "NOT_ESTABLISHED_BY_PROCESS_EXIT"
    stop_request_attempts: int = 0
    service_fallback_attempts: int = 0
    poll_attempts: int = 0

    @property
    def workers_stopped(self):
        return self.state == "STOPPED"


@dataclass(frozen=True)
class PendingShutdownOwner:
    """Explicit retry custody within the current interpreter lifetime.

    Retaining this object retains the captured service, session and their work.
    It is not a transfer to a surviving supervisor or proof of process exit.
    """

    coordinator: "ShutdownCoordinator"

    @property
    def service(self):
        return self.coordinator._service

    @property
    def session(self):
        return self.coordinator._session

    @property
    def observation(self):
        return self.coordinator.observation

    def retry(self, *, timeout_seconds=15.0, poll_seconds=0.01):
        return self.coordinator.drain(timeout_seconds=timeout_seconds,
                                      poll_seconds=poll_seconds, retry_stop=True)


_TERMINAL_SETTLEMENT_FACTORY = object()


class _TerminalSettlement:
    """Non-serializable process-local proof for one bound launcher lifetime.

    A public ``ShutdownObservation`` is descriptive data, never admission
    authority.  This object is minted only by the captured coordinator after it
    has a current terminal observation and its concrete service presents the
    matching native-retirement/no-publication witness.  It is intentionally
    process-local: a hard interpreter exit cannot manufacture a survivor from a
    durable launcher record.
    """

    __slots__ = ("_binding", "_coordinator", "_observation", "_witness")

    def __init__(self, factory, binding, coordinator, observation, witness):
        if factory is not _TERMINAL_SETTLEMENT_FACTORY:
            raise TypeError("SHUTDOWN_SETTLEMENT_FACTORY_REQUIRED")
        self._binding = binding
        self._coordinator = coordinator
        self._observation = observation
        self._witness = witness

    def observation_for(self, binding):
        """Return the exact live observation only for its original custody."""
        if (binding is None or self._binding is not binding
                or self._coordinator._custody_binding is not binding
                or self._coordinator.observation is not self._observation
                or not self._coordinator._terminal_observation(self._observation)
                or not self._coordinator._settlement_witness_current(self._witness)):
            raise ValueError("LAUNCHER_CUSTODY_TERMINAL_PROOF_REQUIRED")
        return self._observation


class ShutdownIncomplete(RuntimeError):
    def __init__(self, observation, pending_owner=None, *, cleanup_error=None,
                 durable_custody_error=None):
        super().__init__("APPLICATION_SHUTDOWN_UNRESOLVED")
        self.observation = observation
        self.pending_owner = pending_owner
        self.cleanup_error = cleanup_error
        # This is diagnostic evidence only.  A failed persistence attempt must
        # never replace the retained owner or the initiating BaseException.
        self.durable_custody_error = durable_custody_error


class LauncherCustodyIncomplete(RuntimeError):
    """A prior outer-process lifetime remains unobserved and blocks restart."""

    def __init__(self, record):
        super().__init__("APPLICATION_LAUNCHER_CUSTODY_RECONCILIATION_REQUIRED")
        self.record = record


class LauncherShutdownCustody:
    """A durable, profile-local restart fence for launcher-owned shutdown.

    This is intentionally *not* a ProductSupervisor, native broker, product
    journal, authority issuer, or evidence ledger.  ``PENDING`` proves only
    that the launcher did not observe terminal settlement before it could exit.
    It cannot acknowledge custody and can never authorize a fresh service.

    The record is held under the same selected profile root that the existing
    ``SqliteJournal`` owns.  Its bytes use the existing canonical wire helper,
    and the record is atomically replaced after a flushed temporary write.  A
    retained process-local lock prevents two launchers for one profile from
    concurrently deciding that a prior lifetime is clear.
    """

    _PROFILE = "ceta-launcher-shutdown-custody-v1"
    _RECORD_NAME = ".ceta-launcher-shutdown-custody-v1.json"
    _LOCK_NAME = ".ceta-launcher-shutdown-custody-v1.lock"
    _FIELDS = frozenset((
        "profile", "record_id", "revision", "state", "launch_phase",
        "publication_state", "observation", "diagnostic_codes",
        "prior_terminal_record_id", "updated_at_ns",
    ))
    _OBSERVATION_FIELDS = frozenset((
        "state", "requested", "service_state", "session_state",
        "context_pending", "diagnostic_codes", "reconciliation",
        "stop_request_attempts", "service_fallback_attempts", "poll_attempts",
    ))
    _PENDING = "PENDING"
    _TERMINATED = "SETTLEMENT_OBSERVED"
    _PHASES = frozenset((
        "CONSTRUCTOR_UNOBSERVED", "START_REQUESTED",
        "START_RETURNED_UNOBSERVED", "STOPPING", "SETTLEMENT_OBSERVED",
    ))
    _PUBLICATION = frozenset((
        "UNOBSERVED", "START_REQUESTED_UNOBSERVED", "POSSIBLE_PUBLICATION",
        "SETTLEMENT_OBSERVED",
    ))
    _CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")
    _RECORD_ID = re.compile(r"launcher-custody:[0-9a-f]{32}")

    def __init__(self, profile_root):
        root = Path(profile_root)
        if not root.is_absolute():
            raise ValueError("LAUNCHER_CUSTODY_ROOT_REQUIRED")
        try:
            facts = self._root_facts(root)
        except (OSError, RuntimeError, ValueError):
            raise ValueError("LAUNCHER_CUSTODY_ROOT_REQUIRED") from None
        self._root = root
        self._root_identity = facts.st_dev, facts.st_ino
        self._path = root / self._RECORD_NAME
        self._lock_path = root / self._LOCK_NAME
        self._lock_descriptor = None
        self._unlock = None
        self._record = None
        # This object is generated only after a reservation has been durably
        # written.  It binds an in-memory coordinator proof to this exact
        # launcher lifetime; it is not persisted or recoverable after a crash.
        self._terminal_binding = None

    @staticmethod
    def _io_path(path):
        """Keep logical profile paths; use one validated native I/O spelling."""
        path = Path(path)
        if os.name != "nt":
            return path
        text = str(path)
        if text[:8].upper() == "\\\\?\\UNC\\":
            text = "\\\\" + text[8:]
        elif text.startswith("\\\\?\\"):
            text = text[4:]
        normal = Path(text)
        if (not normal.is_absolute() or text.startswith("\\\\.\\")
                or not (re.fullmatch(r"[A-Za-z]:", normal.drive)
                        or (normal.drive.startswith("\\\\") and len(normal.drive.split("\\")) == 4))):
            raise ValueError("LAUNCHER_CUSTODY_ROOT_REQUIRED")
        anchor_parts = normal.drive[2:].split("\\") if normal.drive.startswith("\\\\") else []
        for part in (*anchor_parts, *normal.parts[1:]):
            if (not part or part in {".", ".."} or part.endswith((".", " "))
                    or any(character in '<>:"|?*' or ord(character) < 32 for character in part)
                    or Path(part).is_reserved()):
                raise ValueError("LAUNCHER_CUSTODY_ROOT_REQUIRED")
        return Path("\\\\?\\UNC\\" + text[2:] if text.startswith("\\\\") else "\\\\?\\" + text)

    @classmethod
    def _root_facts(cls, root):
        for path in (*reversed(root.parents), root):
            facts = os.lstat(cls._io_path(path))
            if (not stat.S_ISDIR(facts.st_mode)
                    or getattr(facts, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
                raise RuntimeError("LAUNCHER_CUSTODY_LINK_REJECTED")
        return facts

    @staticmethod
    def _is_link(path):
        try:
            facts = os.lstat(LauncherShutdownCustody._io_path(path))
        except FileNotFoundError:
            return False
        return (stat.S_ISLNK(facts.st_mode)
                or bool(getattr(facts, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
                or (stat.S_ISREG(facts.st_mode) and facts.st_nlink != 1))

    def _attach_io_errors(self, primary, errors, **facts):
        """Exact custody is stored without overridable exception/dict hooks."""
        data = BaseException.__dict__["__dict__"].__get__(primary)
        previous = dict.get(data, "launcher_custody_io_errors", ())
        if type(previous) is not tuple:
            previous = ()
        dict.update(data, launcher_custody=self, launcher_custody_root_identity=self._root_identity,
                    launcher_custody_io_errors=previous + tuple(errors), **facts)

    @property
    def path(self):
        return self._path

    @property
    def record(self):
        record = self._record if self._record is not None else self._read()
        return None if record is None else strict_loads(canonical_bytes(record))

    @property
    def terminal_observed(self):
        return self._record is not None and self._record["state"] == self._TERMINATED

    def _coordinator_binding(self):
        """Return the live, per-reservation binding for the captured coordinator."""
        self._require_lock()
        if self._record is None or self._terminal_binding is None:
            raise RuntimeError("LAUNCHER_CUSTODY_RESERVATION_REQUIRED")
        return self._terminal_binding

    def _reject_linked_paths(self):
        facts = self._root_facts(self._root)
        if (facts.st_dev, facts.st_ino) != self._root_identity:
            raise RuntimeError("LAUNCHER_CUSTODY_ROOT_CHANGED")
        for path in (self._path, self._lock_path):
            if self._is_link(path):
                raise RuntimeError("LAUNCHER_CUSTODY_LINK_REJECTED")

    def acquire(self):
        """Retain the per-profile interprocess decision lock for this lifetime."""
        if self._lock_descriptor is not None:
            return
        self._reject_linked_paths()
        descriptor = os.open(self._io_path(self._lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                unlock = lambda value: msvcrt.locking(value, msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - product runtime is Windows; supports local analysis.
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                unlock = lambda value: fcntl.flock(value, fcntl.LOCK_UN)
        except Exception as error:
            failure = RuntimeError("LAUNCHER_CUSTODY_LOCK_UNAVAILABLE")
            try:
                os.close(descriptor)
            except BaseException as secondary:
                self._attach_io_errors(failure, (secondary,), launcher_custody_uncertain_close=descriptor)
            raise failure from error
        except BaseException as primary:
            try:
                os.close(descriptor)
            except BaseException as secondary:
                self._attach_io_errors(primary, (secondary,), launcher_custody_uncertain_close=descriptor)
            raise
        self._lock_descriptor, self._unlock = descriptor, unlock

    def close(self):
        """Release only the launcher decision lock; never erase a record."""
        descriptor, unlock = self._lock_descriptor, self._unlock
        self._lock_descriptor = self._unlock = None
        if descriptor is None:
            return
        try:
            unlock(descriptor)
        except BaseException as primary:
            try:
                os.close(descriptor)
            except BaseException as secondary:
                self._attach_io_errors(primary, (secondary,), launcher_custody_uncertain_close=descriptor)
            raise
        try:
            os.close(descriptor)
        except BaseException as primary:
            self._attach_io_errors(primary, (), launcher_custody_uncertain_close=descriptor)
            raise

    def _require_lock(self):
        if self._lock_descriptor is None:
            raise RuntimeError("LAUNCHER_CUSTODY_LOCK_REQUIRED")

    @classmethod
    def _codes(cls, codes):
        if type(codes) not in (tuple, list) or len(codes) > 64:
            raise ValueError("LAUNCHER_CUSTODY_RECORD_INVALID")
        normalized = []
        for code in codes:
            if type(code) is not str or cls._CODE.fullmatch(code) is None or code in normalized:
                raise ValueError("LAUNCHER_CUSTODY_RECORD_INVALID")
            normalized.append(code)
        return normalized

    @classmethod
    def _append_code(cls, codes, code):
        values = tuple(codes)
        return cls._codes(values if code in values else values + (code,))

    @classmethod
    def _observation_wire(cls, observation):
        if type(observation) is not ShutdownObservation:
            raise ValueError("LAUNCHER_CUSTODY_OBSERVATION_REQUIRED")
        values = {
            "state": observation.state,
            "requested": observation.requested,
            "service_state": observation.service_state,
            "session_state": observation.session_state,
            "context_pending": observation.context_pending,
            "diagnostic_codes": cls._codes(observation.diagnostic_codes),
            "reconciliation": observation.reconciliation,
            "stop_request_attempts": observation.stop_request_attempts,
            "service_fallback_attempts": observation.service_fallback_attempts,
            "poll_attempts": observation.poll_attempts,
        }
        cls._validate_observation(values)
        return values

    @classmethod
    def _validate_observation(cls, value):
        if type(value) is not dict or set(value) != cls._OBSERVATION_FIELDS:
            raise ValueError("LAUNCHER_CUSTODY_RECORD_INVALID")
        if (type(value["state"]) is not str or not value["state"].isupper()
                or type(value["requested"]) is not bool
                or type(value["context_pending"]) is not bool
                or type(value["reconciliation"]) is not str
                or not value["reconciliation"].isupper()
                or any(value[field] is not None and type(value[field]) is not str
                       for field in ("service_state", "session_state"))
                or any(type(value[field]) is not int or value[field] < 0 or value[field] > 1_000_000
                       for field in ("stop_request_attempts", "service_fallback_attempts", "poll_attempts"))):
            raise ValueError("LAUNCHER_CUSTODY_RECORD_INVALID")
        cls._codes(value["diagnostic_codes"])

    @staticmethod
    def _terminal_observation(value):
        """The persisted terminal shape is necessary but never sufficient proof."""
        return (value["state"] == "STOPPED" and value["requested"] is True
                and value["service_state"] == "STOPPED"
                and value["session_state"] == "STOPPED"
                and value["context_pending"] is False
                and value["poll_attempts"] >= 1)

    @classmethod
    def _validate_record(cls, value):
        if type(value) is not dict or set(value) != cls._FIELDS:
            raise ValueError("LAUNCHER_CUSTODY_RECORD_INVALID")
        if (value["profile"] != cls._PROFILE
                or type(value["record_id"]) is not str
                or cls._RECORD_ID.fullmatch(value["record_id"]) is None
                or type(value["revision"]) is not int or value["revision"] < 1
                or value["state"] not in {cls._PENDING, cls._TERMINATED}
                or value["launch_phase"] not in cls._PHASES
                or value["publication_state"] not in cls._PUBLICATION
                or (value["prior_terminal_record_id"] is not None
                    and (type(value["prior_terminal_record_id"]) is not str
                         or cls._RECORD_ID.fullmatch(value["prior_terminal_record_id"]) is None))
                or type(value["updated_at_ns"]) is not int or value["updated_at_ns"] < 0):
            raise ValueError("LAUNCHER_CUSTODY_RECORD_INVALID")
        cls._codes(value["diagnostic_codes"])
        observation = value["observation"]
        if observation is not None:
            cls._validate_observation(observation)
        if value["state"] == cls._TERMINATED:
            if (value["launch_phase"] != "SETTLEMENT_OBSERVED"
                    or value["publication_state"] != "SETTLEMENT_OBSERVED"
                    or observation is None or not cls._terminal_observation(observation)):
                raise ValueError("LAUNCHER_CUSTODY_RECORD_INVALID")

    def _read_wire(self, path):
        stream = path.open("rb")
        try:
            wire = stream.read(MAX_WIRE_BYTES + 1)
        except BaseException as primary:
            errors = []
            returned = False
            try:
                stream.close()
                returned = True
            except BaseException as secondary:
                errors.append(secondary)
            self._attach_io_errors(primary, errors, launcher_custody_read_stream=stream,
                launcher_custody_read_close_attempted=True, launcher_custody_read_close_returned=returned)
            raise
        try:
            stream.close()
        except BaseException as primary:
            self._attach_io_errors(primary, (), launcher_custody_read_stream=stream,
                launcher_custody_read_close_attempted=True, launcher_custody_read_close_returned=False)
            raise
        return wire

    def _read(self):
        self._reject_linked_paths()
        path = self._io_path(self._path)
        try:
            facts = os.lstat(path)
        except FileNotFoundError:
            return None
        except OSError:
            raise RuntimeError("LAUNCHER_CUSTODY_RECORD_UNREADABLE") from None
        if not stat.S_ISREG(facts.st_mode):
            raise RuntimeError("LAUNCHER_CUSTODY_RECORD_UNREADABLE")
        try:
            value = strict_loads(self._read_wire(path))
            self._validate_record(value)
            return value
        except (ContractError, OSError, UnicodeError, ValueError) as primary:
            failure = RuntimeError("LAUNCHER_CUSTODY_RECORD_UNREADABLE")
            data = BaseException.__dict__["__dict__"].__get__(primary)
            errors = dict.get(data, "launcher_custody_io_errors", ())
            if type(errors) is not tuple:
                errors = ()
            facts = {key: dict.__getitem__(data, key) for key in (
                "launcher_custody_read_stream", "launcher_custody_read_close_attempted",
                "launcher_custody_read_close_returned") if dict.__contains__(data, key)}
            self._attach_io_errors(failure, errors, launcher_custody_read_failure=primary, **facts)
            raise failure from None

    def _write(self, value):
        self._require_lock()
        self._validate_record(value)
        self._reject_linked_paths()
        wire = canonical_bytes(value)
        temporary = self._path.with_name(self._path.name + "." + uuid.uuid4().hex + ".tmp")
        temporary_io = self._io_path(temporary)
        descriptor = None
        created = False
        identity = None
        closing = None
        replacement_attempted = False
        try:
            descriptor = os.open(temporary_io, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            created = True
            facts = os.fstat(descriptor)
            identity = facts.st_dev, facts.st_ino
            remaining = memoryview(wire)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("LAUNCHER_CUSTODY_WRITE_FAILED")
                remaining = remaining[written:]
            os.fsync(descriptor)
            closing = descriptor
            descriptor = None
            os.close(closing)
            closing = None
            self._reject_linked_paths()
            facts = os.lstat(temporary_io)
            if self._is_link(temporary) or (facts.st_dev, facts.st_ino) != identity:
                raise RuntimeError("LAUNCHER_CUSTODY_TEMPORARY_CHANGED")
            replacement_attempted = True
            os.replace(temporary_io, self._io_path(self._path))
            created = False
        except BaseException as primary:
            errors = []
            if descriptor is not None:
                closing, descriptor = descriptor, None
                try:
                    os.close(closing)
                    closing = None
                except BaseException as secondary:
                    errors.append(secondary)
            if created:
                try:
                    self._reject_linked_paths()
                    try:
                        facts = os.lstat(temporary_io)
                    except FileNotFoundError:
                        facts = None
                    if facts is not None:
                        if self._is_link(temporary) or identity != (facts.st_dev, facts.st_ino):
                            raise RuntimeError("LAUNCHER_CUSTODY_TEMPORARY_CHANGED")
                        temporary_io.unlink()
                except BaseException as secondary:
                    errors.append(secondary)
            self._attach_io_errors(primary, errors, launcher_custody_temporary_path=temporary,
                launcher_custody_temporary_created=created, launcher_custody_temporary_identity=identity,
                launcher_custody_uncertain_close=closing,
                launcher_custody_replacement_attempted=replacement_attempted)
            raise

    def reserve_launch(self):
        """Fence a new outer launcher before construction can publish work."""
        self.acquire()
        try:
            prior = self._read()
            if prior is not None and prior["state"] != self._TERMINATED:
                raise LauncherCustodyIncomplete(prior)
            record = {
                "profile": self._PROFILE,
                "record_id": "launcher-custody:" + uuid.uuid4().hex,
                "revision": 1,
                "state": self._PENDING,
                # Entering construction is not a no-entry observation.
                "launch_phase": "CONSTRUCTOR_UNOBSERVED",
                "publication_state": "UNOBSERVED",
                "observation": None,
                "diagnostic_codes": [],
                "prior_terminal_record_id": None if prior is None else prior["record_id"],
                "updated_at_ns": time.time_ns(),
            }
            self._write(record)
            self._record = record
            self._terminal_binding = object()
            return self.record
        except BaseException as primary:
            try:
                self.close()
            except BaseException as secondary:
                self._attach_io_errors(primary, (secondary,))
            raise

    def _replace(self, **changes):
        self._require_lock()
        if self._record is None:
            raise RuntimeError("LAUNCHER_CUSTODY_RESERVATION_REQUIRED")
        if self._record["state"] != self._PENDING:
            raise RuntimeError("LAUNCHER_CUSTODY_ALREADY_TERMINAL")
        record = dict(self._record)
        record.update(changes)
        record["revision"] += 1
        record["updated_at_ns"] = time.time_ns()
        self._write(record)
        self._record = record
        return self.record

    def mark_start_requested(self):
        """Persist the ambiguous publication boundary before ``service.start``."""
        return self._replace(launch_phase="START_REQUESTED",
                             publication_state="START_REQUESTED_UNOBSERVED")

    def mark_start_returned(self):
        """A return from start still does not establish publication or retirement."""
        return self._replace(launch_phase="START_RETURNED_UNOBSERVED",
                             publication_state="POSSIBLE_PUBLICATION")

    def mark_constructor_unresolved(self):
        """Construction failed before a retained service can prove no-entry."""
        return self._replace(launch_phase="CONSTRUCTOR_UNOBSERVED",
                             publication_state="UNOBSERVED",
                             diagnostic_codes=self._append_code(
                                 self._record["diagnostic_codes"], "SERVICE_CONSTRUCTION_UNOBSERVED"))

    def mark_unresolved(self, observation):
        """Persist structured uncertainty; this never converts it to settlement."""
        wire = self._observation_wire(observation)
        publication = ("POSSIBLE_PUBLICATION" if self._record["publication_state"] != "UNOBSERVED"
                       else "UNOBSERVED")
        return self._replace(state=self._PENDING, launch_phase="STOPPING",
                             publication_state=publication, observation=wire,
                             diagnostic_codes=self._append_code(
                                 self._record["diagnostic_codes"], "APPLICATION_SHUTDOWN_UNRESOLVED"))

    def mark_termination_observed(self, settlement):
        """Record only a coordinator-bound, concrete terminal settlement.

        A ``ShutdownObservation`` is intentionally rejected here even when it
        says ``STOPPED``.  It can be constructed by any caller and carries no
        native owner/no-publication provenance.  Only the in-memory proof from
        the coordinator captured for this reservation can advance a PENDING
        record to admission-clearing settlement.
        """
        if type(settlement) is not _TerminalSettlement:
            raise ValueError("LAUNCHER_CUSTODY_TERMINAL_PROOF_REQUIRED")
        observation = settlement.observation_for(self._terminal_binding)
        return self._replace(state=self._TERMINATED,
                             launch_phase="SETTLEMENT_OBSERVED",
                             publication_state="SETTLEMENT_OBSERVED",
                             observation=self._observation_wire(observation),
                             diagnostic_codes=self._codes(observation.diagnostic_codes))


class ShutdownCoordinator:
    """One captured service/session; Stop precedes polling or draft validation.

    STOPPED establishes observed owned lifetime settlement only. It does not
    establish saved drafts, completed effects, or reconciled uncertain attempts.
    A timeout retains the captured owners and returns an unresolved observation.
    """

    def __init__(self, service, session=None, *, custody_binding=None):
        self._service, self._session = service, session
        # A normal coordinator remains useful to callers that only need
        # shutdown observation.  A launcher-terminal proof is unavailable
        # unless the outer custody reservation explicitly supplied this exact
        # process-local binding.
        self._custody_binding = custody_binding
        self._requested = False
        self._codes = []
        self._observation = ShutdownObservation("NOT_REQUESTED", False, None, None, False, ())
        self._pending_owner = PendingShutdownOwner(self)

    def capture_session(self, session):
        if self._requested or self._session is not None:
            raise RuntimeError("SHUTDOWN_SESSION_ALREADY_CAPTURED")
        self._session = session

    @property
    def observation(self):
        return self._observation

    @property
    def pending_owner(self):
        return self._pending_owner

    @staticmethod
    def _terminal_observation(observation):
        return (type(observation) is ShutdownObservation
                and observation.state == "STOPPED"
                and observation.requested is True
                and observation.service_state == "STOPPED"
                and observation.session_state == "STOPPED"
                and observation.context_pending is False
                and observation.poll_attempts >= 1)

    def _settlement_witness_current(self, witness):
        """Accept only a current opaque witness from the concrete owner.

        Lifecycle cannot safely infer native retirement from a structural
        service interface.  The composition validator is deliberately exact:
        it rejects substitutes which happen to offer a method named
        ``shutdown_settlement_witness`` and it rechecks the owner's retained
        native/no-publication predicate while holding that owner's lock.
        """
        try:
            from ceta.composition.owned_service import (
                owned_service_shutdown_settlement_witness_is_current,
            )
        except Exception:
            return False
        try:
            return owned_service_shutdown_settlement_witness_is_current(
                self._service, witness) is True
        except BaseException:
            return False

    def terminal_settlement(self):
        """Mint the only proof accepted by a bound launcher custody record."""
        observation = self._observation
        if self._custody_binding is None or not self._terminal_observation(observation):
            raise RuntimeError("SHUTDOWN_TERMINAL_SETTLEMENT_UNAVAILABLE")
        try:
            witness = self._service.shutdown_settlement_witness()
        except Exception as error:
            raise RuntimeError("SHUTDOWN_NATIVE_RETIREMENT_WITNESS_REQUIRED") from error
        if witness is None or not self._settlement_witness_current(witness):
            raise RuntimeError("SHUTDOWN_NATIVE_RETIREMENT_WITNESS_REQUIRED")
        return _TerminalSettlement(_TERMINAL_SETTLEMENT_FACTORY, self._custody_binding,
                                   self, observation, witness)

    def _record(self, code):
        if code not in self._codes:
            self._codes.append(code)
        self._observation = replace(self._observation, diagnostic_codes=tuple(self._codes))

    def _service_stop_fallback(self, reason):
        self._observation = replace(self._observation,
            service_fallback_attempts=self._observation.service_fallback_attempts + 1)
        try:
            self._service.request_stop(reason)
        except BaseException as error:
            self._record("SERVICE_STOP_FALLBACK_FAILED")
            if not isinstance(error, Exception):
                self._record("SERVICE_STOP_FALLBACK_INTERRUPTED")
            return error
        return None

    def request(self, *, retry=False):
        if type(retry) is not bool:
            raise ValueError("SHUTDOWN_RETRY_FLAG_REQUIRED")
        if self._requested and (not retry or self._observation.workers_stopped):
            return self._observation
        self._requested = True
        # Publish requested state before either callback can be interrupted.
        # A session remains conservatively pending until its poll observes exit.
        self._observation = replace(self._observation, state="STOPPING", requested=True,
            context_pending=self._session is not None,
            stop_request_attempts=self._observation.stop_request_attempts + 1)
        try:
            if self._session is None:
                self._service.request_stop("reason:application-exit")
            else:
                self._session.stop()
        except BaseException as error:
            # Session cancellation is first. If its callback fails, still ask the
            # actual service to disable dispatch and terminate its exact owners.
            self._record("SESSION_OR_SERVICE_STOP_FAILED")
            if not isinstance(error, Exception):
                self._record("SESSION_OR_SERVICE_STOP_INTERRUPTED")
            fallback = self._service_stop_fallback("reason:application-exit-fallback")
            if not isinstance(error, Exception):
                raise
            if fallback is not None and not isinstance(fallback, Exception):
                raise fallback
        return self._observation

    def advance(self):
        if not self._requested:
            raise RuntimeError("SHUTDOWN_NOT_REQUESTED")
        self._observation = replace(self._observation,
            poll_attempts=self._observation.poll_attempts + 1)
        try:
            native = self._service.poll() if self._session is None else self._session.poll()
            if type(native) is not dict or type(native.get("state")) is not str:
                raise ValueError("SHUTDOWN_OBSERVATION_REQUIRED")
            service_state = native["state"]
            session_state = service_state if self._session is None else self._session.status
            pending = False if self._session is None else getattr(self._session, "context_busy", False)
            if type(session_state) is not str or type(pending) is not bool:
                raise ValueError("SHUTDOWN_SESSION_OBSERVATION_REQUIRED")
            stopped = service_state == session_state == "STOPPED" and not pending
            self._observation = replace(self._observation,
                state="STOPPED" if stopped else "STOPPING", requested=True,
                service_state=service_state, session_state=session_state, context_pending=pending)
        except BaseException as error:
            self._record("SHUTDOWN_OBSERVATION_FAILED")
            if not isinstance(error, Exception):
                self._record("SHUTDOWN_OBSERVATION_INTERRUPTED")
            self._observation = replace(self._observation, state="OBSERVATION_FAILED", requested=True)
            fallback = self._service_stop_fallback("reason:application-exit-observation-fallback")
            if not isinstance(error, Exception):
                raise
            if fallback is not None and not isinstance(fallback, Exception):
                raise fallback
        return self._observation

    def retain_failure(self, primary, cleanup):
        """Export typed custody without replacing an already raised failure."""
        self._record("APPLICATION_CLEANUP_UNRESOLVED")
        if isinstance(cleanup, ShutdownIncomplete):
            incomplete = cleanup
            incomplete.pending_owner = self.pending_owner
            incomplete.observation = self.observation
        else:
            self._record("SHUTDOWN_DRAIN_FAILED")
            incomplete = ShutdownIncomplete(self.observation, self.pending_owner,
                                            cleanup_error=cleanup)
        if primary is not cleanup:
            try:
                primary.add_note("APPLICATION_CLEANUP_UNRESOLVED: " + type(cleanup).__name__)
            except BaseException:
                self._record("PRIMARY_EXCEPTION_NOTE_FAILED")
                incomplete.observation = self.observation
        # Export after the diagnostic hook: an overridden add_note can clear or
        # replace its exception dictionary even when it returns successfully.
        # The base descriptor also bypasses custom attribute hooks.
        BaseException.__dict__["__dict__"].__get__(primary)["shutdown_incomplete"] = incomplete
        return incomplete

    def drain(self, *, timeout_seconds=15.0, poll_seconds=0.01, retry_stop=False):
        if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                or not 0 <= timeout_seconds <= 60
                or type(poll_seconds) not in (int, float) or not math.isfinite(poll_seconds)
                or not 0 < poll_seconds <= 1 or type(retry_stop) is not bool):
            raise ValueError("SHUTDOWN_TIMING_REQUIRED")
        self.request(retry=retry_stop)
        deadline = time.monotonic() + timeout_seconds
        while True:
            observed = self.advance()
            if observed.workers_stopped:
                return observed
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._record("SHUTDOWN_DEADLINE_EXPIRED")
                return self._observation
            time.sleep(min(poll_seconds, remaining))

"""Canonical retained CPU admission on the existing kernel and journal.

The optional captured native retainer must coordinate the real current owner
view, exact native custody and physical outcome capacity. No provider is
installed here. A configured controlled provider is not production authority.
"""
from functools import wraps
from dataclasses import replace
import math
import inspect
import threading
import time

from ceta.contracts.kernel_transactions import (BUDGET_FIELDS, basis_key, budget_key, intent_key,
    deadline_text, read_basis, read_intent, require)
from ceta.contracts.real_effect import CAP_OPERATION, decode_owned_cpu_request
from ceta.contracts.store_transactions import StoreKey
from ceta.contracts.temporal import (ClockSample, Deadline, require_clock_progress,
    require_deadline_current)
from ceta.contracts.wire import ContractError, MAX_INTEGER
from ceta.contracts.resource_management import ProcessResourceIdentity
from ceta.contracts.workload_throttling import CpuRateChange, CpuRateObservation
from ceta.effects.native_cpu_binding import CpuDriverArguments, DRIVER_DOMAIN
from ceta.identity.cpu_outcome_capacity import _RetainedCpuOutcomeCapacity
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
from .effect_transactions import KernelEffectTransactions, outcome_key, task_outcome_key
from .owner_authority import owned_cpu_proposal

MAXIMUM_CHECK_NS = 50_000_000
_ISSUER = object()
_APPLY = WindowsOwnedProcess.apply_cpu_rate_limit
_RESTORE = WindowsOwnedProcess.restore_cpu_rate_limit
_LIVENESS_LOCK = threading.Lock()
_ACTIVE_OWNERS = {}
_ACTIVE_STORES = {}
_MUTATING_OWNERS = {}
_MUTATING_STORES = {}


class _MutationRegistration:
    """One volatile invocation, never an authority or persistent reservation."""
    __slots__ = ('coordinator', 'started', 'retired', 'cleanup_failures')

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.started = self.retired = False
        self.cleanup_failures = ()


def _registration_custody(primary, registration, secondary=None):
    """Diagnostic hooks cannot replace either exact exception or invocation."""
    try:
        data = BaseException.__dict__['__dict__'].__get__(primary)
        previous = dict.get(data, 'cpu_registration_custody', ())
        if type(previous) is not tuple: previous = ()
        dict.__setitem__(data, 'cpu_registration_custody', previous+(registration,))
        if secondary is not None:
            failures = dict.get(data, 'cpu_registration_cleanup_failures', ())
            if type(failures) is not tuple: failures = ()
            dict.__setitem__(data, 'cpu_registration_cleanup_failures', failures+
                ((secondary, BaseException.__dict__['__traceback__'].__get__(secondary)),))
    except BaseException:
        pass


def _add_mutation(table, identity, registration):
    key = id(identity)
    row = table.get(key)
    require(row is None or (len(row) == 3 and row[0] is identity
        and row[1] == len(row[2])), 'CPU_EXECUTION_REGISTRATION_CHANGED')
    previous = frozenset() if row is None else row[2]
    require(registration not in previous, 'CPU_EXECUTION_REGISTRATION_REUSED')
    invocations = previous | frozenset((registration,))
    table[key] = (identity, len(invocations), invocations)


def _remove_mutation(table, identity, registration):
    """Remove only this invocation, even if its partner was never published."""
    row = table.get(id(identity))
    if row is None: return
    require(len(row) == 3 and row[0] is identity and row[1] == len(row[2]),
        'CPU_EXECUTION_REGISTRATION_CHANGED')
    if registration not in row[2]: return
    remaining = row[2] - frozenset((registration,))
    if remaining: table[id(identity)] = (identity, len(remaining), remaining)
    else: del table[id(identity)]


def _attempt_remove(table, identity, registration):
    # A callee's exception boundary is inside the caller's protected CALL,
    # rather than a nested try/NOP while the caller holds the metadata lock.
    try:
        _remove_mutation(table, identity, registration)
    except BaseException as error:
        return error
    return None


def _argument_key(value):
    require(type(value) is CpuDriverArguments and type(value.identity) is ProcessResourceIdentity
        and type(value.expected) is CpuRateObservation, 'CPU_EXECUTION_DRIVER_BINDING_INVALID')
    value.identity.__post_init__(); value.expected.__post_init__()
    expected = value.expected
    return (value.identity.pid,value.identity.creation_time,value.identity.image_digest,
        expected.identity.pid,expected.identity.creation_time,expected.identity.image_digest,
        expected.job_digest,expected.state.value,None if expected.limit is None else expected.limit.control_flags,
        None if expected.limit is None else expected.limit.value,expected.version,expected.observed_monotonic_ns,
        expected.reason,value.deadline_monotonic_ns,value.maximum_age_ns,value.maximum_duration_ns,
        value.capture_sequence,value.request_commitment,value.driver_domain)


def _expose(primary, lease):
    """Exact custody survives refused attribute, note and formatting hooks."""
    data = BaseException.__dict__['__dict__'].__get__(primary)
    dict.update(data, owned_cpu_execution=lease, owned_process=lease._target)
    if lease._cleanup_failure is not None:
        dict.__setitem__(data, 'owned_cpu_cleanup_failure', lease._cleanup_failure)
    try:
        note = 'Retained CPU admission and canonical consumption facts remain available; never replay dispatch.'
        if not dict.__contains__(data, '__notes__'): dict.__setitem__(data, '__notes__', [note])
        else:
            notes = dict.__getitem__(data, '__notes__')
            if type(notes) is list: list.append(notes, note)
    except BaseException:
        pass


def _require_timing(elapsed, resolution, phase, code):
    """Retain computed rejection terms without another clock or hook call."""
    try:
        require(elapsed <= MAXIMUM_CHECK_NS, code)
    except ContractError as primary:
        try:
            data = BaseException.__dict__['__dict__'].__get__(primary)
            dict.__setitem__(data, 'owned_cpu_timing', dict(phase=phase,
                elapsed_ns=elapsed, bound_ns=MAXIMUM_CHECK_NS, resolution_ns=resolution))
        except BaseException:
            # Diagnostic allocation/refusal must never replace the rejection.
            pass
        raise


def _coordinated(method):
    @wraps(method)
    def wrapped(kernel, *args, **kwargs):
        return kernel._cpu_execution.mutate(method, args, kwargs)
    return wrapped


def _stopping(method):
    signature = inspect.signature(method)
    @wraps(method)
    def wrapped(kernel, *args, **kwargs):
        values = signature.bind(kernel, *args, **kwargs).arguments
        return kernel._cpu_execution.stop(method, args, kwargs, values)
    return wrapped

def _coordinated_resource(method):
    @wraps(method)
    def wrapped(adapter, *args, **kwargs):
        def invoke(kernel, *values, **options):
            return method(adapter, *values, **options)
        invoke.__name__ = 'resource.'+method.__name__
        return adapter._kernel._cpu_execution.mutate(invoke, args, kwargs)
    return wrapped


class _CpuExecutionCoordinator:
    """Volatile liveness/custody only; grants and consumed liability stay in SQL."""
    def __init__(self, kernel):
        self.kernel = kernel
        self.store = kernel._store
        self.stop_lock = getattr(self.store, '_lock', None)
        self.lock = threading.RLock()
        self.decision = threading.Lock()
        self.stopped = threading.Event()
        self.active = None
        self.allowed = None
        self.generation = 0
        self.mutating = 0
        self._mutations = set()
        self.highwater = None
        self.elapsed_highwater = -1
        self.owners = kernel._owners
        self.retain = getattr(kernel._owners, 'retain_owned_cpu_execution', None)
        info = time.get_clock_info('perf_counter')
        require(info.monotonic is True and info.adjustable is False
            and type(info.resolution) is float and math.isfinite(info.resolution)
            and info.resolution > 0, 'CPU_EXECUTION_ELAPSED_CLOCK_UNAVAILABLE')
        self.resolution = max(1, math.ceil(info.resolution*1_000_000_000))
        require(self.resolution <= MAXIMUM_CHECK_NS//2, 'CPU_EXECUTION_ELAPSED_CLOCK_UNAVAILABLE')

    def elapsed(self):
        value = time.perf_counter_ns()
        require(type(value) is int and 0 <= value <= MAX_INTEGER and value >= self.elapsed_highwater,
            'CPU_EXECUTION_ELAPSED_INVALID')
        self.elapsed_highwater = value
        return value

    def cancel(self, lease=None):
        # Only a short pure decision is protected. Never hold this lock over
        # native calls, SQL, authentication, provider callbacks or cleanup.
        with self.decision:
            if lease is not None:
                require(self.active is lease and not lease._closed, 'CPU_EXECUTION_NOT_OWNED')
            self.stopped.set()

    def mutate(self, method, args, kwargs):
        token = (method.__name__, threading.get_ident())
        registration = _MutationRegistration(self)
        primary = None
        # Retirement coverage begins before the first identity publication.
        # No nested try statement sits between the two protected map updates.
        try:
            with _LIVENESS_LOCK:
                self._selected_locked()
                if self.active is not None:
                    require(self.allowed == token, 'CPU_EXECUTION_MUTATION_BUSY')
                    self.allowed = None
                registration.started = True
                _add_mutation(_MUTATING_OWNERS, self.owners, registration)
                _add_mutation(_MUTATING_STORES, self.store, registration)
                self._mutations.add(registration)
                self.mutating = len(self._mutations)
            return method(self.kernel, *args, **kwargs)
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                self._retire_mutation(registration)
            except BaseException as secondary:
                _registration_custody(primary if primary is not None else secondary,
                    registration, secondary)
                if primary is None: raise

    def _retire_mutation(self, registration):
        failures = []
        with _LIVENESS_LOCK:
            for table, identity in ((_MUTATING_OWNERS, self.owners), (_MUTATING_STORES, self.store)):
                failure = _attempt_remove(table, identity, registration)
                if failure is not None: failures.append(failure)
            self._mutations.discard(registration)
            self.mutating = len(self._mutations)
            if registration.started and not registration.retired: self.generation += 1
            registration.retired = not failures
            registration.cleanup_failures = tuple(failures)
        if failures: raise failures[0]

    def _selected_locked(self):
        require(self.kernel._owners is self.owners, 'CPU_EXECUTION_OWNERS_REPLACED')
        require(self.kernel._store is self.store, 'CPU_EXECUTION_STORE_REPLACED')
        for row in (_ACTIVE_OWNERS.get(id(self.owners)), _ACTIVE_STORES.get(id(self.store))):
            require(row is None or (row[2] is self and row[3] is self.active),
                'CPU_EXECUTION_OTHER_KERNEL_ACTIVE')

    def require_selected_coordinator(self):
        with _LIVENESS_LOCK:
            self._selected_locked()

    def _available_locked(self):
        self._selected_locked()
        require(self.active is None and self.mutating == 0 and not self.stopped.is_set(),
            'CPU_EXECUTION_STOPPED_OR_BUSY')
        require(id(self.owners) not in _MUTATING_OWNERS and id(self.store) not in _MUTATING_STORES,
            'CPU_EXECUTION_SHARED_MUTATION_BUSY')

    def require_available(self):
        with _LIVENESS_LOCK:
            self._available_locked()

    def stop(self, method, args, kwargs, values):
        self.require_selected_coordinator()
        lease = self.active
        if lease is None:
            # Original durable authorization/commit semantics; a denied call
            # cannot poison cancellation for a future unrelated admission.
            return self.mutate(method, args, kwargs)
        # No retained coordinator/native/owner lock is acquired in this lane.
        # Refuse contention on the actual journal's short reentrant lock,
        # rather than waiting behind native dispatch or an in-flight writer.
        lock = self.stop_lock
        require(self.kernel._store is self.store and getattr(self.store,'_lock',None) is lock
            and type(lock) is type(threading.RLock()), 'CPU_EXECUTION_STOP_STORE_UNAVAILABLE')
        require(lock.acquire(blocking=False), 'CPU_EXECUTION_STOP_STATE_BUSY')
        try:
            started = time.perf_counter_ns()
            context, reason = values['request_context'], values['reason_ref']
            if method.__name__ == 'revoke':
                peer, key, cells, current, grant, event, record, sample, guard = self.kernel._revoke_basis(
                    values['grant_wire'], context, reason)
                require(key == lease._selected_grant, 'CPU_EXECUTION_STOP_TARGET_MISMATCH')
                guard()  # Same current revocation predicate used at durable COMMIT.
            else:
                from .owner_authority import KernelOwnerAuthority
                authority = KernelOwnerAuthority(self.kernel)
                revoke = method.__name__ == 'revoke_owner_authority'
                require(revoke or method.__name__ == 'stop_owner_authority', 'CPU_EXECUTION_STOP_METHOD_INVALID')
                enrollment, peer, cells, prepared, grant, key = authority._stop_basis(
                    values['enrollment_id'], context, reason, revoke=revoke)
                require(key == lease._selected_grant
                    and enrollment.scope_id == lease._request.scope_id
                    and enrollment.owner_session_nonce == lease._request.owner_session_nonce,
                    'CPU_EXECUTION_STOP_TARGET_MISMATCH')
                authority._guard('REVOKE' if revoke else 'STOP', enrollment, None, None, None, peer, context)
            require((peer.principal_id,peer.session_id) == (lease._request.principal_id,lease._request.actor_session),
                'CPU_EXECUTION_STOP_PEER_MISMATCH')
            require(self.kernel._snapshot(tuple(cells)) == cells, 'CPU_EXECUTION_STOP_STATE_CHANGED')
            finished = time.perf_counter_ns()
            require(type(started) is int and type(finished) is int and 0 <= started <= finished <= MAX_INTEGER,
                'CPU_EXECUTION_STOP_ELAPSED_INVALID')
            require(finished-started+2*self.resolution <= lease._request.maximum_duration_ns, 'CPU_EXECUTION_STOP_CHECK_TOO_SLOW')
            # Every fallible authorization/state/time callback has completed.
            with self.decision:
                require(self.active is lease and not lease._closed, 'CPU_EXECUTION_STOP_LEASE_CHANGED')
                self.stopped.set()
                admitted = lease._dispatch
        finally:
            lock.release()
        pending = ContractError('CPU_EXECUTION_CONTROL_DURABLE_PENDING')
        _expose(pending, lease)
        dict.update(BaseException.__dict__['__dict__'].__get__(pending),
            immediate_cancellation=True,durable_completed=False,dispatch_already_admitted=admitted,
            stop_preflight_elapsed_ns=finished-started+2*self.resolution)
        raise pending

    def call(self, lease, name, *args):
        token = (name, threading.get_ident())
        with _LIVENESS_LOCK:
            self._selected_locked()
            require(self.active is lease and self.allowed is None and self.mutating == 0,
                'CPU_EXECUTION_NOT_OWNED')
            self.allowed = token
        try:
            return getattr(self.kernel, name)(*args)
        finally:
            with _LIVENESS_LOCK:
                if self.allowed is token: self.allowed = None

    def create(self, request_wire, permit_wire, binding, capture, proof, context):
        return _RetainedCpuExecution(_ISSUER, self, request_wire, permit_wire,
            binding, capture, proof, context)

    def claim_liveness(self, lease):
        try:
            with _LIVENESS_LOCK:
                self._available_locked()
                row = (self.owners,self.store,self,lease)
                _ACTIVE_OWNERS[id(self.owners)] = row
                _ACTIVE_STORES[id(self.store)] = row
                self.active = lease
        except BaseException as primary:
            try:
                self.release_liveness(lease)
            except BaseException as secondary:
                lease._pending_cleanup = True
                lease._cleanup_failure = secondary
                _registration_custody(primary, lease, secondary)
            raise

    def release_liveness(self, lease):
        with _LIVENESS_LOCK:
            # Partial registration does not imply that its partner exists.
            # A losing lease can never clear another lease's winning rows.
            for table, key in ((_ACTIVE_OWNERS, id(self.owners)), (_ACTIVE_STORES, id(self.store))):
                row = table.get(key)
                if row is not None and row[0] is self.owners and row[1] is self.store \
                        and row[2] is self and row[3] is lease:
                    del table[key]
            if self.active is lease: self.active = None


class _RetainedCpuExecution:
    """Identity-bound, single-entry kernel capability, never a data receipt."""
    __slots__ = ('_owner', '_request', '_wire', '_supplied', '_binding', '_capture',
        '_proof', '_context', '_thread', '_target', '_binding_check', '_arguments',
        '_manager', '_retained', '_current', '_exit', '_entered', '_entry_attempted', '_used',
        '_closed', '_pending_cleanup', '_permit', '_attempt', '_consumption',
        '_cells', '_positions', '_generation', '_dispatch', '_outcome', '_native_arguments',
        '_effect', '_dispatching', '_called', '_change', '_argument_facts', '_consumption_attempted',
        '_intent_deadline', '_admission_started', '_clock_anchor', '_cleanup_failure', '_selected_grant',
        '_outcome_capacity')

    def __init__(self, issuer, owner, request_wire, permit_wire, binding, capture, proof, context):
        require(issuer is _ISSUER, 'CPU_EXECUTION_KERNEL_ISSUER_REQUIRED')
        self._owner = owner
        self._request = decode_owned_cpu_request(request_wire)
        self._wire = self._request.canonical_wire
        self._supplied = owner.kernel._decode(permit_wire, 'OperationPermit')
        require(self._supplied.as_dict()['status'] == 'PREPARED', 'CPU_EXECUTION_PREPARED_PERMIT_REQUIRED')
        expected = owned_cpu_proposal(owner.kernel._codec, self._request).as_dict()
        p = self._supplied.as_dict()
        require(p['scope_id'] == expected['scope_id'] and p['proposal_ref'] == expected['record_id']
            and p['operation'] == expected['operation'] and p['task_id'] == expected['task_id']
            and p['arguments_commitment'] == self._request.input_commitment,
            'CPU_EXECUTION_REQUEST_BINDING_MISMATCH')
        self._binding, self._capture, self._proof, self._context = binding, capture, proof, context
        self._target = getattr(binding, '_target', None)
        self._binding_check = getattr(binding, 'require_current', None)
        self._arguments = getattr(binding, 'driver_arguments', None)
        self._thread = threading.get_ident()
        self._manager = self._retained = self._current = self._exit = None
        self._entered = self._used = self._closed = self._pending_cleanup = False
        self._entry_attempted = False
        self._permit = self._attempt = self._consumption = None
        self._cells = self._positions = self._generation = None
        self._dispatch = False
        self._outcome = self._native_arguments = None
        self._effect = None
        self._dispatching = self._called = False
        self._change = None
        self._argument_facts = None
        self._consumption_attempted = False
        self._intent_deadline = self._admission_started = self._clock_anchor = self._cleanup_failure = self._selected_grant = None
        self._outcome_capacity = None

    def __copy__(self):
        raise ContractError('CPU_EXECUTION_COPY_FORBIDDEN')

    def __deepcopy__(self, memo):
        raise ContractError('CPU_EXECUTION_COPY_FORBIDDEN')

    def __reduce_ex__(self, protocol):
        raise ContractError('CPU_EXECUTION_SERIALIZATION_FORBIDDEN')

    def _owned(self):
        require(threading.get_ident() == self._thread, 'CPU_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        require(self._owner.active is self and not self._closed, 'CPU_EXECUTION_NOT_OWNED')
        require(self._owner.kernel._owners is self._owner.owners, 'CPU_EXECUTION_OWNERS_REPLACED')
        require(self._owner.kernel._store is self._owner.store
            and getattr(self._owner.store,'_lock',None) is self._owner.stop_lock, 'CPU_EXECUTION_STORE_REPLACED')
        require(self._request.canonical_wire == self._wire, 'CPU_EXECUTION_INPUT_CHANGED')

    def _canonical(self):
        k = self._owner.kernel
        data = KernelEffectTransactions(k)
        request, permit, peer, cells, metadata, key, task = data._load(
            self._wire, self._permit.canonical_wire, self._context)
        result = data._recover(request, permit, peer, cells, metadata, key)
        row = result.as_dict()
        require(row['state'] == 'ATTEMPT_COMMITTED' and row['reserved_bytes'] == request.required_outcome_bytes
            and row['attempt_index'] == self._attempt.as_dict()['attempt_index'],
            'CPU_EXECUTION_ATTEMPT_CHANGED')
        require(self._deadline(metadata) == self._intent_deadline, 'CPU_EXECUTION_INTENT_DEADLINE_CHANGED')
        basis_wire = metadata['basis_wire'].encode('utf8')
        basis, grant, prepared = read_basis(basis_wire, k._codec)
        proposal = owned_cpu_proposal(k._codec, request)
        selected = k._selected(proposal, basis, grant, prepared)
        current = k._snapshot(tuple(cells) + selected)
        require(all(current[key] == value for key, value in cells.items()), 'CPU_EXECUTION_CANONICAL_CHANGED')
        require(k._present(current, basis_key(request.scope_id, request.proposal_id)) == basis_wire,
            'CPU_EXECUTION_BASIS_CHANGED')
        k._validate(proposal, basis_wire, peer, current)
        positions = (k._store.position(request.scope_id), k._store.store_position())
        return current, positions

    def _deadline(self, metadata):
        value = metadata['deadline']
        require(type(value) is dict and set(value) == set(Deadline.__dataclass_fields__), 'DEADLINE_REQUIRED')
        deadline = Deadline(**value)
        require(self._supplied.as_dict()['expires_at'] == deadline_text(deadline.expires_wall_ns)
            and (self._permit is None or self._permit.as_dict()['expires_at'] == self._supplied.as_dict()['expires_at']),
            'CPU_EXECUTION_PERMIT_DEADLINE_MISMATCH')
        return deadline

    def _prepared_identity(self):
        """Bind the canonical target before a retained callback can request Stop."""
        k, permit = self._owner.kernel, self._supplied.as_dict()
        key = StoreKey('permit', permit['scope_id'], permit['record_id'])
        intent = intent_key(permit['scope_id'], permit['record_id'])
        cells = k._snapshot((key, intent))
        require(k._present(cells, key) == self._supplied.canonical_wire,
            'CPU_EXECUTION_PREPARATION_CHANGED')
        metadata = read_intent(k._present(cells, intent))
        require(metadata['scope_id'] == permit['scope_id'] and metadata['permit_id'] == permit['record_id']
            and metadata['state'] == 'INTENT_COMMITTED' and metadata['consumption'] is None,
            'CPU_EXECUTION_PREPARATION_CHANGED')
        basis, grant, prepared = read_basis(metadata['basis_wire'].encode('utf8'), k._codec)
        require(basis['proposal_wire'].encode('utf8') == owned_cpu_proposal(k._codec, self._request).canonical_wire
            and metadata['grant_key'] == grant.as_dict() and grant.record_id == permit['grant_ref']
            and grant.scope_id in (self._request.scope_id, k._installation),
            'CPU_EXECUTION_PREPARATION_CHANGED')
        self._intent_deadline = self._deadline(metadata)
        self._selected_grant = grant

    def _check(self, phase):
        self._owned()
        k = self._owner.kernel
        started = self._owner.elapsed()
        peer = k._peer(self._context)
        require((peer.principal_id, peer.session_id) == (self._request.principal_id, self._request.actor_session),
            'CPU_EXECUTION_PEER_CHANGED')
        previous, sample = k._clock()
        previous, sample = (ClockSample(**{n:getattr(v,n) for n in ClockSample.__dataclass_fields__})
                            for v in (previous, sample))
        if self._owner.highwater is not None: require_clock_progress(self._owner.highwater, sample)
        deadlines = (self._request.deadline,) + (() if self._intent_deadline is None else (self._intent_deadline,))
        for deadline in deadlines: require_deadline_current(deadline, previous, sample)
        if self._clock_anchor is None: self._clock_anchor = sample
        require(self._binding_check(self._capture, self._request) is None, 'CPU_EXECUTION_NATIVE_BINDING_DENIED')
        if phase == 'DISPATCH':
            # Consumption and the exact attempt/history were audited before
            # yield. Under this retained single-writer owner, compare every
            # audited dependency cell and both canonical heads, rather than
            # replaying the same immutable history again inside native Set.
            cells = k._snapshot(tuple(self._cells))
            positions = (k._store.position(self._request.scope_id), k._store.store_position())
            require(cells == self._cells and positions == self._positions
                and self._owner.generation == self._generation, 'CPU_EXECUTION_CANONICAL_CHANGED')
        # The qualified owner retains its native/authority/capacity view.
        # Include the trusted capacity mark in this same measured interval;
        # after it only elapsed accounting and the pure final decision remain.
        callback_started = self._owner.elapsed()
        require(self._current(phase, self._request, self._permit, self._attempt,
            self._binding, self._capture, self._proof, peer, self._context) is None,
            'CPU_EXECUTION_OWNER_DECISION_INVALID')
        if phase == 'DISPATCH':
            from ceta.identity.owner_session import NativeCpuOwnerSession
            if (isinstance(self._owner.owners, NativeCpuOwnerSession)
                    or self._outcome_capacity is not None
                    or getattr(self._owner.store, '_capacity_active', None) is not None):
                require(type(self._outcome_capacity) is _RetainedCpuOutcomeCapacity,
                    'CPU_EXECUTION_PHYSICAL_CAPACITY_REQUIRED')
                _RetainedCpuOutcomeCapacity.mark_dispatch(self._outcome_capacity, self)
        finished = self._owner.elapsed()
        elapsed = finished-started+2*self._owner.resolution
        try:
            _require_timing(finished-callback_started+2*self._owner.resolution,
                self._owner.resolution, phase, 'CPU_EXECUTION_OWNER_TOO_SLOW')
        except ContractError as timing:
            if self._owner.active is self and not self._closed and self._owner.stopped.is_set():
                raise ContractError('CPU_EXECUTION_STOPPED') from timing
            raise
        total_elapsed = finished-self._admission_started+2*self._owner.resolution
        require(elapsed <= self._request.maximum_duration_ns, 'CPU_EXECUTION_CHECK_WINDOW_EXCEEDED')
        wall_budget = self._request.operation_budget.values[BUDGET_FIELDS.index('wall_time_ms')]*1_000_000
        require(total_elapsed <= wall_budget, 'CPU_EXECUTION_ADMISSION_WINDOW_EXCEEDED')
        # Charge the entire retained admission, including time between checks.
        # A fresh native sample may advance farther; a stalled sample cannot
        # reset the measured admission horizon. Max avoids double-charging
        # all elapsed time onto every genuinely fresh native sample.
        monotonic_bound = max(sample.monotonic_ns+elapsed,self._clock_anchor.monotonic_ns+total_elapsed)
        wall_bound = max(sample.latest_wall_ns+elapsed,self._clock_anchor.latest_wall_ns+total_elapsed)
        for deadline in deadlines:
            require(monotonic_bound < deadline.expires_monotonic_ns and wall_bound < deadline.expires_wall_ns,
                'CPU_EXECUTION_DEADLINE_ELAPSED')
        require(0 <= monotonic_bound-self._request.expected_limit.observed_monotonic_ns
            <= self._request.maximum_observation_age_ns, 'CPU_EXECUTION_OBSERVATION_STALE')
        require(self._request.canonical_wire == self._wire, 'CPU_EXECUTION_INPUT_CHANGED')
        self._owner.highwater = sample
        self._owned()

    def __enter__(self):
        require(threading.get_ident() == self._thread, 'CPU_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        require(not self._used, 'CPU_EXECUTION_SINGLE_USE')
        self._used = True
        owner, k = self._owner, self._owner.kernel
        require(callable(owner.retain), 'CPU_EXECUTION_NATIVE_OWNER_UNAVAILABLE')
        require(k._store is owner.store and getattr(owner.store,'_lock',None) is owner.stop_lock
            and type(owner.stop_lock) is type(threading.RLock()), 'CPU_EXECUTION_STOP_STORE_UNAVAILABLE')
        require(isinstance(self._target, WindowsOwnedProcess) and callable(self._binding_check) and callable(self._arguments),
            'CPU_EXECUTION_NATIVE_BINDING_REQUIRED')
        try:
            owner.require_available()
            self._admission_started = owner.elapsed()
            self._prepared_identity()
            owner.claim_liveness(self)
            peer = k._peer(self._context)
            self._manager = owner.retain(self._request, self._supplied, self._binding,
                self._capture, self._proof, peer, self._context, owner)
            enter, self._exit = getattr(self._manager, '__enter__', None), getattr(self._manager, '__exit__', None)
            require(callable(enter) and callable(self._exit), 'CPU_EXECUTION_RETAINER_REQUIRED')
            self._entry_attempted = True
            self._retained = enter(); self._entered = True
            self._current = getattr(self._retained, 'require_current', None)
            require(callable(self._current), 'CPU_EXECUTION_CURRENT_CAPABILITY_REQUIRED')
            _require_timing(owner.elapsed()-self._admission_started+2*owner.resolution,
                owner.resolution, 'ENTRY', 'CPU_EXECUTION_ENTRY_TOO_SLOW')
            self._check('CAPACITY')
            require(not owner.stopped.is_set(), 'CPU_EXECUTION_STOPPED')
            self._consumption_attempted = True
            consumed = owner.call(self, 'consume', self._supplied.canonical_wire, self._context)
            self._permit = k._decode(consumed.record_wire, 'OperationPermit')
            self._consumption = k._resolve_consumption(self._permit, peer=peer)
            intent = intent_key(self._request.scope_id, self._permit.record_id)
            metadata = read_intent(k._present(k._snapshot((intent,)), intent))
            require(self._intent_deadline == self._deadline(metadata)
                and self._selected_grant == StoreKey(**metadata['grant_key']),
                'CPU_EXECUTION_PREPARATION_CHANGED')
            self._check('CONSUMED')
            self._attempt = owner.call(self, 'begin_owned_cpu_attempt', self._wire,
                self._permit.canonical_wire, self._proof, self._context)
            require(self._attempt.as_dict()['state'] == 'ATTEMPT_COMMITTED', 'CPU_EXECUTION_FRESH_ATTEMPT_REQUIRED')
            self._cells, self._positions = self._canonical()
            self._generation = owner.generation
            self._native_arguments = self._arguments(self._capture, self._request)
            arguments = self._native_arguments
            require(type(arguments) is CpuDriverArguments and arguments.driver_domain == DRIVER_DOMAIN
                and arguments.identity == self._request.process_identity
                and arguments.request_commitment == self._request.input_commitment
                and arguments.expected.identity == self._request.process_identity
                and arguments.expected.job_digest == self._request.job_digest
                and arguments.expected.limit == self._request.expected_limit.limit
                and arguments.expected.version == self._request.expected_limit.version,
                'CPU_EXECUTION_DRIVER_BINDING_INVALID')
            require(all(type(v) is int and 1 <= v <= MAX_INTEGER for v in
                (arguments.deadline_monotonic_ns,arguments.maximum_age_ns,
                 arguments.maximum_duration_ns,arguments.capture_sequence)), 'CPU_EXECUTION_DRIVER_BOUNDS_INVALID')
            self._argument_facts = _argument_key(arguments)
            name = 'apply_cpu_rate_limit' if self._request.operation == CAP_OPERATION else 'restore_cpu_rate_limit'
            self._effect = getattr(self._target, name, None)
            require(callable(self._effect) and getattr(self._effect, '__self__', None) is self._target
                and getattr(self._effect, '__func__', None) is (_APPLY if self._request.operation == CAP_OPERATION else _RESTORE),
                'CPU_EXECUTION_NATIVE_EFFECT_UNAVAILABLE')
            self._check('READY')
            require(not owner.stopped.is_set(), 'CPU_EXECUTION_STOPPED')
            return self
        except BaseException as primary:
            # Recover facts only; a committed consumption/attempt must never be
            # turned into a fresh dispatch by retrying the failed command.
            try:
                require(self._consumption_attempted, 'CPU_EXECUTION_NO_CONSUMPTION_ATTEMPT')
                saved = k.recover_permit(self._supplied.canonical_wire, self._context)
                if saved.as_dict()['status'] == 'CONSUMED':
                    self._permit = saved
                    self._consumption = k._resolve_consumption(saved, peer=k._peer(self._context))
                    self._attempt = k.recover_owned_cpu_outcome(self._wire, saved.canonical_wire, self._context)
            except BaseException:
                pass  # Original failure and exact retained owner remain exposed.
            self._finish(type(primary), primary, BaseException.__dict__['__traceback__'].__get__(primary))
            _expose(primary, self)
            raise

    def driver_arguments(self):
        self._owned()
        require(not self._dispatch and self._native_arguments is not None, 'CPU_EXECUTION_ALREADY_ADMITTED')
        value = self._native_arguments
        require(_argument_key(value) == self._argument_facts, 'CPU_EXECUTION_DRIVER_ARGUMENTS_CHANGED')
        return replace(value,identity=replace(value.identity),expected=replace(value.expected,
            identity=replace(value.expected.identity),limit=None if value.expected.limit is None else replace(value.expected.limit)))

    def dispatch_fence(self):
        self._owned()
        require(self._dispatching and not self._dispatch, 'CPU_EXECUTION_FENCE_NOT_ARMED')
        self._check('DISPATCH')
        require(_argument_key(self._native_arguments) == self._argument_facts, 'CPU_EXECUTION_DRIVER_ARGUMENTS_CHANGED')
        # All fallible callbacks have finished. Stop and dispatch admission
        # linearize on the same short lock. WT4 then checks retained native
        # fields and executes its sole Set without another external callback.
        with self._owner.decision:
            require(not self._owner.stopped.is_set(), 'CPU_EXECUTION_STOPPED')
            require(self._owner.active is self and self._owner.generation == self._generation,
                'CPU_EXECUTION_CANONICAL_CHANGED')
            self._dispatch = True
        return None

    def dispatch(self):
        """Call only this exact captured WT4 operation, target and intended limit."""
        self._owned()
        require(not self._called and not self._dispatching, 'CPU_EXECUTION_SINGLE_DISPATCH')
        request = decode_owned_cpu_request(self._wire)
        arguments = self.driver_arguments()
        effect = self._effect
        require(getattr(effect, '__self__', None) is self._target
            and getattr(effect, '__func__', None) is (_APPLY if request.operation == CAP_OPERATION else _RESTORE),
            'CPU_EXECUTION_NATIVE_EFFECT_CHANGED')
        expected = arguments.expected
        keywords = dict(arguments.keyword_arguments)
        keywords['dispatch_fence'] = self.dispatch_fence
        positional = (request.request_id, arguments.identity, expected, request.target_limit)
        if request.operation != CAP_OPERATION:
            positional = (request.request_id, request.restoration_of, arguments.identity,
                          expected, request.original_limit)
        self._called = self._dispatching = True
        try:
            change = effect(*positional, **keywords)
            self._change = change
            require(self._dispatch and type(change) is CpuRateChange, 'CPU_EXECUTION_NATIVE_RESULT_INVALID')
            change.__post_init__()
            require(change.identity == request.process_identity and change.job_digest == request.job_digest,
                'CPU_EXECUTION_NATIVE_RESULT_CHANGED')
            if request.operation == CAP_OPERATION:
                require(change.operation_id == request.request_id and change.intended == request.target_limit,
                    'CPU_EXECUTION_NATIVE_RESULT_CHANGED')
            else:
                require(change.operation_id == request.restoration_of and change.restoration_id == request.request_id
                    and change.before == request.original_limit, 'CPU_EXECUTION_NATIVE_RESULT_CHANGED')
            return change
        except BaseException as primary:
            try:
                data = BaseException.__dict__['__dict__'].__get__(primary)
                pending = dict.get(data, 'cpu_rate_change', self._target._cpu_change)
                if type(pending) is CpuRateChange: self._change = pending
            except BaseException:
                pass
            _expose(primary, self)
            raise
        finally:
            self._dispatching = False

    def cancel(self):
        self._owner.cancel(self)

    def record_outcome(self, receipt_wire, observation_wire, native_proof):
        self._owned()
        require(self._dispatch, 'CPU_EXECUTION_DISPATCH_NOT_ADMITTED')
        # Existing ET3 authenticates independent native outcome proof and
        # accounts cumulative evidence. Stop never refunds consumed liability.
        self._outcome = self._owner.call(self, 'record_owned_cpu_outcome', self._wire,
            self._permit.canonical_wire, receipt_wire, observation_wire, native_proof, self._context)
        return self._outcome

    def inspection(self):
        """Read-only custody/facts, not a replacement execution capability."""
        return dict(consumed_permit=None if self._permit is None else self._permit.canonical_wire,
            consumption=self._consumption,attempt=self._attempt,outcome=self._outcome,native_change=self._change,
            dispatch_admitted=self._dispatch,closed=self._closed,pending_cleanup=self._pending_cleanup,
            retained_native_owner=self._retained,entry_manager=self._manager,cleanup_failure=self._cleanup_failure,
            outcome_capacity=self._outcome_capacity,
            stopped=self._owner.stopped.is_set(),native_effect='UNESTABLISHED_BY_ADMISSION')

    def _finish(self, kind, primary, traceback):
        secondary = None
        try:
            if self._entry_attempted and not self._entered:
                # Failed entry may have acquired custody before raising. Its
                # manager remains exposed; do not guess that exit is replayable.
                self._pending_cleanup = True
            if self._entered:
                self._entered = False
                require(self._exit(kind, primary, traceback) is None, 'CPU_EXECUTION_EXIT_DECISION_INVALID')
        except BaseException as error:
            self._pending_cleanup = True
            self._cleanup_failure = secondary = error
        finally:
            with self._owner.decision:
                self._closed = not self._pending_cleanup
            if self._closed:
                try:
                    self._owner.release_liveness(self)
                except BaseException as error:
                    self._pending_cleanup = True
                    self._closed = False
                    self._cleanup_failure = secondary = error
        if primary is not None:
            _expose(primary, self)
        elif secondary is not None:
            _expose(secondary, self)
            raise secondary

    def __exit__(self, kind, primary, traceback):
        self._owned()
        self._finish(kind, primary, traceback)
        return None

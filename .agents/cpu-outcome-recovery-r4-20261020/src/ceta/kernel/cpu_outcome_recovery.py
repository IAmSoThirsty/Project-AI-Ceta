"""Recovery of one original CPU invocation; never new effect authority."""
from dataclasses import dataclass
import threading
import uuid

from ceta.contracts.kernel_transactions import require
from ceta.contracts.wire import ContractError, canonical_bytes


class _NoCopy:
    def __copy__(self): raise ContractError('CPU_RECOVERY_COPY_FORBIDDEN')
    def __deepcopy__(self, memo): raise ContractError('CPU_RECOVERY_COPY_FORBIDDEN')
    def __reduce_ex__(self, protocol): raise ContractError('CPU_RECOVERY_SERIALIZATION_FORBIDDEN')


@dataclass(frozen=True, slots=True)
class _PendingOutcome(_NoCopy):
    execution: object
    kernel: object
    context: object
    inputs: tuple
    expected: tuple
    entries: tuple
    checks: tuple
    changes: tuple
    cells: tuple
    position: object
    state: str

    def retry(self, kernel, inputs, guard):
        from ceta.identity.cpu_outcome_capacity import _RetainedCpuOutcomeCapacity
        execution = self.execution
        execution._owned()
        require(kernel is self.kernel and kernel._cpu_execution.active is execution
            and execution._pending_transaction is self and execution._context is self.context
            and type(inputs) is tuple and inputs == self.inputs,
            'CPU_RECOVERY_EXACT_PENDING_OUTCOME_REQUIRED')
        capacity = execution._outcome_capacity
        require(type(capacity) is _RetainedCpuOutcomeCapacity and capacity.execution is execution
            and capacity.journal is kernel._store, 'CPU_RECOVERY_CAPACITY_CHANGED')
        capacity.require_current('OUTCOME', execution._request, execution._permit,
            self.context, execution._owner)
        require(capacity.lease.retained_payloads() == tuple(e.payload_wire for e in self.entries),
            'CPU_RECOVERY_RETAINED_BYTES_CHANGED')
        guard()
        if kernel._store.store_position() == self.position:
            # The actual same writer still enforces original heads and all CAS.
            kernel._store.commit(self.expected, self.entries, checks=self.checks,
                changes=self.changes, guard=guard)
        else:
            # A COMMIT may precede an interrupted notification. Authenticate
            # history AND the exact store transaction before acknowledging it.
            kernel._store._recover_capacity_commit(capacity.lease, self.expected,
                self.entries, self.checks, self.changes, self.cells, self.position, guard)
        require(capacity.lease.durable, 'CPU_RECOVERY_DURABLE_OUTCOME_REQUIRED')
        execution._pending_transaction = None


def retain_outcome_transaction(kernel, inputs, expected, entries, checks, changes, cells, state):
    """Capture final canonical bytes before staging or attempting COMMIT."""
    execution = kernel._cpu_execution.active
    if execution is None or execution._outcome_capacity is None:
        return None  # The existing independent domain owner port is unchanged.
    execution._owned()
    require(execution._pending_transaction is None, 'CPU_RECOVERY_PENDING_TRANSACTION_EXISTS')
    require(execution._outcome_capacity.state == 'DURABLE_READBACK'
        or not execution._outcome_capacity.lease.durable,
        'CPU_CAPACITY_RECONCILIATION_RESERVATION_REQUIRED')
    value = _PendingOutcome(execution, kernel, execution._context, inputs, expected,
        entries, checks, changes, tuple(cells.values()), kernel._store.store_position(), state)
    execution._pending_transaction = value
    return value


@dataclass(frozen=True, slots=True)
class _DeniedDispatch(_NoCopy):
    execution: object
    effect: object
    target: object
    arguments: tuple
    request_wire: bytes
    permit_wire: bytes
    attempt_wire: bytes
    context: object
    thread: int
    primary: BaseException
    receipt_wire: bytes

    def require_current(self, execution, receipt, observation, proof, context, retained):
        from .cpu_execution import _argument_key, _APPLY, _RESTORE
        from ceta.contracts.real_effect import CAP_OPERATION
        require(execution._denied_dispatch is self and proof is self
            and execution is self.execution and context is self.context
            and execution._context is self.context and threading.get_ident() == self.thread
            and execution._thread == self.thread and execution._retained is retained
            and retained.lease is execution and execution._target is self.target
            and execution._effect is self.effect and execution._called and not execution._dispatch
            and not execution._dispatching and execution._wire == self.request_wire
            and execution._permit.canonical_wire == self.permit_wire
            and execution._attempt.projection_wire == self.attempt_wire
            and _argument_key(execution._native_arguments) == self.arguments
            and getattr(self.effect, '__self__', None) is self.target
            and getattr(self.effect, '__func__', None) is
                (_APPLY if execution._request.operation == CAP_OPERATION else _RESTORE)
            and observation is None and receipt.canonical_wire == self.receipt_wire,
            'CPU_RECOVERY_DENIAL_ORIGIN_CHANGED')
        return None


def capture_denial(execution, effect, primary):
    """Called only inside the captured WT4 call's exception boundary."""
    from .cpu_execution import _argument_key
    execution._owned()
    require(execution._called and execution._dispatching and not execution._dispatch
        and execution._effect is effect and execution._denied_dispatch is None
        and execution._attempt is not None and execution._permit is not None
        and _argument_key(execution._native_arguments) == execution._argument_facts,
        'CPU_RECOVERY_DENIAL_NOT_ESTABLISHED')
    request, permit = execution._request, execution._permit
    event = execution._attempt.as_dict()['attempt_index']['event_id']
    wire = canonical_bytes(dict(record_type='ExecutionReceipt', schema_version='1',
        record_id='receipt:' + uuid.uuid4().hex, scope_id=request.scope_id,
        causation_ref=event, task_id=request.task_id, operation_id=request.request_id,
        permit_ref=permit.record_id, plan_node_ref=None, executor_session=request.actor_session,
        input_commitment=permit.as_dict()['input_commitment'], dispatch_event_ref=event,
        started_at=None, finished_at=None, exit_code=None, output_ref=None,
        output_commitment=None, changed_resource_claims=[], error_refs=[],
        cancellation_state='REQUESTED' if execution._owner.stopped._flag else 'NONE',
        effect_status='NOT_STARTED', attestation_ref=None))
    wire = execution._owner.kernel._codec.decode(wire).canonical_wire
    execution._denied_dispatch = _DeniedDispatch(execution, effect, execution._target,
        execution._argument_facts, execution._wire, permit.canonical_wire,
        execution._attempt.projection_wire, execution._context, execution._thread, primary, wire)


@dataclass(frozen=True, slots=True)
class _EntryRetirement(_NoCopy):
    borrows: tuple
    error: object


def retire_failed_entry(execution, context):
    """Retire proven-empty unconfigured capacity entry, without consumption."""
    from ceta.identity.owner_session import _NativeCpuExecutionRetainer, _NativeLifecycleBorrow
    from ceta.identity.cpu_outcome_capacity import _RetainedCpuOutcomeCapacity
    execution._owned()
    retained, capacity, kernel = execution._manager, execution._outcome_capacity, execution._owner.kernel
    require(context is execution._context and execution._recovery is None
        and execution._entry_attempted and not execution._entered and execution._retained is None
        and execution._pending_cleanup and not execution._consumption_attempted
        and execution._permit is None and execution._attempt is None and not execution._called
        and not execution._dispatch and not execution._dispatching
        and len(execution._recovery_history) < 32
        and all(b.retired for previous in execution._recovery_history for b in previous.borrows),
        'CPU_RECOVERY_EMPTY_ENTRY_REQUIRED')
    require(type(retained) is _NativeCpuExecutionRetainer and retained.lease is execution
        and retained.state == 'FAILED' and retained.pending and retained.exit_attempted
        and retained.capacity_entry_attempted and not retained.capacity_entered
        and all(b.retired for b in retained._lock_borrows)
        and type(capacity) is _RetainedCpuOutcomeCapacity and retained.capacity_manager is capacity
        and capacity.retainer is retained and capacity.state == 'FAILED' and capacity.lease is None
        and capacity.journal is kernel._store and kernel._store._capacity_vfs is None
        and kernel._store._capacity_active is None,
        'CPU_RECOVERY_EMPTY_CAPACITY_UNPROVED')
    retained._selected()
    borrows = []
    primary = None
    try:
        retained.state = 'ACTIVE'
        for lock in (retained.binding._lock, retained.target._lock):
            borrow = _NativeLifecycleBorrow(lock, execution._thread)
            borrows.append(borrow)
            require(borrow.acquire(), 'CPU_RECOVERY_NATIVE_BUSY')
        retained._pure(bookkeeping=True)
        permit = kernel.recover_permit(execution._supplied.canonical_wire, context)
        require(permit.canonical_wire == execution._supplied.canonical_wire
            and permit.as_dict()['status'] == 'PREPARED', 'CPU_RECOVERY_PREPARED_PERMIT_CHANGED')
        retained._pure(bookkeeping=True)
    except BaseException as error:
        primary = error
    finally:
        for borrow in reversed(borrows):
            try: borrow.retire()
            except BaseException as error:
                retained.cleanup_errors.append(error)
                if primary is None: primary = error
        retained.state = 'FAILED'
    execution._recovery_history += (_EntryRetirement(tuple(borrows), primary),)
    if primary is not None:
        dict.update(BaseException.__dict__['__dict__'].__get__(primary),
            owned_cpu_execution=execution, cpu_entry_recovery_borrows=tuple(borrows))
        raise primary
    capacity.state, retained.state = 'CLOSED', 'CLOSED'
    retained.pending = execution._pending_cleanup = False
    retained.owner._execution, retained.owner._effect_busy = None, False
    execution._closed = True
    try:
        execution._owner.release_liveness(execution)
    except BaseException as primary:
        execution._closed = False
        execution._pending_cleanup = retained.pending = True
        retained.state = 'FAILED'
        retained.cleanup_errors.append(primary)
        dict.__setitem__(BaseException.__dict__['__dict__'].__get__(primary), 'owned_cpu_execution', execution)
        raise
    return execution.inspection()


class _CpuOutcomeRecovery(_NoCopy):
    """Original-context, same-thread bookkeeping borrow with no dispatch lane."""
    def __init__(self, execution, context):
        self.execution, self.context = execution, context
        self.used = self.entered = False
        self.borrows = []
        self.errors = []

    def __enter__(self):
        from ceta.identity.owner_session import _NativeCpuExecutionRetainer, _NativeLifecycleBorrow
        from ceta.identity.cpu_outcome_capacity import _RetainedCpuOutcomeCapacity
        lease = self.execution
        require(not self.used and threading.get_ident() == lease._thread
            and self.context is lease._context, 'CPU_RECOVERY_ORIGINAL_CONTEXT_REQUIRED')
        self.used = True
        require(lease._recovery is None and lease._used and not lease._dispatching
            and lease._called and (lease._dispatch or lease._denied_dispatch is not None)
            and lease._permit is not None and lease._attempt is not None
            and len(lease._recovery_history) < 32,
            'CPU_RECOVERY_ORIGINAL_ATTEMPT_REQUIRED')
        retained, capacity = lease._retained, lease._outcome_capacity
        require(type(retained) is _NativeCpuExecutionRetainer and lease._manager is retained
            and type(capacity) is _RetainedCpuOutcomeCapacity and retained.capacity is capacity
            and capacity.retainer is retained and capacity.execution is lease,
            'CPU_RECOVERY_ORIGINAL_CUSTODY_REQUIRED')
        require(not lease._entered and retained.exit_attempted
            and retained.state in ('FAILED', 'CLOSED')
            and all(b.retired for b in retained._lock_borrows)
            and all(b.retired for previous in lease._recovery_history for b in previous.borrows)
            and capacity.lease is not None,
            'CPU_RECOVERY_UNCERTAIN_RETIREMENT')
        if retained.state == 'FAILED':
            require(not lease._closed and lease._pending_cleanup and retained.pending
                and capacity.state == 'PENDING' and capacity.lease.state in ('ACTIVE', 'PENDING')
                and not capacity.lease.release_attempted, 'CPU_RECOVERY_UNCERTAIN_RETIREMENT')
        else:
            require(lease._closed and capacity.state == 'CLOSED' and capacity.lease.durable,
                'CPU_RECOVERY_DURABLE_PREVIOUS_OUTCOME_REQUIRED')
            prior = lease._owner.kernel.recover_owned_cpu_outcome(lease._wire,
                lease._permit.canonical_wire, self.context)
            require(prior.as_dict()['state'] in ('UNCERTAIN', 'DISCREPANCY'),
                'CPU_RECOVERY_RECONCILABLE_OUTCOME_REQUIRED')
        # Every subsequent failure leaves the original kernel/owner custody
        # visible. The old exit and old lock borrows are never called again.
        lease._recovery = self
        try:
            if lease._closed:
                lease._owner.claim_recovery_liveness(lease)
                lease._closed = False
                require(retained.owner._execution is None and not retained.owner._effect_busy,
                    'CPU_RECOVERY_OWNER_BUSY')
                retained.owner._execution, retained.owner._effect_busy = retained, True
            else:
                lease._owned()
                require(lease._pending_cleanup and retained.pending and capacity.state == 'PENDING'
                    and capacity.lease.state in ('ACTIVE', 'PENDING'), 'CPU_RECOVERY_PENDING_CUSTODY_REQUIRED')
            retained._selected()
            retained.state = 'ACTIVE'
            for lock in (retained.binding._lock, retained.target._lock):
                borrow = _NativeLifecycleBorrow(lock, lease._thread)
                self.borrows.append(borrow)
                require(borrow.acquire(), 'CPU_RECOVERY_NATIVE_BUSY')
            retained._pure(bookkeeping=True)
            capacity.resume_bookkeeping()
            # Existing native provenance requires an active retained borrow.
            # Original errors stay on their objects; these booleans describe
            # this explicit recovery borrow only, with dispatch permanently off.
            lease._entered, lease._pending_cleanup = True, False
            retained.pending = False
            self.entered = True
            return lease
        except BaseException as primary:
            if lease._owner.active is lease:
                self._retire(primary)
            else:
                lease._recovery = None
            raise

    def _retire(self, primary=None):
        lease, errors = self.execution, []
        retained, capacity = lease._retained, lease._outcome_capacity
        try:
            if self.entered:
                capacity.finish_bookkeeping()
        except BaseException as error:
            errors.append(error)
        for borrow in reversed(self.borrows):
            try:
                borrow.retire()
            except BaseException as error:
                errors.append(error)
        complete = (self.entered and not errors and capacity.state == 'CLOSED'
            and capacity.lease.durable and lease._pending_transaction is None)
        lease._entered = False
        lease._pending_cleanup = retained.pending = not complete
        retained.state = 'CLOSED' if complete else 'FAILED'
        if complete:
            retained.owner._execution, retained.owner._effect_busy = None, False
            lease._closed = True
            try:
                lease._owner.release_liveness(lease)
            except BaseException as error:
                errors.append(error)
                lease._closed = False
                lease._pending_cleanup = retained.pending = True
                retained.state = 'FAILED'
                complete = False
        if not complete:
            if not errors: errors.append(ContractError('CPU_RECOVERY_DURABLE_OUTCOME_PENDING'))
            retained.cleanup_errors.extend(errors)
            if retained.cleanup_error is None: retained.cleanup_error = errors[0]
            lease._cleanup_failure = errors[0]
        self.errors.extend(errors)
        lease._recovery_history += (self,)
        lease._recovery = None
        if primary is not None:
            data = BaseException.__dict__['__dict__'].__get__(primary)
            dict.update(data, owned_cpu_execution=lease, cpu_outcome_recovery=self,
                cpu_outcome_recovery_errors=tuple(errors))
        elif errors:
            raise errors[0]

    def __exit__(self, kind, primary, trace):
        require(self.entered and self.execution._recovery is self
            and threading.get_ident() == self.execution._thread, 'CPU_RECOVERY_NOT_OWNED')
        self._retire(primary)
        return None

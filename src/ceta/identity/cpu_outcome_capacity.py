"""Bind the existing physical reservation to one canonical CPU invocation.

This is volatile custody on the selected SqliteJournal, never authority or a
second writer. Native observation/provenance remains the owner's responsibility.
"""
import threading
from types import TracebackType

from ceta.contracts.kernel_transactions import require
from ceta.contracts.real_effect import OwnedCpuRequest
from ceta.contracts.wire import ContractError, ParsedRecord
from ceta.store.journal import SqliteJournal
from ceta.store.outcome_capacity import OutcomeCapacityBudget, OutcomeCapacityLease


def _expose(primary, binding, secondary=None):
    data = BaseException.__dict__['__dict__'].__get__(primary)
    dict.update(data, owned_cpu_capacity=binding, outcome_capacity_custody=binding.lease)
    if secondary is not None:
        dict.__setitem__(data, 'owned_cpu_capacity_cleanup_error', secondary)


class _RetainedCpuOutcomeCapacity:
    """Single-use, original-thread adapter used by NativeCpuOwnerSession."""
    __slots__ = ('view', 'journal', 'budget', 'budget_fields', 'request', 'wire', 'prepared', 'prepared_wire',
        'context', 'coordinator', 'kernel', 'owner', 'execution', 'retainer', 'thread',
        'store_binding', 'registry', 'clock', 'lease', 'state', 'exit_attempted', 'cleanup_error', 'previous_leases')

    def __init__(self, view, request, prepared, context, coordinator):
        require(type(request) is OwnedCpuRequest and type(prepared) is ParsedRecord,
            'CPU_CAPACITY_CANONICAL_INPUT_REQUIRED')
        budget = getattr(view, '_outcome_budget', None)
        require(type(budget) is OutcomeCapacityBudget, 'CPU_CAPACITY_CONFIGURATION_REQUIRED')
        budget.__post_init__()
        require(budget.memory_bytes >= request.required_outcome_bytes,
            'CPU_CAPACITY_FULL_OUTCOME_SLOT_REQUIRED')
        self.view, self.budget, self.request, self.prepared = view, budget, request, prepared
        self.budget_fields = (budget.database_bytes, budget.wal_bytes, budget.shm_bytes, budget.memory_bytes)
        self.wire, self.prepared_wire = request.canonical_wire, prepared.canonical_wire
        self.context, self.coordinator = context, coordinator
        self.kernel, self.journal, self.owner = coordinator.kernel, coordinator.store, coordinator.owners
        self.execution, self.retainer = coordinator.active, coordinator.owners._execution
        self.store_binding, self.registry, self.clock = view._store, view._registry, view._clock
        self.thread, self.state, self.exit_attempted = threading.get_ident(), 'NEW', False
        self.lease = self.cleanup_error = None
        self.previous_leases = ()
        self._selected()
        require(prepared is self.execution._supplied and request is self.execution._request
            and prepared.as_dict()['status'] == 'PREPARED', 'CPU_CAPACITY_PREPARATION_CHANGED')

    def _selected(self):
        # Local imports avoid a construction-time cycle with the canonical kernel.
        from ceta.identity.native_owner_view import NativeOwnerView, NativeStoreBinding
        from ceta.identity.owner_session import NativeCpuOwnerSession, _NativeCpuExecutionRetainer
        from ceta.kernel.transactions import KernelTransactions
        from ceta.kernel.cpu_execution import _CpuExecutionCoordinator, _RetainedCpuExecution
        require(threading.get_ident() == self.thread, 'CPU_CAPACITY_ORIGINAL_THREAD_REQUIRED')
        owner, kernel, coordinator, execution = self.owner, self.kernel, self.coordinator, self.execution
        require(type(self.view) is NativeOwnerView and type(owner) is NativeCpuOwnerSession
            and owner._view is self.view and type(kernel) is KernelTransactions
            and kernel._owners is owner and owner._preparation_kernel is kernel
            and type(coordinator) is _CpuExecutionCoordinator and kernel._cpu_execution is coordinator
            and coordinator.kernel is kernel and coordinator.owners is owner
            and coordinator.store is self.journal and kernel._store is self.journal
            and type(execution) is _RetainedCpuExecution and coordinator.active is execution
            and execution._owner is coordinator and execution._thread == self.thread
            and execution._context is self.context and not execution._closed,
            'CPU_CAPACITY_CANONICAL_OWNER_CHANGED')
        require(type(self.journal) is SqliteJournal and not self.journal._closed
            and not self.journal._read_only and self.journal._codec is kernel._codec
            and type(self.store_binding) is NativeStoreBinding and not self.store_binding.closed
            and self.journal.path == self.store_binding._database_path
            and self.view._store is self.store_binding and self.view._registry is self.registry
            and self.view._clock is self.clock and self.view._outcome_budget is self.budget
            and (self.budget.database_bytes, self.budget.wal_bytes, self.budget.shm_bytes,
                 self.budget.memory_bytes) == self.budget_fields
            and coordinator.stop_lock is self.journal._lock, 'CPU_CAPACITY_STORE_CHANGED')
        require(type(self.retainer) is _NativeCpuExecutionRetainer and owner._execution is self.retainer
            and self.retainer.owner is owner and self.retainer.lease is execution
            and self.retainer.context is self.context and self.retainer.coordinator is coordinator
            and self.retainer.state in ('ENTERING', 'ACTIVE')
            and execution._wire == self.wire and execution._supplied.canonical_wire == self.prepared_wire,
            'CPU_CAPACITY_RETAINER_CHANGED')

    def __enter__(self):
        self._selected()
        require(self.state == 'NEW' and self.execution._outcome_capacity is None,
            'CPU_CAPACITY_SINGLE_USE_REQUIRED')
        self.state = 'ENTERING'
        # Publish recoverable adapter custody before the VFS reservation begins.
        self.execution._outcome_capacity = self
        try:
            self.lease = SqliteJournal.reserve_outcome_capacity(self.journal, self.budget)
            require(type(self.lease) is OutcomeCapacityLease, 'CPU_CAPACITY_LEASE_REQUIRED')
            require(OutcomeCapacityLease.__enter__(self.lease) is self.lease,
                'CPU_CAPACITY_ENTRY_RESULT_INVALID')
            self.state = 'ACTIVE'
            self.require_current('CAPACITY', self.request, None, self.context, self.coordinator)
            return self
        except BaseException as primary:
            self.state = 'FAILED'
            _expose(primary, self)
            raise

    def _active(self):
        self._selected()
        require(self.state in ('ACTIVE', 'DURABLE_READBACK') and self.execution._outcome_capacity is self
            and type(self.lease) is OutcomeCapacityLease and self.lease.journal is self.journal
            and self.lease.budget is self.budget and
            (self.journal._capacity_active is self.lease if self.state == 'ACTIVE' else
                self.execution._recovery is not None and self.lease.state == 'CLOSED'
                and self.lease.durable and self.journal._capacity_active is None),
            'CPU_CAPACITY_LEASE_CHANGED')

    def require_current(self, phase, request, permit, context, coordinator):
        self._active()
        require(type(phase) is str and phase in ('CAPACITY', 'ADMISSION', 'CONSUMED', 'ATTEMPT', 'READY', 'DISPATCH', 'OUTCOME')
            and type(request) is OwnedCpuRequest and request.canonical_wire == self.wire
            and context is self.context and coordinator is self.coordinator,
            'CPU_CAPACITY_INPUT_CHANGED')
        execution = self.execution
        if phase == 'CAPACITY':
            require(permit is None and execution._permit is None and not execution._consumption_attempted,
                'CPU_CAPACITY_PHASE_CHANGED')
        elif phase == 'ADMISSION':
            require(type(permit) is ParsedRecord and permit.record_type == 'OperationPermit'
                and permit.canonical_wire == self.prepared_wire == execution._supplied.canonical_wire
                and permit.as_dict()['status'] == 'PREPARED'
                and execution._consumption_attempted and execution._permit is None
                and execution._attempt is None and not execution._called
                and not execution._dispatching and execution._recovery is None,
                'CPU_CAPACITY_PHASE_CHANGED')
        else:
            require(type(permit) is ParsedRecord and execution._permit is not None
                and permit.canonical_wire == execution._permit.canonical_wire
                and permit.as_dict()['status'] == 'CONSUMED', 'CPU_CAPACITY_PERMIT_CHANGED')
        if phase == 'OUTCOME':
            require((execution._dispatch or execution._denied_dispatch is not None)
                and execution._called and not execution._dispatching
                and self.lease.may_have_executed, 'CPU_CAPACITY_OUTCOME_BEFORE_DISPATCH')
            if self.state == 'DURABLE_READBACK': return None
        else:
            require(not execution._dispatch and not self.lease.may_have_executed,
                'CPU_CAPACITY_DISPATCH_ALREADY_MARKED')
        # The approved method uses its preallocated native-state buffer only.
        OutcomeCapacityLease.require_current(self.lease)
        return None

    def mark_dispatch(self, execution):
        self._active()
        require(execution is self.execution and execution._called and execution._dispatching
            and not execution._dispatch and execution._attempt is not None,
            'CPU_CAPACITY_DISPATCH_NOT_ARMED')
        self.require_current('DISPATCH', self.request, execution._permit, self.context, self.coordinator)
        # Conservative mark precedes the short final Stop/dispatch decision.
        # A subsequent denial retains capacity for explicit reconciliation.
        OutcomeCapacityLease.mark_may_have_executed(self.lease)

    def stage_outcome(self, payloads):
        self._active()
        if self.state == 'DURABLE_READBACK':
            self._reserve_reconciliation()
        self.require_current('OUTCOME', self.request, self.execution._permit, self.context, self.coordinator)
        require(not self.lease.durable, 'CPU_CAPACITY_RECONCILIATION_RESERVATION_REQUIRED')
        OutcomeCapacityLease.stage_outcome(self.lease, payloads)

    def __exit__(self, kind, primary, trace):
        self._active()
        require(not self.exit_attempted and ((primary is None and kind is None and trace is None)
            or (isinstance(primary, BaseException) and kind is type(primary)
                and (trace is None or type(trace) is TracebackType))), 'CPU_CAPACITY_EXIT_INVALID')
        self.exit_attempted = True
        try:
            OutcomeCapacityLease.__exit__(self.lease, kind, primary, trace)
        except BaseException as secondary:
            self.state, self.cleanup_error = 'PENDING', secondary
            if primary is not None:
                _expose(primary, self, secondary)
                raise primary
            _expose(secondary, self)
            raise
        self.state = 'CLOSED'
        return None

    def resume_bookkeeping(self):
        """Resume retained bytes or allocate a fresh same-writer reconciliation slot."""
        self._selected()
        require(self.execution._recovery is not None and self.exit_attempted
            and self.execution._called and not self.execution._dispatching,
            'CPU_RECOVERY_BOOKKEEPING_REQUIRED')
        old = self.lease
        if self.state == 'PENDING':
            require(old.state in ('ACTIVE', 'PENDING') and old.may_have_executed
                and not old.release_attempted and self.journal._capacity_active is old,
                'CPU_RECOVERY_UNCERTAIN_CAPACITY_RELEASE')
            OutcomeCapacityLease.require_current(old)
            self.state = 'ACTIVE'
            return
        require(self.state == 'CLOSED' and old.state == 'CLOSED' and old.durable
            and self.journal._capacity_active is None and self.execution._pending_transaction is None,
            'CPU_RECOVERY_DURABLE_PREVIOUS_OUTCOME_REQUIRED')
        # An exact retry remains read-only and needs no new reservation. Only
        # the canonical writer's final new settlement will allocate capacity.
        self.state = 'DURABLE_READBACK'

    def _reserve_reconciliation(self):
        require(self.state == 'DURABLE_READBACK' and self.execution._recovery is not None,
            'CPU_RECOVERY_BOOKKEEPING_REQUIRED')
        old = self.lease
        self.previous_leases += (old,)
        self.state = 'ENTERING'
        try:
            self.lease = SqliteJournal.reserve_outcome_capacity(self.journal, self.budget)
            OutcomeCapacityLease.__enter__(self.lease)
            # This is custody for a past admitted operation, never a new Set.
            OutcomeCapacityLease.mark_may_have_executed(self.lease)
            self.state = 'ACTIVE'
        except BaseException as primary:
            self.state, self.cleanup_error = 'PENDING', primary
            _expose(primary, self)
            raise

    def finish_bookkeeping(self):
        self._active()
        try:
            require(self.execution._recovery is not None, 'CPU_RECOVERY_BOOKKEEPING_REQUIRED')
            if self.state == 'DURABLE_READBACK':
                require(self.execution._pending_transaction is None,
                    'CPU_RECOVERY_DURABLE_OUTCOME_REQUIRED')
                self.state = 'CLOSED'
                return
            if not self.lease.durable:
                # Existing lease exit preserves the original pending bytes.
                OutcomeCapacityLease.__exit__(self.lease, None, None, None)
            require(self.lease.durable and self.execution._pending_transaction is None,
                'CPU_RECOVERY_DURABLE_OUTCOME_REQUIRED')
            if self.lease.state == 'PENDING':
                OutcomeCapacityLease.finish_reconciliation(self.lease)
            else:
                OutcomeCapacityLease.__exit__(self.lease, None, None, None)
        except BaseException as primary:
            self.state, self.cleanup_error = 'PENDING', primary
            _expose(primary, self)
            raise
        self.state = 'CLOSED'

    def __copy__(self): raise ContractError('CPU_CAPACITY_COPY_FORBIDDEN')
    def __deepcopy__(self, memo): raise ContractError('CPU_CAPACITY_COPY_FORBIDDEN')
    def __reduce_ex__(self, protocol): raise ContractError('CPU_CAPACITY_SERIALIZATION_FORBIDDEN')


def stage_owned_cpu_outcome(kernel, payloads):
    """Bind final ET payloads to the capacity held by this kernel invocation."""
    execution = kernel._cpu_execution.active
    capacity = None if execution is None else execution._outcome_capacity
    if capacity is None and getattr(kernel._store, '_capacity_active', None) is None:
        # Independent domain callers retain their original owner contract.
        # The concrete CPU dispatch fence requires this adapter before Set.
        return
    require(type(capacity) is _RetainedCpuOutcomeCapacity and capacity.kernel is kernel
        and capacity.execution is execution and capacity.journal is kernel._store,
        'CPU_CAPACITY_OUTCOME_OWNER_REQUIRED')
    _RetainedCpuOutcomeCapacity.stage_outcome(capacity, payloads)

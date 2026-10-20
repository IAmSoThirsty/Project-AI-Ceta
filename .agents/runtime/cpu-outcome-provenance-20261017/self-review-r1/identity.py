"""Retained provenance for the canonical CPU producer and native observer.

Only an active, dispatched kernel lease can produce a receipt here. This
volatile owner holds original objects; it creates no permission or durable
state. The existing kernel alone writes and settles the outcome.
"""
from dataclasses import dataclass
import threading
import uuid

from ceta.contracts.kernel_transactions import PeerIdentity, require
from ceta.contracts.real_effect import CAP_OPERATION, CpuEffectObservation, OwnedCpuRequest
from ceta.contracts.wire import ContractError, ParsedRecord, canonical_bytes
from ceta.contracts.workload_throttling import CpuRateChange
from ceta.effects.native_observer import NativeCpuEffectObserver
from ceta.kernel.cpu_execution import _CpuExecutionCoordinator, _RetainedCpuExecution
from ceta.kernel.effect_transactions import OwnedCpuOutcome
from ceta.kernel.transactions import KernelTransactions
from ceta.store.journal import SqliteJournal
from .native_owner_view import NativeOwnerView
from .owner_session import NativeCpuOwnerSession, _NativeCpuExecutionRetainer

_OBSERVE = NativeCpuEffectObserver.observe
_ORIGIN = NativeCpuEffectObserver.require_observation_origin


def _change_facts(change, request):
    if change is None:
        return None
    require(type(change) is CpuRateChange, 'CPU_OUTCOME_CHANGE_TYPE_INVALID')
    change.__post_init__()
    require(change.identity == request.process_identity and change.job_digest == request.job_digest,
            'CPU_OUTCOME_CHANGE_TARGET_CHANGED')
    if request.operation == CAP_OPERATION:
        require(change.operation_id == request.request_id and change.intended == request.target_limit
                and change.before == request.original_limit and change.restoration_id is None,
                'CPU_OUTCOME_CHANGE_OPERATION_CHANGED')
    else:
        require(change.operation_id == request.restoration_of and change.restoration_id == request.request_id
                and change.before == request.original_limit,
                'CPU_OUTCOME_CHANGE_OPERATION_CHANGED')
    observed = change.observed
    return (change.operation_id, change.identity.pid, change.identity.creation_time,
        change.identity.image_digest, change.job_digest, change.before.control_flags, change.before.value,
        change.intended.control_flags, change.intended.value, change.state, change.reason, change.restoration_id,
        None if observed is None else (observed.identity.pid, observed.identity.creation_time,
            observed.identity.image_digest, observed.job_digest, observed.state.value,
            None if observed.limit is None else (observed.limit.control_flags, observed.limit.value),
            observed.version, observed.observed_monotonic_ns, observed.reason))


@dataclass(frozen=True, slots=True)
class CpuOutcomeCapture:
    """Transport data and a local opaque token; neither is standalone proof."""
    receipt_wire: bytes
    observation_wire: bytes | None
    proof: object
    observation_error: BaseException | None


class _Producer:
    """Private original references and immutable snapshots for one admission."""
    def __init__(self, lease, view):
        self.lease, self.view = lease, view
        self.coordinator, self.kernel = lease._owner, lease._owner.kernel
        self.owner, self.store = self.kernel._owners, self.kernel._store
        self.retained, self.context, self.thread = lease._retained, lease._context, lease._thread
        self.target, self.binding, self.capture = lease._target, lease._binding, lease._capture
        self.request, self.permit, self.attempt = lease._request, lease._permit, lease._attempt
        self.wire, self.permit_wire = lease._wire, lease._permit.canonical_wire
        self.attempt_wire, self.consumption = lease._attempt.projection_wire, lease._consumption
        self.peer = (self.retained.peer.principal_id, self.retained.peer.session_id)
        self.change, self.change_facts = lease._change, _change_facts(lease._change, self.request)
        p, attempt = self.permit.as_dict(), self.attempt.as_dict()
        event = attempt['attempt_index']['event_id']
        # Dispatch admission cannot establish whether Set took effect. Even a
        # reported APPLIED/RESTORED result still needs the independent observer.
        self.receipt = self.kernel._codec.decode(canonical_bytes(dict(
            record_type='ExecutionReceipt', schema_version='1', record_id='receipt:' + uuid.uuid4().hex,
            scope_id=self.request.scope_id, causation_ref=event, task_id=self.request.task_id,
            operation_id=self.request.request_id, permit_ref=self.permit.record_id, plan_node_ref=None,
            executor_session=self.request.actor_session, input_commitment=p['input_commitment'],
            dispatch_event_ref=event, started_at=None, finished_at=None, exit_code=None,
            output_ref=None, output_commitment=None, changed_resource_claims=[], error_refs=[],
            cancellation_state='REQUESTED' if self.coordinator.stopped._flag else 'NONE',
            effect_status='MAY_HAVE_EXECUTED', attestation_ref=None)))
        self.receipt_wire = self.receipt.canonical_wire
        self.last_sequence = self.last_monotonic = None
        self.observer_image = None


class NativeCpuOutcomeProvenance:
    """One same-view producer and observer binding, with fail-closed origin checks."""
    def __init__(self, view, observer):
        require(type(view) is NativeOwnerView and type(observer) is NativeCpuEffectObserver
                and observer._clock is view._clock, 'CPU_OUTCOME_NATIVE_COMPOSITION_REQUIRED')
        self._view, self._observer = view, observer
        self._configuration = (observer._executable, observer._image, observer._commitment,
                               observer._driver_sha, observer._clock)
        self._lock = threading.Lock()
        self._producer = self._proof = self._observation = self._observation_wire = None
        self._observation_error = None

    def _lease(self, lease, *, dispatched):
        require(type(lease) is _RetainedCpuExecution, 'CPU_OUTCOME_ORIGINAL_LEASE_REQUIRED')
        coordinator, kernel = lease._owner, lease._owner.kernel
        owner, retained, view = kernel._owners, lease._retained, self._view
        require(type(coordinator) is _CpuExecutionCoordinator and type(kernel) is KernelTransactions
                and type(owner) is NativeCpuOwnerSession and type(retained) is _NativeCpuExecutionRetainer
                and type(kernel._store) is SqliteJournal, 'CPU_OUTCOME_CANONICAL_OWNERS_REQUIRED')
        require(getattr(view, '_cpu_outcome', None) is self and owner._view is view
                and owner._preparation_kernel is kernel and kernel._cpu_execution is coordinator
                and coordinator.kernel is kernel and coordinator.owners is owner
                and coordinator.store is kernel._store and coordinator.active is lease
                and coordinator.stop_lock is kernel._store._lock and not kernel._store._closed
                and not kernel._store._read_only and kernel._store._codec is kernel._codec
                and kernel._store.path == view._store._database_path,
                'CPU_OUTCOME_CANONICAL_BINDING_CHANGED')
        require(lease._entered and not lease._closed and not lease._pending_cleanup
                and lease._thread == threading.get_ident() and retained.thread == lease._thread
                and retained.state == 'ACTIVE' and not retained.pending
                and retained is owner._execution and lease._manager is retained
                and retained.owner is owner and retained.coordinator is coordinator
                and retained.kernel is kernel and retained.lease is lease
                and retained.context is lease._context and owner._dispatch is retained.dispatch
                and retained.dispatch[0] is lease._context and retained.dispatch[1] == lease._thread
                and retained.target is lease._target and retained.binding is lease._binding
                and retained.capture is lease._capture and retained.proof is lease._proof,
                'CPU_OUTCOME_RETAINED_CUSTODY_CHANGED')
        require(type(lease._request) is OwnedCpuRequest and lease._request.canonical_wire == lease._wire == retained.wire
                and type(lease._permit) is ParsedRecord and lease._permit.record_type == 'OperationPermit'
                and lease._permit.as_dict()['status'] == 'CONSUMED' and lease._consumption is not None
                and lease._consumption.consumed_permit_wire == lease._permit.canonical_wire
                and type(lease._attempt) is OwnedCpuOutcome
                and lease._attempt.as_dict()['state'] == 'ATTEMPT_COMMITTED',
                'CPU_OUTCOME_CONSUMED_ATTEMPT_REQUIRED')
        require(type(retained.peer) is PeerIdentity
                and (retained.peer.principal_id, retained.peer.session_id) ==
                    (lease._request.principal_id, lease._request.actor_session),
                'CPU_OUTCOME_ORIGINAL_PEER_CHANGED')
        require(not lease._dispatching and (lease._dispatch and lease._called if dispatched else not lease._called),
                'CPU_OUTCOME_DISPATCH_PHASE_INVALID')
        observer = self._observer
        require(type(observer) is NativeCpuEffectObserver and self._configuration ==
                (observer._executable, observer._image, observer._commitment, observer._driver_sha, observer._clock)
                and observer._clock is view._clock and view._clock is owner._native_clock
                and observer._commitment == lease._request.observer_commitment,
                'CPU_OUTCOME_OBSERVER_BINDING_CHANGED')
        return None

    def require_ready(self, lease):
        """Structural check only; dispatch performs the actual admission gate."""
        return self._lease(lease, dispatched=False)

    def _current(self, producer):
        lease = producer.lease
        self._lease(lease, dispatched=True)
        require(producer.view is self._view and producer.coordinator is lease._owner
                and producer.kernel is lease._owner.kernel and producer.owner is producer.kernel._owners
                and producer.store is producer.kernel._store and producer.retained is lease._retained
                and producer.context is lease._context and producer.thread == lease._thread
                and producer.target is lease._target and producer.binding is lease._binding
                and producer.capture is lease._capture and producer.request is lease._request
                and producer.wire == lease._wire and producer.permit is lease._permit
                and producer.permit_wire == lease._permit.canonical_wire and producer.attempt is lease._attempt
                and producer.attempt_wire == lease._attempt.projection_wire and producer.consumption is lease._consumption
                and producer.change is lease._change and producer.change_facts == _change_facts(lease._change, lease._request)
                and producer.receipt.canonical_wire == producer.receipt_wire
                and producer.peer == (producer.retained.peer.principal_id, producer.retained.peer.session_id),
                'CPU_OUTCOME_PRODUCER_CHANGED')

    def collect(self, lease):
        """Observe through the captured implementation; keep the first receipt immutable."""
        require(self._lock.acquire(blocking=False), 'CPU_OUTCOME_BUSY')
        try:
            self._lease(lease, dispatched=True)
            if self._producer is None or self._producer.lease is not lease:
                require(self._producer is None or self._producer.lease._closed,
                        'CPU_OUTCOME_OTHER_PRODUCER_ACTIVE')
                self._producer = _Producer(lease, self._view)
            producer = self._producer
            self._current(producer)
            # A failed refresh never leaves an earlier proof current.
            self._proof = self._observation = self._observation_wire = self._observation_error = None
            try:
                observation = _OBSERVE(self._observer, producer.request, producer.target)
                require(type(observation) is CpuEffectObservation, 'CPU_OUTCOME_OBSERVATION_TYPE_INVALID')
                _ORIGIN(self._observer, producer.request, producer.target, observation)
                if producer.last_sequence is not None:
                    require(observation.sequence > producer.last_sequence
                            and observation.clock.monotonic_ns > producer.last_monotonic
                            and observation.observer_identity.image_digest == producer.observer_image,
                            'CPU_OUTCOME_OBSERVATION_REPLAY')
                self._observation, self._observation_wire = observation, observation.canonical_wire
                producer.last_sequence, producer.last_monotonic = observation.sequence, observation.clock.monotonic_ns
                producer.observer_image = observation.observer_identity.image_digest
            except BaseException as error:
                self._observation_error = error
            self._current(producer)
            self._proof = object()
            return CpuOutcomeCapture(producer.receipt_wire, self._observation_wire,
                                     self._proof, self._observation_error)
        finally:
            self._lock.release()

    def require_current(self, view, request, permit, receipt, observation, proof, peer, context, retained):
        """Pure repeated callback: no SQL, authentication, native observation or effects."""
        require(self._lock.acquire(blocking=False), 'CPU_OUTCOME_BUSY')
        try:
            producer = self._producer
            require(view is self._view and producer is not None and self._proof is not None
                    and proof is self._proof, 'CPU_OUTCOME_ORIGINAL_PROOF_REQUIRED')
            self._current(producer)
            require(retained is producer.retained and context is producer.context
                    and type(peer) is PeerIdentity and (peer.principal_id, peer.session_id) == producer.peer
                    and type(request) is OwnedCpuRequest and request.canonical_wire == producer.wire
                    and type(permit) is ParsedRecord and permit.record_type == 'OperationPermit'
                    and permit.canonical_wire == producer.permit_wire
                    and type(receipt) is ParsedRecord and receipt.record_type == 'ExecutionReceipt'
                    and receipt.canonical_wire == producer.receipt_wire,
                    'CPU_OUTCOME_DECODED_BINDING_CHANGED')
            if self._observation is None:
                require(observation is None and self._observation_wire is None
                        and self._observation_error is not None, 'CPU_OUTCOME_UNOBSERVED_DATA_REQUIRED')
            else:
                require(type(observation) is CpuEffectObservation
                        and observation.canonical_wire == self._observation_wire == self._observation.canonical_wire,
                        'CPU_OUTCOME_OBSERVATION_BYTES_CHANGED')
                _ORIGIN(self._observer, producer.request, producer.target, self._observation)
            self._current(producer)
            return None
        finally:
            self._lock.release()

    def __copy__(self): raise ContractError('CPU_OUTCOME_OWNER_COPY_FORBIDDEN')
    def __deepcopy__(self, memo): raise ContractError('CPU_OUTCOME_OWNER_COPY_FORBIDDEN')
    def __reduce_ex__(self, protocol): raise ContractError('CPU_OUTCOME_OWNER_SERIALIZATION_FORBIDDEN')

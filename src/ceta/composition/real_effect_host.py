"""Selected Windows ingress for one bounded genuine manual CPU operation.

The trusted parent supplies deployment and peer registrations, never the wire
caller. A RUN request holds its original native pipe context across enrollment,
exact display/approval, canonical preparation, dispatch, observation and settlement.
RESTORE uses a fresh command context and genuine approval over the original cap.
"""
import secrets
import threading

from ceta.composition.real_effect_runtime import ManualRealEffectProfile, ManualRuntimeSelection
from ceta.contracts.kernel_transactions import require
from ceta.contracts.local_ipc import LocalMessage
from ceta.contracts.local_results import encode_response
from ceta.contracts.manual_effect import OPERATIONS
from ceta.contracts.wire import ContractError, RecordCodec
from ceta.identity.windows_pipe import WindowsPipeServer


class ManualRealEffectHost:
    def __init__(self, selection, codec, pipe_name, *, peer_pid, peer_creation_time,
                 peer_image_sha256, principal_id, actor_session):
        require(type(selection) is ManualRuntimeSelection and type(codec) is RecordCodec,
            'MANUAL_HOST_TRUSTED_SELECTION_REQUIRED')
        self._thread, self.run_id = threading.get_ident(), 'run:' + secrets.token_hex(16)
        self.profile = self.receiver = None
        self._cap_session = self._last_session = None
        self._pending = None
        self._stopped = False
        try:
            self.profile = object.__new__(ManualRealEffectProfile)
            ManualRealEffectProfile.__init__(self.profile, selection, codec)
            self.profile.registry.register(peer_pid, principal_id, actor_session,
                allowed_operations=tuple(OPERATIONS), allowed_scopes=(selection.scope_id,),
                expected_creation_time=peer_creation_time, expected_image_sha256=peer_image_sha256)
            self.receiver = object.__new__(WindowsPipeServer)
            WindowsPipeServer.__init__(self.receiver, pipe_name, self.profile.registry, self, codec,
                response_encoder=encode_response, context_retainer=self.retain_context)
        except BaseException as primary:
            self._expose(primary)
            raise

    def _expose(self, primary):
        dict.__setitem__(BaseException.__dict__['__dict__'].__get__(primary),
            'manual_real_effect_host', self)

    def _current(self):
        require(threading.get_ident() == self._thread, 'MANUAL_HOST_ORIGINAL_THREAD_REQUIRED')

    def ready(self):
        self._current()
        return dict(profile='ceta-owned-real-effect-v1', run_id=self.run_id,
            receiver_generation=self.receiver.receiver_generation,
            scope_id=self.profile.selection.scope_id,
            authority='REQUIRES_GENUINE_ENROLLMENT_AND_EXACT_APPROVAL')

    def retain_context(self, original_context):
        """Pure custody lookup, captured by the receiver before dispatch."""
        self._current()
        session = self.profile._session
        if session is not None and session._context is original_context and not session.closed:
            self._pending = session
            return session
        return None

    def __call__(self, message, original_context):
        self._current()
        require(type(message) is LocalMessage and message.operation in OPERATIONS,
            'MANUAL_HOST_OPERATION_UNAVAILABLE')
        self.profile.registry.require_message(original_context, message)
        value = message.record.as_dict()
        require(value['kind'] == OPERATIONS[message.operation]
            and value['run_id'] == self.run_id
            and message.scope_id == self.profile.selection.scope_id,
            'MANUAL_HOST_COMMAND_BINDING')
        require(self._pending is None, 'MANUAL_HOST_ORIGINAL_INVOCATION_PENDING')
        kind = value['kind']
        if kind in ('INSPECT', 'STOP'):
            return self._historical(original_context, stop_reason=value['reason_ref'] if kind == 'STOP' else None)
        if kind == 'RECONCILE':
            # New messages may inspect canonical outcome, but cannot reconstruct
            # a private pending execution lease from serialized request IDs.
            require(self._last_session is not None
                and value['request_id'] == self._last_session._request.request_id,
                'MANUAL_HOST_REQUEST_ID_MISMATCH')
            return self._historical(original_context)
        require(not self._stopped, 'MANUAL_HOST_STOPPED')
        if kind == 'RUN':
            require(self._cap_session is None and self._last_session is None,
                'MANUAL_HOST_CAP_SINGLE_ATTEMPT')
        else:
            require(self._cap_session is not None
                and value['request_id'] == self._cap_session._cap_request.request_id
                and self._last_session is self._cap_session,
                'MANUAL_HOST_ORIGINAL_CAP_REQUIRED')
        session = self.profile.command_session(original_context)
        self._last_session = session  # Publish before context/helper/worker work.
        try:
            with session:
                if kind == 'RUN':
                    session.enroll()
                    session.prepare(cpu_rate=value['cpu_rate'])
                else:
                    original = self._cap_session._cap_request
                    enrollment = session._owner.owner_enrollment_expected(original_context)
                    state = session._kernel.recover_owner_enrollment(enrollment.request_id,
                        original_context).as_dict()
                    require(state['state'] == 'ENROLLED'
                        and state['cap_approval']['request_wire'] == original.canonical_wire.decode('utf8'),
                        'MANUAL_HOST_CANONICAL_CAP_CHANGED')
                    session._enrollment, session._enrollment_stage = enrollment, 'ENROLLED'
                    session._cap_request, session._task_id = original, original.task_id
                    session.prepare(restoration=True)
                request_id = session._request.request_id
                session.approve(request_id)
                # A pending/rejected ceremony cannot reach this state predicate.
                result = session.execute(request_id)
                result['run_id'] = self.run_id
            if kind == 'RUN':
                self._cap_session = session
            return result
        except BaseException as primary:
            self.retain_context(original_context)
            self._expose(primary)
            raise

    def _historical(self, original_context, *, stop_reason=None):
        owner = self.profile.runtime._owner
        kernel = self.profile.runtime.kernel._kernel
        with owner.native_context(original_context):
            session = self._last_session
            enrollment = None if session is None else session._enrollment
            state = None if enrollment is None else kernel.recover_owner_enrollment(
                enrollment.request_id, original_context).as_dict()
            outcome = None
            if session is not None and session._execution is not None:
                permit = session._execution.inspection()['consumed_permit']
                if permit is not None:
                    outcome = kernel.recover_owned_cpu_outcome(session._request.canonical_wire,
                        permit, original_context).as_dict()
            if stop_reason is not None:
                if enrollment is not None:
                    kernel.stop_owner_authority(enrollment.request_id, original_context, stop_reason)
                owner.request_stop()
                self._stopped = True
            return dict(profile='ceta-owned-real-effect-v1', run_id=self.run_id,
                state='STOPPED' if self._stopped else 'HISTORICAL_READBACK',
                enrollment=state, outcome=outcome,
                active_native_context_reconstructed=False)

    def reconcile_pending(self):
        """Trusted original-thread recovery while the SAME context remains live."""
        self._current()
        require(self._pending is not None, 'MANUAL_HOST_NO_PENDING_INVOCATION')
        session = self._pending
        request = session._request if session._request is not None else session._enrollment
        require(request is not None, 'MANUAL_HOST_PRECOMMAND_CUSTODY_PENDING')
        result = session.reconcile(request.request_id)
        session.close()
        require(session.closed, 'MANUAL_HOST_ORIGINAL_INVOCATION_PENDING')
        self.receiver.retire_retained_context()
        self._pending = None
        return result

    def receive_once(self, timeout_seconds=30.0):
        self._current()
        require(type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 30,
            'MANUAL_HOST_RECEIVE_BOUND')
        return self.receiver.receive_once(timeout_seconds)

    def close(self):
        self._current()
        try:
            require(self._pending is None and (self.profile is None or self.profile._session is None),
                'MANUAL_HOST_ORIGINAL_INVOCATION_PENDING')
            if self.receiver is not None:
                self.receiver.close()
            if self.profile is not None:
                self.profile.close()
        except BaseException as primary:
            self._expose(primary)
            raise

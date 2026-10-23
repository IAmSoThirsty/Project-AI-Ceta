"""Native enrollment witness on the captured peer, clock, files and helper.

The canonical kernel issues authority. This owner binds its enrollment ports to
one measured native session and an opaque, locally retained ceremony witness.
The selected CPU subclass bridges preparation and retained admission to committed
canonical approval. Other owners and revocation retain their closed defaults.
"""
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from types import TracebackType
import threading
import math
import time

from ceta.contracts.kernel_transactions import commitment, identifier, require
from ceta.contracts.owner_enrollment import (EnrollmentRequest, decode_enrollment_request,
    enrollment_transcript_bytes, require_enrollment_transcript_binding)
from ceta.contracts.real_effect import NativeApprovalTranscript
from ceta.contracts.temporal import require_clock_progress
from ceta.contracts.wire import ContractError
from ceta.identity.native_approval import (NativeApprovalOwner, NativeApprovalSession,
    NativeApprovalResult, NativeProcessEvidence)
from ceta.identity.native_clock import NativeSessionClock
from ceta.identity.native_code_binding import NativeCodeBinding
from ceta.identity.native_owner_view import NativeOwnerView, _luid_hex
from ceta.identity.owners import WindowsIdentityOwners


def _expose(primary, owner, *, cleanup_error=None):
    data = BaseException.__dict__['__dict__'].__get__(primary)
    dict.update(data, native_owner_session=owner, close_cleanup=owner.close)
    if cleanup_error is not None:
        dict.__setitem__(data, 'native_owner_session_cleanup_error', cleanup_error)
    message = 'Native enrollment-session custody remains available for explicit retirement.'
    if not dict.__contains__(data, '__notes__'):
        dict.__setitem__(data, '__notes__', [message])
    else:
        notes = dict.__getitem__(data, '__notes__')
        if type(notes) is list and all(type(note) is str for note in notes):
            list.append(notes, message)


def _expose_context(primary, guard, boundary_error=None):
    """Keep context errors separate from OS3's exact session-close secondary."""
    data = BaseException.__dict__['__dict__'].__get__(primary)
    # Bind the owned implementation directly; no instance diagnostic hook runs.
    close = NativeOwnerSession.close.__get__(guard._owner, NativeOwnerSession)
    dict.update(data, native_owner_session=guard._owner, close_cleanup=close,
        native_owner_context_guard=guard, native_owner_context_pending=guard._pending,
        native_owner_context_original_traceback=guard._traceback)
    previous = dict.get(data, 'native_owner_context_guards', ())
    if type(previous) is not tuple:
        dict.__setitem__(data, 'native_owner_context_prior_guards', previous)
        previous = ()
    if not any(item is guard for item in previous):
        dict.__setitem__(data, 'native_owner_context_guards', previous+(guard,))
    if boundary_error is not None:
        trace = BaseException.__dict__['__traceback__'].__get__(boundary_error)
        list.append(guard._failures, (boundary_error, trace))
        previous = dict.get(data, 'native_owner_context_boundary_failures', ())
        if type(previous) is not tuple:
            dict.__setitem__(data, 'native_owner_context_prior_failures', previous)
            previous = ()
        dict.__setitem__(data, 'native_owner_context_boundary_failures',
            previous+((boundary_error, trace),))


class _NativeContextGuard:
    """One original-thread entry/exit around an owned generator context."""
    __slots__ = ('_owner', '_context', '_factory', '_thread', '_state', '_manager',
        '_exit', '_pending', '_primary', '_traceback', '_failures', '_fault')

    def __init__(self, owner, original_context, factory):
        self._owner, self._context, self._factory = owner, original_context, factory
        self._thread, self._state = threading.get_ident(), 'NEW'
        self._manager = self._exit = self._primary = self._traceback = self._fault = None
        self._pending, self._failures = False, []

    def _original_thread(self):
        if threading.get_ident() != self._thread:
            error = ContractError('OWNER_SESSION_CONTEXT_ORIGINAL_THREAD_REQUIRED')
            _expose_context(error, self)
            raise error

    def _reject(self, code):
        error = ContractError(code)
        if self._state in ('ENTERING', 'EXITING'): self._fault = error
        _expose_context(error, self)
        raise error

    def __enter__(self):
        self._original_thread()
        if self._state != 'NEW': self._reject('OWNER_SESSION_CONTEXT_SINGLE_USE')
        self._state = 'ENTERING'
        try:
            self._manager = self._factory(self._owner, self._context)
            enter = getattr(self._manager, '__enter__', None)
            self._exit = getattr(self._manager, '__exit__', None)
            require(callable(enter) and callable(self._exit), 'OWNER_SESSION_CONTEXT_MANAGER_REQUIRED')
            result = enter()
        except BaseException as primary:
            self._state, self._pending, self._primary = 'FAILED', True, primary
            self._traceback = BaseException.__dict__['__traceback__'].__get__(primary)
            _expose_context(primary, self)
            raise
        self._state = 'ACTIVE'
        if result is not self._owner or self._fault is not None:
            primary = self._fault or ContractError('OWNER_SESSION_CONTEXT_ENTER_RESULT_INVALID')
            # Entry returned, so this one exit receives the real failure, never
            # an invented success. A failed entry is never blindly exited.
            self.__exit__(type(primary), primary, None)
            self._state = 'FAILED'
            _expose_context(primary, self)
            raise primary
        return result

    def __exit__(self, kind, primary, trace):
        self._original_thread()
        if self._state != 'ACTIVE': self._reject('OWNER_SESSION_CONTEXT_EXIT_ONCE_REQUIRED')
        if not ((primary is None and kind is None and trace is None)
                or (isinstance(primary, BaseException) and kind is type(primary)
                    and (trace is None or type(trace) is TracebackType))):
            self._reject('OWNER_SESSION_CONTEXT_EXCEPTION_ARGUMENTS_INVALID')
        self._state, self._primary = 'EXITING', primary
        self._traceback = None if primary is None else BaseException.__dict__['__traceback__'].__get__(primary)
        error = None
        try:
            result = self._exit(kind, primary, trace)
        except BaseException as failure:
            error = failure
        else:
            if result is not None and result is not False:
                error = ContractError('OWNER_SESSION_CONTEXT_EXIT_DECISION_INVALID')
            elif self._fault is not None:
                error = self._fault
        if error is not None:
            self._pending = True
        if primary is not None:
            data = BaseException.__dict__['__dict__'].__get__(primary)
            if dict.get(data, 'native_owner_session') is self._owner and (
                    dict.__contains__(data, 'native_owner_session_cleanup_error')
                    or dict.get(data, 'native_owner_context_pending') is True):
                self._pending = True
            self._state = 'FAILED' if self._pending else 'CLOSED'
            _expose_context(primary, self, error)
            # contextlib may have touched the original before failing. Restore
            # via the trusted descriptor and let the caller's with re-raise it.
            BaseException.__dict__['__traceback__'].__set__(primary, self._traceback)
            return False
        if error is not None:
            self._state = 'FAILED'
            self._primary = error
            self._traceback = BaseException.__dict__['__traceback__'].__get__(error)
            _expose_context(error, self, error)
            raise error
        self._state = 'CLOSED'
        return False

    def inspection(self):
        return dict(state=self._state, pending_cleanup=self._pending, owner=self._owner,
            original_context=self._context, manager=self._manager, primary=self._primary,
            original_traceback=self._traceback, boundary_failures=tuple(self._failures))

    def __copy__(self):
        raise ContractError('OWNER_SESSION_CONTEXT_COPY_FORBIDDEN')

    def __deepcopy__(self, memo):
        raise ContractError('OWNER_SESSION_CONTEXT_COPY_FORBIDDEN')

    def __reduce_ex__(self, protocol):
        raise ContractError('OWNER_SESSION_CONTEXT_SERIALIZATION_FORBIDDEN')


def _native_context_boundary(factory):
    @wraps(factory)
    def guarded(owner, original_context):
        return _NativeContextGuard(owner, original_context, factory)
    return guarded

def _require_principal(helper, owner):
    # TokenHasRestrictions records whether filtering ever occurred; it is not
    # the restricted-SID count. Ordinary medium-integrity limited UAC tokens
    # may have that flag set and no restricted SIDs. Preserve both facts and
    # require the exact same non-elevated class on the helper and native peer.
    require(type(helper) is NativeProcessEvidence
        and helper.user_sid == owner.user_sid and helper.logon_sid == owner.logon_sid
        and helper.terminal_session == owner.terminal_session
        and _luid_hex(helper.authentication_id) == owner.authentication_luid_hex
        and helper.integrity_sid == owner.integrity_sid == 'S-1-16-8192'
        and helper.integrity_attributes == owner.integrity_attributes
        and helper.elevation_type == owner.elevation_type and owner.elevation_type in (1,3)
        and helper.restricted == bool(owner.has_restrictions)
        and helper.restricted_sid_count == len(owner.restricted_sids) == 0
        and helper.ui_access == owner.ui_access == 0
        and owner.token_type == 1 and owner.impersonation_level == 0,
        'OWNER_SESSION_HELPER_PRINCIPAL_MISMATCH')


class _NativeEnrollmentLease:
    __slots__ = ('owner', 'session', 'context', 'wire', 'active', 'thread')

    def __init__(self, owner, session, context, wire):
        self.owner, self.session, self.context, self.wire = owner, session, context, wire
        self.active, self.thread = True, threading.get_ident()

    def require_current(self, wire, challenge, nonce, helper, context):
        owner, session = self.owner, self.session
        owner._require_dispatch(context)
        require(self.active and self.thread == threading.get_ident()
            and owner._enrollment_lease is self and owner._approval._active is session
            and type(session) is NativeApprovalSession and session._owner is owner._approval
            and session._lease is self and not session._closed and not session._stop.is_set()
            and not owner._stopped.is_set(), 'OWNER_SESSION_ENROLLMENT_LEASE_INVALID')
        require(type(wire) is bytes and wire == self.wire == owner._expected.canonical_wire
            and session._bound_request_wire == wire and session._bound_context is context
            and context is self.context and session.mode == 'interactive' and session._enrollment,
            'OWNER_SESSION_ENROLLMENT_BODY_CHANGED')
        expected = owner._expected
        require(challenge == expected.challenge_id and nonce == expected.ceremony_nonce
            and type(helper) is NativeProcessEvidence and helper == session.helper_evidence
            and helper.identity == expected.helper_identity == expected.ui_identity
            and session.enrollment_binding.helper_commitment == expected.helper_commitment == expected.ui_commitment,
            'OWNER_SESSION_ENROLLMENT_HELPER_CHANGED')
        # A completed helper is deliberately not required to remain live. The
        # native transport observes exit/empty job before publishing its result;
        # its image, process, token and interop custody remain retained here.
        owner._require_native(expected, context, allow_expired=False)
        require(not session._stop.is_set() and not owner._stopped.is_set(), 'OWNER_SESSION_STOPPED')


class _CeremonyWitness:
    __slots__ = ('session', 'context', 'request_wire', 'transcript_wire', 'active')

    def __init__(self, session, context, request_wire, transcript_wire):
        self.session, self.context = session, context
        self.request_wire, self.transcript_wire, self.active = request_wire, transcript_wire, True


class NativeOwnerSession(WindowsIdentityOwners):
    """Concrete enrollment/currentness owner; never a grant issuer or writer."""
    def __init__(self, view, clock, code_binding, *, installation_id, scope_id,
                 policy_commitment, helper_name, helper_source_name, worker_name,
                 temporary_root):
        require(type(view) is NativeOwnerView and type(clock) is NativeSessionClock
            and view._clock is clock and type(code_binding) is NativeCodeBinding,
            'OWNER_SESSION_NATIVE_OWNERS_REQUIRED')
        identifier(installation_id);identifier(scope_id);commitment(policy_commitment)
        require(installation_id != scope_id, 'OWNER_SESSION_SCOPE_INVALID')
        require(Path(temporary_root).resolve(strict=True) == view._store._root_path,
            'OWNER_SESSION_TEMPORARY_ROOT_BINDING_MISMATCH')
        super().__init__(view._registry)
        self._view, self._native_clock, self._code = view, clock, code_binding
        self._installation, self._scope, self._policy = installation_id, scope_id, policy_commitment
        self._lock, self._stopped = threading.RLock(), threading.Event()
        self._closed, self._dispatch, self._expected = False, None, None
        self._enrollment_lease, self._proof, self._anchor = None, None, None
        rows = code_binding.snapshot()
        def entry(group, name):
            require(type(name) is str, 'OWNER_SESSION_MANIFEST_NAME_REQUIRED')
            selected = [row for row in rows if row[0] == group and row[1] == name]
            require(len(selected) == 1, 'OWNER_SESSION_MANIFEST_BINDING_MISSING')
            stored = next(row for row in code_binding._files if row['group'] == group and row['logical_name'] == name)
            return selected[0], stored['path']
        helper, helper_path = entry('environment', helper_name)
        source, _ = entry('source', helper_source_name)
        worker, _ = entry('environment', worker_name)
        self._worker_commitment = 'sha256:' + worker[2]
        self._approval = NativeApprovalOwner(helper_path, helper[2], temporary_root=temporary_root,
            canonical_owner=self, clock_owner=clock, helper_source_commitment='sha256:' + source[2])

    @property
    def approval_owner(self): return self._approval

    @property
    def closed(self): return self._closed

    def clock(self):
        previous,current = self._native_clock.clock()
        # The ceremony interval begins at our measured pre-consent anchor.
        # Intermediate fresh observations must not move its beginning past the
        # retained transcript. NC2 independently maintains its own highwater.
        anchor = previous if self._anchor is None else self._anchor
        require_clock_progress(anchor,current)
        return anchor,current

    def _require_dispatch(self, context):
        held = self._dispatch
        require(not self._closed and held is not None and held[0] is context
            and held[1] == threading.get_ident(), 'OWNER_SESSION_ORIGINAL_DISPATCH_REQUIRED')
        held[2].require_current()
        require(not self._view._store.closed, 'OWNER_SESSION_STORE_CLOSED')
        return self.authenticate(context)

    @_native_context_boundary
    @contextmanager
    def native_context(self, original_context):
        require(self._lock.acquire(blocking=False), 'OWNER_SESSION_BUSY')
        try:
            require(not self._closed and self._dispatch is None, 'OWNER_SESSION_DISPATCH_ALREADY_HELD')
            self.authenticate(original_context)
            self._view._store.require_current()
            with self._code.retained() as code_lease:
                self._dispatch = (original_context, threading.get_ident(), code_lease)
                try:
                    yield self
                finally:
                    if self._proof is not None:self._proof.active = False
                    self._proof = None
                    self._dispatch = None
        finally:
            self._lock.release()

    def _require_native(self, request, context, *, allow_expired):
        peer = self._require_dispatch(context)
        require(type(request) is EnrollmentRequest
            and request.installation_id == self._installation and request.scope_id == self._scope
            and request.policy_commitment == self._policy
            and request.source_commitment == self._code.source_commitment
            and request.environment_commitment == self._code.environment_commitment
            and request.worker_image_commitment == self._worker_commitment,
            'OWNER_SESSION_ENROLLMENT_CONFIGURATION_CHANGED')
        observed = self._view.observe(context)
        require(observed.peer == peer and observed.owner_facts == request.owner_facts
            and observed.private_root == request.private_root and observed.database == request.database,
            'OWNER_SESSION_NATIVE_BINDING_CHANGED')
        if not allow_expired:
            from ceta.contracts.owner_enrollment import require_enrollment_current
            require_enrollment_current(request,request,observed.previous_clock,observed.current_clock)
        # Last external callback above; remaining code is a pure retained fence.
        self._dispatch[2].require_current()
        require(not self._view._store.closed, 'OWNER_SESSION_STORE_CLOSED')
        return observed

    def designate_enrollment(self, request, prepared, original_context):
        self._require_dispatch(original_context)
        require(not self._stopped.is_set() and self._expected is None
            and type(request) is EnrollmentRequest and type(prepared) is NativeApprovalSession
            and prepared is self._approval._active and prepared._owner is self._approval
            and prepared.mode == 'prepared' and not prepared._closed,
            'OWNER_SESSION_ENROLLMENT_DESIGNATION_DENIED')
        frozen = decode_enrollment_request(request.canonical_wire)
        binding = prepared.enrollment_binding
        require((frozen.challenge_id,frozen.ceremony_nonce,frozen.helper_identity,frozen.ui_identity,
                frozen.helper_commitment,frozen.ui_commitment) ==
            (binding.challenge_id,binding.ceremony_nonce,binding.helper.identity,binding.ui_identity,
                binding.helper_commitment,binding.ui_commitment), 'OWNER_SESSION_PREPARATION_MISMATCH')
        observed = self._require_native(frozen,original_context,allow_expired=False)
        _require_principal(binding.helper,frozen.owner_facts)
        self._anchor = observed.current_clock
        self._expected = frozen
        return frozen

    def owner_enrollment_expected(self, original_context):
        self._require_dispatch(original_context)
        require(self._expected is not None, 'OWNER_SESSION_ENROLLMENT_NOT_DESIGNATED')
        return decode_enrollment_request(self._expected.canonical_wire)

    @contextmanager
    def retain_native_enrollment(self, request_wire, original_context):
        self._require_dispatch(original_context)
        require(self._expected is not None and request_wire == self._expected.canonical_wire
            and self._enrollment_lease is None and not self._stopped.is_set(),
            'OWNER_SESSION_ENROLLMENT_LEASE_DENIED')
        session = self._approval._active
        require(type(session) is NativeApprovalSession and session._owner is self._approval,
            'OWNER_SESSION_NATIVE_SESSION_REQUIRED')
        lease = self._enrollment_lease = _NativeEnrollmentLease(self,session,original_context,request_wire)
        try:
            yield lease
        finally:
            lease.active = False
            if self._enrollment_lease is lease:self._enrollment_lease = None

    def retain_verified_enrollment(self, session, original_context):
        """Create an opaque native witness; canonical nonce consumption is later."""
        self._require_dispatch(original_context)
        require(self._expected is not None and self._proof is None and not self._stopped.is_set()
            and type(session) is NativeApprovalSession and session is self._approval._active
            and session._owner is self._approval and session._enrollment
            and session._native_exited and session.native_facts.get('empty_job') is True
            and session.native_facts.get('exit_code') == 0 and not session._closed
            and type(session._result) is NativeApprovalResult and session._result.reported_verified,
            'OWNER_SESSION_GENUINE_CEREMONY_REQUIRED')
        try:
            NativeApprovalSession._require_gate_budget(session)
            transcript = session.transcript()
            NativeApprovalSession._require_gate_budget(session)
            require(type(transcript) is NativeApprovalTranscript, 'OWNER_SESSION_TRANSCRIPT_REQUIRED')
            observed = self._require_native(self._expected,original_context,allow_expired=False)
            NativeApprovalSession._require_gate_budget(session)
            require(self._anchor is not None, 'OWNER_SESSION_CEREMONY_CLOCK_ANCHOR_REQUIRED')
            require_enrollment_transcript_binding(self._expected,self._expected,transcript,
                self._anchor,observed.current_clock)
            NativeApprovalSession._require_gate_budget(session)
            witness = _CeremonyWitness(session,original_context,self._expected.canonical_wire,
                enrollment_transcript_bytes(transcript))
            # Cached verification cannot renew the original helper allowance.
            NativeApprovalSession._require_gate_budget(session)
            require(not session._stop.is_set() and not session._closed and not self._stopped.is_set(),
                'OWNER_SESSION_STOPPED')
            self._proof = witness
            return transcript,witness
        except BaseException as primary:
            NativeApprovalSession._expose(session,primary,())
            raise

    def require_owner_authority_current(self, phase, enrollment, effect_request, transcript,
                                        native_proof, peer, original_context):
        require(type(phase) is str and phase in ('CHALLENGE','ENROLL','STOP','REVOKE','RECOVER'),
            'OWNER_SESSION_EFFECT_OWNER_NOT_COMPOSED')
        require(self._expected is not None and type(enrollment) is EnrollmentRequest
            and enrollment.canonical_wire == self._expected.canonical_wire
            and effect_request is None, 'OWNER_SESSION_EXPECTED_ENROLLMENT_CHANGED')
        observed = self._require_native(enrollment,original_context,allow_expired=phase in ('STOP','REVOKE','RECOVER'))
        require(peer == observed.peer, 'OWNER_SESSION_PEER_CHANGED')
        if phase in ('CHALLENGE','ENROLL'):require(not self._stopped.is_set(), 'OWNER_SESSION_STOPPED')
        if phase == 'ENROLL':
            proof = self._proof
            require(type(proof) is _CeremonyWitness and native_proof is proof and proof.active
                and proof.context is original_context and proof.request_wire == enrollment.canonical_wire
                and type(transcript) is NativeApprovalTranscript
                and proof.transcript_wire == enrollment_transcript_bytes(transcript)
                and proof.session is self._approval._active and not proof.session._closed
                and not proof.session._stop.is_set() and proof.session._result.reported_verified,
                'OWNER_SESSION_NATIVE_WITNESS_REQUIRED')
        self._dispatch[2].require_current()
        if phase in ('CHALLENGE','ENROLL'):require(not self._stopped.is_set(), 'OWNER_SESSION_STOPPED')

    def request_stop(self):
        self._stopped.set()
        self._approval.cancel_current()

    def close(self):
        try:self.request_stop()
        except BaseException as primary:
            _expose(primary,self)
            raise
        require(self._lock.acquire(blocking=False), 'OWNER_SESSION_BUSY')
        try:
            if self._closed:return
            session = self._approval._active
            if session is not None:session.close()
            require(self._approval._active is None and self._enrollment_lease is None,
                'OWNER_SESSION_NATIVE_CUSTODY_PENDING')
            if self._proof is not None:self._proof.active = False
            self._proof = None
            self._closed = True
        except BaseException as primary:
            _expose(primary,self)
            raise
        finally:
            self._lock.release()


class _NativeEffectApprovalLease:
    __slots__ = ('owner','designation','session','context','thread','active','helper','helper_wire')

    def __init__(self, owner, designation, session, context):
        self.owner,self.designation,self.session,self.context = owner,designation,session,context
        self.thread,self.active,self.helper,self.helper_wire = threading.get_ident(),True,None,None

    def require_current(self, wire, challenge, nonce, helper, context):
        from ceta.contracts.wire import canonical_bytes
        owner,session = self.owner,self.session
        with owner._effect_operation(context, retained_current=True):
            require(self.active and owner._effect_lease is self and self.thread == threading.get_ident()
                and context is self.context and session is owner._approval._active
                and session._owner is owner._approval and session._lease is self
                and not session._closed and not session._stop.is_set()
                and session.mode == 'interactive' and not session._enrollment,
                'OWNER_EFFECT_NATIVE_LEASE_INVALID')
            require(type(wire) is bytes and type(challenge) is str and type(nonce) is str
                and wire == self.designation.wire
                and wire == session._bound_request_wire and context is session._bound_context
                and challenge == session.challenge_id and nonce == session.ceremony_nonce,
                'OWNER_EFFECT_NATIVE_BODY_CHANGED')
            require(type(helper) is NativeProcessEvidence and helper is session.helper_evidence,
                'OWNER_EFFECT_NATIVE_HELPER_CHANGED')
            helper_wire = canonical_bytes(helper.as_dict())
            if self.helper is not None:
                require(helper is self.helper and helper_wire == self.helper_wire,
                    'OWNER_EFFECT_NATIVE_HELPER_CHANGED')
            _,observed = owner._require_effect(self.designation,context)
            _require_principal(helper,observed.owner_facts)
            # Pin only actually measured NA2 helper evidence, never a caller DTO.
            if self.helper is None:self.helper,self.helper_wire = helper,helper_wire
            owner._effect_fence(self.designation,session)


class _EffectDesignation:
    __slots__ = ('wire','binding','capture','target','context','thread','serial','active')

    def __init__(self, wire, binding, capture, context, serial):
        self.wire,self.binding,self.capture,self.target = wire,binding,capture,binding._target
        self.context,self.thread,self.serial,self.active = context,threading.get_ident(),serial,True


class _NativeEffectWitness:
    __slots__ = ('designation','session','context','wire','transcript_wire','active')

    def __init__(self, designation, session, context, transcript_wire):
        self.designation,self.session,self.context = designation,session,context
        self.wire,self.transcript_wire,self.active = designation.wire,transcript_wire,True


def _expose_execution(primary, retained, secondary=None):
    try:
        data = BaseException.__dict__['__dict__'].__get__(primary)
        dict.update(data, native_owner_execution=retained, native_owner_session=retained.owner)
        if secondary is not None:
            dict.__setitem__(data, 'native_owner_execution_cleanup_error', secondary)
    except BaseException:
        pass  # Even failed diagnostics may not replace the original exception.


class _NativeLifecycleBorrow:
    """One nonblocking recursive-lock level, registered before acquisition."""
    def __init__(self, lock, thread):
        require(type(lock) is type(threading.RLock()), 'OWNER_EXECUTION_NATIVE_LOCK_REQUIRED')
        require(threading.get_ident() == thread, 'OWNER_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        self.lock, self.thread, self.before = lock, thread, lock._recursion_count()
        self.attempted, self.acquired = False, None
        self.retirement_attempted, self.retired = False, False

    def acquire(self):
        require(not self.attempted, 'OWNER_EXECUTION_LOCK_ACQUIRE_ONCE_REQUIRED')
        require(threading.get_ident() == self.thread, 'OWNER_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        self.attempted = True
        acquired = self.lock.acquire(blocking=False)
        self.acquired = acquired
        return acquired

    def retire(self):
        require(threading.get_ident() == self.thread, 'OWNER_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        require(not self.retirement_attempted, 'OWNER_EXECUTION_LOCK_RETIRE_ONCE_REQUIRED')
        self.retirement_attempted = True
        depth = self.lock._recursion_count()
        if not self.attempted or self.acquired is False:
            require(depth == self.before, 'OWNER_EXECUTION_LOCK_DEPTH_CHANGED')
        elif self.acquired is None and depth == self.before:
            pass  # Interrupted before acquisition completed; no new level exists.
        else:
            require(depth == self.before + 1, 'OWNER_EXECUTION_LOCK_DEPTH_CHANGED')
            self.lock.release()
            require(self.lock._recursion_count() == self.before, 'OWNER_EXECUTION_LOCK_RETIRE_UNPROVED')
        self.retired = True


class _NativeCpuExecutionRetainer:
    """Borrow one existing kernel/native lifetime; never create permission."""
    def __init__(self, owner, request, prepared, binding, capture, proof, peer, context, coordinator):
        self.owner, self.request, self.prepared = owner, request, prepared
        self.binding, self.capture, self.proof = binding, capture, proof
        self.peer, self.context, self.coordinator = peer, context, coordinator
        self.kernel, self.thread = coordinator.kernel, threading.get_ident()
        self.view, self.registry = owner._view, owner._registry
        self.native_store, self.native_clock, self.code = owner._view._store, owner._native_clock, owner._code
        self.lease = coordinator.active
        self.wire, self.prepared_wire = request.canonical_wire, prepared.canonical_wire
        self.designation, self.dispatch = owner._effect, owner._dispatch
        self.proof_session, self.transcript_wire = proof.session, proof.transcript_wire
        self.approval_result = proof.session._result
        self.configuration = (owner._expected.canonical_wire, owner._policy, owner._worker_commitment,
            owner._code.source_commitment, owner._code.environment_commitment)
        self.target, self.lifetime = binding._target, binding._lifetime
        self.capacity_factory = owner._execution_capacity
        self.provenance = owner._execution_provenance
        self.state, self.pending, self.cleanup_error = 'NEW', False, None
        self.capacity_manager = self.capacity = self.capacity_current = self.capacity_exit = None
        self.capacity_entry_attempted = self.capacity_entered = self.exit_attempted = False
        self.locks, self._lock_borrows, self.cleanup_errors = [], [], []
        self.registry_entry = None
        self.admission_basis = self.admission_observed = self.admission_last_tick = None

    def _selected(self):
        from ceta.kernel.transactions import KernelTransactions
        from ceta.kernel.cpu_execution import _CpuExecutionCoordinator, _RetainedCpuExecution
        from ceta.store.journal import SqliteJournal
        owner, kernel, coordinator, lease = self.owner, self.kernel, self.coordinator, self.lease
        require(threading.get_ident() == self.thread, 'OWNER_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        require(type(owner) is NativeCpuOwnerSession and type(kernel) is KernelTransactions
            and owner._preparation_kernel is kernel and kernel._owners is owner
            and type(coordinator) is _CpuExecutionCoordinator and kernel._cpu_execution is coordinator
            and coordinator.owners is owner and coordinator.store is kernel._store
            and type(lease) is _RetainedCpuExecution and coordinator.active is lease
            and lease._owner is coordinator and not lease._closed and lease._thread == self.thread
            and lease._context is self.context and lease._binding is self.binding and lease._target is self.target
            and lease._capture is self.capture and lease._proof is self.proof
            and lease._wire == self.wire and lease._supplied.canonical_wire == self.prepared_wire,
            'OWNER_EXECUTION_CANONICAL_CUSTODY_CHANGED')
        require(owner._view is self.view and owner._registry is self.registry
            and self.view._registry is self.registry and self.view._store is self.native_store
            and owner._native_clock is self.native_clock and self.view._clock is self.native_clock
            and owner._code is self.code, 'OWNER_EXECUTION_NATIVE_OWNER_CHANGED')
        store = kernel._store
        require(type(store) is SqliteJournal and not store._closed and not store._read_only
            and store._codec is kernel._codec and store.path == owner._view._store._database_path
            and not owner._view._store.closed and coordinator.stop_lock is store._lock,
            'OWNER_EXECUTION_STORE_CHANGED')
        require(owner._dispatch is self.dispatch and self.dispatch is not None
            and self.dispatch[0] is self.context and self.dispatch[1] == self.thread
            and owner._effect is self.designation and self.designation.context is self.context
            and self.designation.wire == self.wire and self.designation.binding is self.binding
            and self.designation.capture is self.capture and self.designation.target is self.target
            and self.designation.serial == owner._effect_serial and self.designation.thread == self.thread,
            'OWNER_EXECUTION_ORIGINAL_BINDING_CHANGED')
        require(owner._execution_capacity is self.capacity_factory
            and owner._execution_provenance is self.provenance,
            'OWNER_EXECUTION_DEPENDENCY_CHANGED')

    def _pure(self, *, bookkeeping=False):
        self._selected()
        owner, binding, target, proof = self.owner, self.binding, self.target, self.proof
        require(not owner._closed and owner._execution is self and self.state in ('ENTERING', 'ACTIVE')
            and type(proof) is _NativeEffectWitness and owner._effect_proof is proof
            and proof.designation is self.designation and proof.context is self.context
            and proof.wire == self.wire and proof.session is self.proof_session
            and proof.transcript_wire == self.transcript_wire
            and self.configuration == (owner._expected.canonical_wire, owner._policy, owner._worker_commitment,
                owner._code.source_commitment, owner._code.environment_commitment),
            'OWNER_EXECUTION_APPROVAL_CUSTODY_CHANGED')
        require(type(proof.session) is NativeApprovalSession
            and proof.session is owner._approval._active and proof.session._owner is owner._approval
            and proof.session._bound_context is self.context
            and proof.session._bound_request_wire == self.wire
            and not proof.session._enrollment and proof.session.mode == 'interactive'
            and not proof.session._closed and proof.session._native_exited
            and type(proof.session._result) is NativeApprovalResult and proof.session._result is self.approval_result
            and proof.session._result.reported_verified
            and proof.session.native_facts.get('empty_job') is True
            and proof.session.native_facts.get('exit_code') == 0,
            'OWNER_EXECUTION_GENUINE_APPROVAL_CHANGED')
        record = binding._current
        require(not binding._closed and binding._target is target and binding._clock is owner._native_clock
            and binding._target_fields() == self.lifetime and record is not None
            and record.public is self.capture and self.capture is self.designation.capture
            and not target._closed and target._process is not None and target._job is not None,
            'OWNER_EXECUTION_NATIVE_LIFETIME_CHANGED')
        registry = owner._registry
        require(registry._lock.acquire(blocking=False), 'OWNER_EXECUTION_CONTEXT_BUSY')
        try:
            require(not registry._closed and registry._active.get(self.context) is self.registry_entry
                and self.registry_entry is not None, 'OWNER_EXECUTION_CONTEXT_CHANGED')
        finally: registry._lock.release()
        self.dispatch[2].require_current()  # Existing pure same-thread code lease.
        if not bookkeeping:
            owner._effect_fence(self.designation, proof.session)
            require(proof.active and not self.coordinator.stopped._flag,
                'OWNER_EXECUTION_STOPPED')
        # Bookkeeping deliberately does not compare the old policy/version or
        # revive the inactive approval proof after Set/Stop. Its opaque producer
        # and observer origins must still pass the separately captured predicate.

    def _capture_admission_basis(self):
        """Read the selected canonical preparation before the short writer call."""
        from ceta.contracts.kernel_transactions import basis_key, intent_key, read_basis, read_intent
        from ceta.contracts.store_transactions import StoreKey
        from ceta.kernel.owner_authority import owned_cpu_proposal
        from ceta.store.journal import SqliteJournal
        kernel, lease = self.kernel, self.lease
        require(not kernel._store._connection.in_transaction,
            'OWNER_ADMISSION_WRITER_REENTRY')
        require(all(getattr(getattr(kernel._store, name, None), '__func__', None)
            is getattr(SqliteJournal, name) for name in ('snapshot', 'commit', 'position', 'replay')),
            'OWNER_ADMISSION_STORE_METHOD_CHANGED')
        permit = self.prepared.as_dict()
        key = StoreKey('permit', permit['scope_id'], permit['record_id'])
        intent = intent_key(permit['scope_id'], permit['record_id'])
        prepared = basis_key(permit['scope_id'], permit['proposal_ref'])
        cells = kernel._snapshot((key, intent, prepared))
        metadata = read_intent(kernel._present(cells, intent))
        require(kernel._present(cells, key) == self.prepared_wire
            and metadata['scope_id'] == self.request.scope_id
            and metadata['permit_id'] == permit['record_id']
            and metadata['state'] == 'INTENT_COMMITTED' and metadata['consumption'] is None,
            'OWNER_ADMISSION_PREPARATION_CHANGED')
        wire = metadata['basis_wire'].encode('utf8')
        basis, grant, read_set = read_basis(wire, kernel._codec)
        proposal = owned_cpu_proposal(kernel._codec, self.request)
        require(kernel._present(cells, prepared) == wire
            and basis['proposal_wire'].encode('utf8') == proposal.canonical_wire
            and basis['owner_input_commitment'] == self.request.input_commitment
            and (basis['principal_id'], basis['actor_session']) ==
                (self.peer.principal_id, self.peer.session_id)
            and basis['adapter_commitment'] == self.request.adapter_commitment
            and basis['task_revision'] == self.request.task_revision
            and read_set.scope_id == self.request.scope_id
            and read_set.policy_commitment == self.request.policy_commitment
            and read_set.environment_commitment == self.request.environment_commitment
            and grant == lease._selected_grant
            and grant.as_dict() == metadata['grant_key']
            and grant.record_id == permit['grant_ref']
            and kernel._cpu_execution.active is lease,
            'OWNER_ADMISSION_BASIS_CHANGED')
        self.admission_basis = wire

    def require_admission(self, permit, basis_wire, peer):
        """Repeatable pre/post-COMMIT check over this one consuming lease.

        The kernel alone validates and changes its durable canonical rows. This
        check reads retained facts and the existing reservation's cached native
        state, performs no SQL or fresh OS query, and creates no authority.
        """
        from ceta.contracts.kernel_transactions import PeerIdentity
        from ceta.contracts.local_ipc import LocalMessage
        from ceta.contracts.wire import ParsedRecord
        from ceta.identity.cpu_outcome_capacity import _RetainedCpuOutcomeCapacity
        from ceta.identity.windows_pipe import WindowsPeerRegistry, _Active, WindowsPeerRegistration
        self._pure()
        lease, owner, kernel = self.lease, self.owner, self.kernel
        require(self.state == 'ACTIVE' and lease._entered and lease._manager is self
            and lease._retained is self and not lease._pending_cleanup
            and lease._consumption_attempted and lease._permit is None
            and lease._attempt is None and not lease._dispatch and not lease._dispatching
            and not lease._called and lease._recovery is None
            and getattr(kernel._admission_check, '__self__', None) is owner
            and getattr(kernel._admission_check, '__func__', None) is NativeCpuOwnerSession.require_admission,
            'OWNER_ADMISSION_CONSUMING_LEASE_REQUIRED')
        require(type(permit) is ParsedRecord and permit.record_type == 'OperationPermit'
            and permit.canonical_wire == self.prepared_wire == lease._supplied.canonical_wire
            and permit.as_dict()['status'] == 'PREPARED'
            and type(basis_wire) is bytes and basis_wire == self.admission_basis
            and type(peer) is PeerIdentity and peer == self.peer
            and (peer.principal_id, peer.session_id) ==
                (self.request.principal_id, self.request.actor_session),
            'OWNER_ADMISSION_INPUT_CHANGED')
        registry, active = owner._registry, self.registry_entry
        require(type(registry) is WindowsPeerRegistry and registry is owner._view._registry
            and type(active) is _Active and type(active.entry.registration) is WindowsPeerRegistration
            and type(active.message) is LocalMessage
            and active.thread_id == threading.get_native_id()
            and (active.entry.registration.principal_id, active.entry.registration.session_id) ==
                (peer.principal_id, peer.session_id)
            and active.message.sender_session == peer.session_id
            and active.message.scope_id == self.request.scope_id
            and active.message.operation in active.entry.registration.allowed_operations
            and active.message.scope_id in active.entry.registration.allowed_scopes,
            'OWNER_ADMISSION_ORIGINAL_CONTEXT_REQUIRED')
        require(type(self.capacity) is _RetainedCpuOutcomeCapacity
            and self.capacity is self.capacity_manager
            and getattr(self.capacity_current, '__self__', None) is self.capacity
            and getattr(self.capacity_current, '__func__', None)
                is _RetainedCpuOutcomeCapacity.require_current,
            'OWNER_ADMISSION_RETAINED_CAPACITY_REQUIRED')
        require(self.capacity_current('ADMISSION', self.request, permit, self.context,
            self.coordinator) is None, 'OWNER_ADMISSION_CAPACITY_DECISION_INVALID')
        # No native peer/image/token query, journal read or human callback is
        # made in this predicate. The kernel reauthenticates the real peer.
        monotonic, wall = time.monotonic(), time.time_ns()
        tick = time.perf_counter_ns()
        require(type(monotonic) is float and math.isfinite(monotonic)
            and type(wall) is int and type(tick) is int
            and self.admission_last_tick is not None
            and self.admission_last_tick <= tick, 'OWNER_ADMISSION_TIMER_INVALID')
        self.admission_last_tick = tick
        require(monotonic < active.monotonic_deadline, 'WINDOWS_REQUEST_CONTEXT_EXPIRED')
        require(active.message.issued_at_ms <= wall//1_000_000 < active.message.expires_at_ms,
            'IPC_MESSAGE_EXPIRED_OR_FUTURE')
        elapsed = tick-lease._admission_started+2*self.coordinator.resolution
        require(elapsed >= 0, 'OWNER_ADMISSION_TIMER_INVALID')
        observed = self.admission_observed.current_clock
        monotonic_bound = observed.monotonic_ns+elapsed
        wall_bound = observed.latest_wall_ns+elapsed
        for deadline in (owner._expected.deadline, self.request.deadline, lease._intent_deadline):
            require(deadline is not None and deadline.boot_id == observed.boot_id
                and deadline.durable_epoch == observed.durable_epoch
                and deadline.resume_generation == observed.resume_generation
                and monotonic_bound < deadline.expires_monotonic_ns
                and wall_bound < deadline.expires_wall_ns, 'OWNER_ADMISSION_DEADLINE_ELAPSED')
        require(0 <= monotonic_bound-self.request.expected_limit.observed_monotonic_ns
            <= self.request.maximum_observation_age_ns, 'OWNER_ADMISSION_OBSERVATION_STALE')
        # The final pure fence follows the capacity and independent timer reads.
        _RetainedCpuOutcomeCapacity._active(self.capacity)
        self._pure()
        require(not owner._closed and not owner._stopped._flag
            and not self.coordinator.stopped._flag, 'OWNER_ADMISSION_STOPPED')
        return None

    def __enter__(self):
        require(self.state == 'NEW', 'OWNER_EXECUTION_SINGLE_USE')
        self._selected()
        require(self.owner._execution is None and not self.owner._effect_busy
            and not self.owner._effect_retaining, 'OWNER_EXECUTION_BUSY')
        require(not self.kernel._store._connection.in_transaction,
            'OWNER_EXECUTION_WRITER_REENTRY')
        self.state, self.owner._execution, self.owner._effect_busy = 'ENTERING', self, True
        try:
            for lock in (self.binding._lock, self.target._lock):
                borrow = _NativeLifecycleBorrow(lock, self.thread)
                self._lock_borrows.append(borrow)
                require(borrow.acquire(), 'OWNER_EXECUTION_NATIVE_BUSY')
                self.locks.append(lock)
            self.admission_last_tick = self.lease._admission_started
            _, self.admission_observed = self.owner._require_effect(self.designation, self.context)
            self._capture_admission_basis()
            registry = self.owner._registry
            require(registry._lock.acquire(blocking=False), 'OWNER_EXECUTION_CONTEXT_BUSY')
            try:
                require(not registry._closed, 'OWNER_EXECUTION_CONTEXT_CHANGED')
                self.registry_entry = registry._active.get(self.context)
                require(self.registry_entry is not None, 'OWNER_EXECUTION_CONTEXT_CHANGED')
            finally: registry._lock.release()
            self._pure()
            self.capacity_manager = self.capacity_factory(self.request, self.prepared,
                self.context, self.coordinator)
            enter = getattr(self.capacity_manager, '__enter__', None)
            self.capacity_exit = getattr(self.capacity_manager, '__exit__', None)
            require(callable(enter) and callable(self.capacity_exit), 'OWNER_EXECUTION_CAPACITY_RETAINER_REQUIRED')
            self.capacity_entry_attempted = True
            self.capacity = enter()
            self.capacity_entered = True
            self.capacity_current = getattr(self.capacity, 'require_current', None)
            require(callable(self.capacity_current), 'OWNER_EXECUTION_CAPACITY_CAPABILITY_REQUIRED')
            self.state = 'ACTIVE'
            self.require_current('CAPACITY', self.request, None, None, self.binding,
                self.capture, self.proof, self.peer, self.context)
            return self
        except BaseException as primary:
            try:
                self._retire(type(primary), primary, BaseException.__dict__['__traceback__'].__get__(primary))
            except BaseException as secondary:
                # Failed entry already makes the kernel retain this manager.
                # Retirement must not replace its exact original exception.
                _expose_execution(primary, self, secondary)
            _expose_execution(primary, self, self.cleanup_error)
            raise

    def require_current(self, phase, request, permit, attempt, binding, capture, proof, peer, context):
        require(self.lease._recovery is None, 'CPU_RECOVERY_BOOKKEEPING_ONLY')
        require(type(phase) is str and phase in ('CAPACITY', 'CONSUMED', 'READY', 'DISPATCH')
            and self.state == 'ACTIVE' and request is self.lease._request
            and request.canonical_wire == self.wire and binding is self.binding and capture is self.capture
            and proof is self.proof and peer == self.peer and context is self.context,
            'OWNER_EXECUTION_INPUT_CHANGED')
        require(not self.lease._dispatch and permit is self.lease._permit and attempt is self.lease._attempt,
            'OWNER_EXECUTION_PHASE_CHANGED')
        if phase == 'CAPACITY':
            require(permit is None and attempt is None and not self.lease._consumption_attempted,
                'OWNER_EXECUTION_PHASE_CHANGED')
        else:
            require(permit is not None and permit.as_dict()['status'] == 'CONSUMED',
                'OWNER_EXECUTION_CONSUMPTION_REQUIRED')
            require((attempt is None) == (phase == 'CONSUMED'), 'OWNER_EXECUTION_PHASE_CHANGED')
        if phase == 'DISPATCH':
            require(self.lease._dispatching, 'OWNER_EXECUTION_DISPATCH_NOT_ARMED')
        self._pure()
        require(self.capacity_current(phase, request, permit, context, self.coordinator) is None,
            'OWNER_EXECUTION_CAPACITY_DECISION_INVALID')
        self._pure()  # No fresh authentication/native query or SQL after the capability.
        return None

    def require_outcome_current(self, phase, request, permit, receipt, observation, proof, peer, context):
        require(type(phase) is str and phase in ('ATTEMPT', 'OUTCOME')
            and self.state == 'ACTIVE' and request.canonical_wire == self.wire
            and self.lease._permit is not None and permit.canonical_wire == self.lease._permit.canonical_wire
            and permit.as_dict()['status'] == 'CONSUMED' and context is self.context and peer == self.peer,
            'OWNER_EXECUTION_OUTCOME_BINDING_CHANGED')
        bookkeeping = phase == 'OUTCOME'
        if bookkeeping:
            require((self.lease._dispatch or self.lease._denied_dispatch is not None)
                and self.lease._called and not self.lease._dispatching
                and self.lease._attempt is not None and receipt is not None,
                'OWNER_EXECUTION_PRODUCER_NOT_DISPATCHED')
        else:
            require(proof is self.proof and not self.lease._dispatch and receipt is None and observation is None,
                'OWNER_EXECUTION_ATTEMPT_BINDING_CHANGED')
        self._pure(bookkeeping=bookkeeping)
        require(self.capacity_current(phase, request, permit, context, self.coordinator) is None,
            'OWNER_EXECUTION_CAPACITY_DECISION_INVALID')
        if bookkeeping:
            if self.lease._dispatch:
                require(self.provenance(request, permit, receipt, observation, proof, peer,
                    context, self) is None, 'OWNER_EXECUTION_PROVENANCE_DECISION_INVALID')
            else:
                from ceta.kernel.cpu_outcome_recovery import _DeniedDispatch
                origin = self.lease._denied_dispatch
                require(type(origin) is _DeniedDispatch, 'CPU_RECOVERY_DENIAL_NOT_ESTABLISHED')
                origin.require_current(self.lease, receipt, observation, proof, context, self)
        self._pure(bookkeeping=bookkeeping)
        return None

    def _retirement_failure(self, error):
        self.pending = True
        if self.cleanup_error is None: self.cleanup_error = error
        self.cleanup_errors.append(error)

    def _retire(self, kind, primary, trace):
        if self.exit_attempted:
            error = ContractError('OWNER_EXECUTION_EXIT_ONCE_REQUIRED')
            _expose_execution(primary if primary is not None else error, self, error)
            raise error
        self.exit_attempted = True
        if self.capacity_entry_attempted and not self.capacity_entered:
            self.pending = True  # The provider owns an uncertain failed entry.
        try:
            if self.capacity_entered:
                self.capacity_entered = False
                require(self.capacity_exit(kind, primary, trace) is None,
                    'OWNER_EXECUTION_CAPACITY_EXIT_INVALID')
        except BaseException as secondary:
            self._retirement_failure(secondary)
        finally:
            for borrow in reversed(self._lock_borrows):
                try:
                    borrow.retire()
                except BaseException as secondary:
                    self._retirement_failure(secondary)
            if all(borrow.retired for borrow in self._lock_borrows): self.locks.clear()
            self.state = 'FAILED' if self.pending else 'CLOSED'
            if not self.pending and self.owner._execution is self:
                self.owner._execution = None
                self.owner._effect_busy = False
        if primary is not None:
            _expose_execution(primary, self, self.cleanup_error)
        if self.cleanup_error is not None:
            # The canonical kernel preserves its body primary and marks its
            # lease pending only when this exit reports uncertain retirement.
            _expose_execution(self.cleanup_error, self, self.cleanup_error)
            raise self.cleanup_error

    def __exit__(self, kind, primary, trace):
        require(threading.get_ident() == self.thread, 'OWNER_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        require((primary is None and kind is None and trace is None)
            or (isinstance(primary, BaseException) and kind is type(primary)
                and (trace is None or type(trace) is TracebackType)),
            'OWNER_EXECUTION_EXCEPTION_ARGUMENTS_INVALID')
        self._retire(kind, primary, trace)
        return None

    def __copy__(self): raise ContractError('OWNER_EXECUTION_COPY_FORBIDDEN')
    def __deepcopy__(self, memo): raise ContractError('OWNER_EXECUTION_COPY_FORBIDDEN')
    def __reduce_ex__(self, protocol): raise ContractError('OWNER_EXECUTION_SERIALIZATION_FORBIDDEN')


class NativeCpuOwnerSession(NativeOwnerSession):
    """Selected approval/preparation and retained CPU admission owner.

    The canonical kernel alone consumes ceremonies and issues authority. This
    class borrows CPB1/WT4 custody and retains actual NA2 evidence. Its objects
    cannot substitute for a kernel execution lease or open a native Set path.
    """
    def __init__(self, *args, **kwargs):
        self._effect = self._effect_lease = self._effect_proof = None
        self._effect_busy,self._effect_retaining,self._effect_serial = False,False,0
        self._preparation_kernel = self._preparation_invocation = None
        self._execution = None
        super().__init__(*args,**kwargs)
        self._execution_capacity = getattr(self._view, 'retain_owned_cpu_outcome_capacity', None)
        self._execution_provenance = getattr(self._view, 'require_owned_cpu_outcome_provenance', None)

    def retain_owned_cpu_execution(self, request, prepared_permit, binding, capture, proof,
                                   peer, original_context, coordinator):
        from ceta.contracts.real_effect import OwnedCpuRequest
        from ceta.effects.native_cpu_binding import NativeCpuBinding
        capacity = getattr(self, '_execution_capacity', None)
        provenance = getattr(self, '_execution_provenance', None)
        require(callable(capacity) and getattr(capacity, '__self__', None) is self._view,
            'OWNER_EXECUTION_PHYSICAL_CAPACITY_UNAVAILABLE')
        require(callable(provenance) and getattr(provenance, '__self__', None) is self._view,
            'OWNER_EXECUTION_PROVENANCE_UNAVAILABLE')
        require(type(request) is OwnedCpuRequest and type(binding) is NativeCpuBinding
            and self._preparation_kernel is coordinator.kernel and coordinator.owners is self
            and coordinator.store is self._preparation_kernel._store
            and self._effect is not None and self._effect.wire == request.canonical_wire
            and self._effect.binding is binding and self._effect.capture is capture
            and self._effect_proof is proof and type(proof) is _NativeEffectWitness,
            'OWNER_EXECUTION_NATIVE_APPROVAL_REQUIRED')
        return _NativeCpuExecutionRetainer(self, request, prepared_permit, binding, capture,
            proof, peer, original_context, coordinator)

    def require_owned_cpu_outcome_current(self, phase, request, consumed_permit, receipt,
                                          observation, native_proof, peer, original_context):
        retained = getattr(self, '_execution', None)
        require(type(retained) is _NativeCpuExecutionRetainer and retained.owner is self,
            'OWNER_EXECUTION_RETAINED_OUTCOME_REQUIRED')
        return retained.require_outcome_current(phase, request, consumed_permit, receipt,
            observation, native_proof, peer, original_context)

    def require_admission(self, permit, basis_wire, peer):
        retained = getattr(self, '_execution', None)
        require(type(retained) is _NativeCpuExecutionRetainer and retained.owner is self,
            'OWNER_ADMISSION_RETAINED_EXECUTION_REQUIRED')
        return _NativeCpuExecutionRetainer.require_admission(retained, permit, basis_wire, peer)

    def _bind_preparation_kernel(self, kernel):
        """Bind once to the actual existing writer, never to a supplied verdict."""
        from ceta.kernel.transactions import KernelTransactions
        from ceta.store.journal import SqliteJournal
        from ceta.contracts.store_transactions import STORE_PROFILE
        require(type(self) is NativeCpuOwnerSession and type(kernel) is KernelTransactions
            and kernel._owners is self and kernel._installation == self._installation
            and self._preparation_kernel is None, 'OWNER_PREPARATION_KERNEL_BINDING')
        store = kernel._store
        from ceta.identity.native_owner_view import NativeStoreBinding
        require(type(store) is SqliteJournal and type(self._view) is NativeOwnerView
            and type(self._view._store) is NativeStoreBinding
            and store._codec is kernel._codec and store._profile == STORE_PROFILE
            and not store._closed and not store._read_only
            and store.path == self._view._store._database_path,
            'OWNER_PREPARATION_STORE_BINDING')
        self._preparation_kernel = kernel

    def _preparation_identity(self, invocation):
        from ceta.kernel.transactions import KernelTransactions, _PreparationInvocation
        from ceta.store.journal import SqliteJournal
        from ceta.store.state import TransactionState
        kernel = self._preparation_kernel
        require(type(kernel) is KernelTransactions and type(invocation) is _PreparationInvocation
            and invocation.active and invocation.owner is self and invocation.kernel is kernel
            and invocation.store is kernel._store and kernel._owners is self
            and kernel._preparation_owner is self and kernel._preparation_invocation is invocation
            and self._preparation_invocation is invocation
            and invocation.thread == threading.get_ident()
            and self._dispatch is not None and self._dispatch[0] is invocation.context
            and self._dispatch[1] == invocation.thread, 'OWNER_PREPARATION_INVOCATION_REQUIRED')
        store = invocation.store
        require(type(store) is SqliteJournal and not store._closed and not store._read_only
            and store._codec is kernel._codec and type(store._state) is TransactionState
            and store._state.connection is store._connection
            and type(store._connection) is store._sqlite.Connection
            and store.path == self._view._store._database_path and not self._view._store.closed,
            'OWNER_PREPARATION_STORE_CHANGED')
        # An instance-level fake snapshot/commit is not the canonical writer.
        require(all(getattr(getattr(store, name, None), '__func__', None) is getattr(SqliteJournal, name)
            for name in ('snapshot', 'commit', 'position', 'replay')),
            'OWNER_PREPARATION_STORE_METHOD_CHANGED')
        require(kernel._installation == self._installation and not self._closed
            and not self._stopped._flag, 'OWNER_PREPARATION_STOPPED')
        if invocation.enrollment_wire is not None:
            expected = self._expected
            require(expected is not None and expected.canonical_wire == invocation.enrollment_wire
                and expected.installation_id == self._installation and expected.scope_id == self._scope
                and expected.policy_commitment == self._policy
                and expected.source_commitment == self._code.source_commitment
                and expected.environment_commitment == self._code.environment_commitment
                and expected.worker_image_commitment == self._worker_commitment
                and self._effect is invocation.designation
                and self._effect.wire == invocation.request.canonical_wire,
                'OWNER_PREPARATION_CONFIGURATION_CHANGED')

    def _begin_preparation(self, invocation):
        from ceta.kernel.owner_authority import enrollment_key
        from ceta.contracts.real_effect import decode_owned_cpu_request
        require(self._preparation_invocation is None and not self._effect_busy
            and not self._effect_retaining, 'OWNER_PREPARATION_REENTRANT')
        self._preparation_invocation = invocation
        self._effect_busy = True
        self._preparation_identity(invocation)
        require(not invocation.store._connection.in_transaction,
            'OWNER_PREPARATION_WRITER_REENTRY')
        info = time.get_clock_info('perf_counter')
        require(info.monotonic is True and info.adjustable is False
            and type(info.resolution) is float and math.isfinite(info.resolution)
            and 0 < info.resolution <= .001, 'OWNER_PREPARATION_TIMER_UNAVAILABLE')
        invocation.resolution_ns = max(1, math.ceil(info.resolution*1_000_000_000))
        invocation.started = invocation.last_tick = time.perf_counter_ns()
        require(type(invocation.started) is int and invocation.started >= 0,
            'OWNER_PREPARATION_TIMER_UNAVAILABLE')
        self._require_dispatch(invocation.context)
        designation = self._effect
        require(designation is not None, 'OWNER_PREPARATION_DESIGNATION_REQUIRED')
        request, observed = self._require_effect(designation, invocation.context)
        invocation.request = decode_owned_cpu_request(request.canonical_wire)
        invocation.designation, invocation.observed = designation, observed
        invocation.enrollment_wire = self._expected.canonical_wire
        invocation.enrollment_key = enrollment_key(self._installation,self._expected.request_id)
        self._preparation_identity(invocation)
        self._effect_fence(designation)

    def _end_preparation(self, invocation):
        # No callbacks, SQL, native cleanup or permission revival on retirement.
        if self._preparation_invocation is invocation:
            self._preparation_invocation = None
            self._effect_busy = False
        else:
            require(self._preparation_invocation is None, 'OWNER_PREPARATION_CUSTODY_CHANGED')

    def require_prepared_basis(self, proposal, basis_wire, peer):
        """Pure current check over kernel-owned rows and retained native custody.

        Fresh native observation precedes journal entry. This predicate performs
        no SQLite command, native query, human wait or effect; the same journal
        CAS owns the selected canonical approval/control/task/resource rows.
        """
        from ceta.contracts.kernel_transactions import read_basis, logical_key
        from ceta.contracts.real_effect import (CAP_OPERATION, decode_native_approval_transcript,
            require_approval_binding)
        from ceta.contracts.owner_enrollment import require_enrollment_current
        from ceta.kernel.owner_authority import (KernelOwnerAuthority, _row, _wire,
            ceremony_key, grant_key_for, owned_cpu_proposal)
        invocation = getattr(self, '_preparation_invocation', None)
        require(invocation is not None, 'OWNER_PREPARATION_INVOCATION_REQUIRED')
        self._preparation_identity(invocation)
        require(self._effect_busy and invocation.phase == 'PREPARING' and proposal is invocation.proposal
            and type(basis_wire) is bytes and basis_wire == invocation.basis_wire
            and peer == invocation.peer == invocation.observed.peer,
            'OWNER_PREPARATION_INPUT_CHANGED')
        require(type(invocation.cells) is tuple and len(invocation.cells) <= 128,
            'OWNER_PREPARATION_ROWS_REQUIRED')
        cells = {cell.key: cell for cell in invocation.cells}
        require(len(cells) == len(invocation.cells), 'OWNER_PREPARATION_ROWS_REQUIRED')
        kernel, request, observed = invocation.kernel, invocation.request, invocation.observed
        require(self._expected is not None and self._expected.canonical_wire == invocation.enrollment_wire
            and self._effect is invocation.designation and self._effect.wire == request.canonical_wire,
            'OWNER_PREPARATION_REQUEST_CHANGED')
        enrollment = decode_enrollment_request(invocation.enrollment_wire)
        cell = cells[invocation.enrollment_key]
        row = _row(cell.value_wire)
        require(cell.generation > 0 and row['scope_id'] == self._installation
            and row['enrollment_id'] == enrollment.request_id
            and row['request_wire'].encode('utf8') == invocation.enrollment_wire
            and row['policy_generation'] == enrollment.policy_generation
            and row['enrollment_event_ref'] is not None and row['enrollment_transcript_wire'] is not None,
            'OWNER_PREPARATION_ENROLLMENT_CHANGED')
        # Reuse the canonical owner's pure current-view/policy predicates.
        authority = object.__new__(KernelOwnerAuthority)
        authority.k = kernel
        KernelOwnerAuthority._current(authority,cells,row,enrollment)
        KernelOwnerAuthority._effect_binding(enrollment,request)
        field = 'cap_approval' if request.operation == CAP_OPERATION else 'restore_approval'
        approval = row[field]
        require(type(approval) is dict and set(approval) == {'request_wire','transcript_wire',
            'proposal_wire','basis_wire','decision_event_ref'}, 'OWNER_PREPARATION_APPROVAL_REQUIRED')
        expected = owned_cpu_proposal(kernel._codec,request)
        require(approval['request_wire'].encode('utf8') == request.canonical_wire
            and approval['proposal_wire'].encode('utf8') == expected.canonical_wire == proposal.canonical_wire
            and approval['basis_wire'].encode('utf8') == basis_wire,
            'OWNER_PREPARATION_APPROVAL_CHANGED')
        basis, grant_key, _ = read_basis(basis_wire,kernel._codec)
        require(grant_key == grant_key_for(enrollment) and row['grant_key'] == grant_key.as_dict()
            and basis['owner_input_commitment'] == request.input_commitment
            and basis['approval_evidence_ref'] == approval['decision_event_ref'],
            'OWNER_PREPARATION_APPROVAL_CHANGED')
        identifier(approval['decision_event_ref'])
        transcript = decode_native_approval_transcript(approval['transcript_wire'].encode('utf8'))
        require(transcript.helper_commitment == enrollment.helper_commitment
            and transcript.ui_commitment == enrollment.ui_commitment
            and transcript.challenge_id != enrollment.challenge_id
            and transcript.ceremony_nonce != enrollment.ceremony_nonce,
            'OWNER_PREPARATION_APPROVAL_CHANGED')
        expected_request = _wire(dict(scope_id=self._installation,enrollment_id=enrollment.request_id,
            request_commitment=request.input_commitment,decision_event_ref=approval['decision_event_ref']))
        request_key = logical_key('projection',self._installation,'owner-effect',request.request_id)
        require(cells[request_key].value_wire == expected_request,'OWNER_PREPARATION_REQUEST_INDEX_CHANGED')
        for kind,value in (('challenge',transcript.challenge_id),('nonce',transcript.ceremony_nonce)):
            key = ceremony_key(self._installation,kind,value)
            require(cells[key].value_wire == _wire(dict(scope_id=self._installation,kind=kind,value=value,
                enrollment_id=enrollment.request_id,request_commitment=request.input_commitment,
                state='CONSUMED',event_ref=approval['decision_event_ref'])),
                'OWNER_PREPARATION_CEREMONY_CHANGED')
        require_enrollment_current(enrollment,enrollment,observed.previous_clock,observed.current_clock)
        require_approval_binding(request,transcript,observed.previous_clock,observed.current_clock)
        tick = time.perf_counter_ns()
        require(type(tick) is int and invocation.last_tick <= tick,
            'OWNER_PREPARATION_TIMER_ROLLBACK')
        invocation.last_tick = tick
        elapsed = tick-invocation.started+2*invocation.resolution_ns
        for deadline in (enrollment.deadline,request.deadline):
            require(observed.current_clock.monotonic_ns+elapsed < deadline.expires_monotonic_ns
                and observed.current_clock.latest_wall_ns+elapsed < deadline.expires_wall_ns,
                'OWNER_PREPARATION_DEADLINE_ELAPSED')
        require(0 <= observed.current_clock.monotonic_ns+elapsed-request.expected_limit.observed_monotonic_ns
            <= request.maximum_observation_age_ns
            and 0 <= observed.current_clock.monotonic_ns+elapsed-transcript.observed_clock.monotonic_ns
            <= enrollment.maximum_observation_age_ns, 'OWNER_PREPARATION_OBSERVATION_STALE')
        # Independent timer reads precede the complete retained final fence.
        self._preparation_identity(invocation)
        self._effect_fence(invocation.designation)
        # No fallible owner/clock callback follows this final local Stop fence.
        require(not self._stopped._flag and not self._closed and invocation.active,
            'OWNER_PREPARATION_STOPPED')

    @contextmanager
    def _effect_operation(self, context, *, retained_current=False):
        self._require_dispatch(context)
        require(not self._effect_busy and (not self._effect_retaining or retained_current),
            'OWNER_EFFECT_REENTRANT')
        self._effect_busy = True
        try:yield
        finally:self._effect_busy = False

    def _invalidate_effect(self):
        if self._effect is not None:self._effect.active = False
        if self._effect_lease is not None:self._effect_lease.active = False
        if self._effect_proof is not None:self._effect_proof.active = False

    @_native_context_boundary
    @contextmanager
    def native_context(self, original_context):
        with super().native_context(original_context):
            primary = None
            try:yield self
            except BaseException as error:
                primary = error
                raise
            finally:
                designation = self._effect
                self._invalidate_effect()
                try:
                    session = self._approval._active
                    if designation is not None and session is not None and not session._enrollment:
                        session.close()
                except BaseException as cleanup:
                    if primary is None:
                        _expose(cleanup,self)
                        raise
                    _expose(primary,self,cleanup_error=cleanup)
                finally:
                    self._effect = self._effect_proof = None

    def _effect_fence(self, designation, session=None):
        require(not self._closed and not self._stopped.is_set()
            and designation is self._effect and designation.active
            and designation.serial == self._effect_serial
            and self._dispatch is not None
            and designation.context is self._dispatch[0]
            and designation.thread == threading.get_ident(),'OWNER_EFFECT_STOPPED_OR_CHANGED')
        if session is not None:
            lease = self._effect_lease
            require(type(session) is NativeApprovalSession and session is self._approval._active
                and session._owner is self._approval and not session._closed
                and not session._stop.is_set() and session.mode == 'interactive' and not session._enrollment
                and session._bound_request_wire == designation.wire
                and session._bound_context is designation.context
                and type(lease) is _NativeEffectApprovalLease and session._lease is lease
                and lease.owner is self and lease.session is session and lease.designation is designation
                and lease.active and lease.context is designation.context
                and lease.thread == threading.get_ident()
                and lease.helper is session.helper_evidence,'OWNER_EFFECT_SESSION_CHANGED')
        binding,target = designation.binding,designation.target
        record = binding._current
        require(not binding._closed and not binding._cancelled._flag and binding._reason is None
            and (binding._external_cancel is None or not binding._external_cancel._flag)
            and record is not None and record.public is designation.capture
            and binding._target is target and binding._target_fields() == binding._lifetime
            and not target._closed and not target._termination_requested and target._exit_code is None
            and not target._cpu_lifetime_unavailable and target._process is not None and target._job is not None
            and target._cpu_version == record.measurement.original.version
            and target._cpu_policy == record.measurement.original.limit,
            'OWNER_EFFECT_NATIVE_TARGET_CHANGED')
        clock,sample = self._native_clock,binding._last_clock
        require(sample is not None and clock is binding._clock and clock._state == 'ACTIVE'
            and clock._reason is None and clock._registration is not None and clock._session == binding._session
            and clock._epoch == sample.durable_epoch and clock._resume == sample.resume_generation,
            'OWNER_EFFECT_CLOCK_CHANGED')
        self._dispatch[2].require_current()
        require(not self._view._store.closed,'OWNER_SESSION_STORE_CLOSED')
        require(not self._stopped._flag and not self._closed and designation.active
            and (session is None or not session._stop._flag),'OWNER_EFFECT_STOPPED_OR_CHANGED')

    def _require_effect(self, designation, context):
        from ceta.contracts.real_effect import decode_owned_cpu_request
        from ceta.kernel.owner_authority import KernelOwnerAuthority
        self._effect_fence(designation)
        require(context is designation.context,'OWNER_EFFECT_ORIGINAL_CONTEXT_REQUIRED')
        require(self._expected is not None,'OWNER_SESSION_ENROLLMENT_NOT_DESIGNATED')
        request = decode_owned_cpu_request(designation.wire)
        observed = self._require_native(self._expected,context,allow_expired=False)
        KernelOwnerAuthority._effect_binding(self._expected,request)
        require(designation.binding._clock is self._native_clock
            and designation.binding._target is designation.target
            and request.process_identity == designation.target.resource_identity
            and request.process_identity.image_digest == self._worker_commitment,
            'OWNER_EFFECT_NATIVE_TARGET_CHANGED')
        designation.binding.require_current(designation.capture,request)
        self._effect_fence(designation)
        return request,observed

    def designate_effect(self, request, binding, capture, original_context):
        """Freeze data/custody for one ceremony; this neither approves nor admits."""
        from ceta.contracts.real_effect import OwnedCpuRequest,decode_owned_cpu_request
        from ceta.contracts.wire import MAX_INTEGER
        from ceta.effects.native_cpu_binding import NativeCpuBinding
        with self._effect_operation(original_context):
            require(type(request) is OwnedCpuRequest and type(binding) is NativeCpuBinding
                and self._effect is None and self._effect_lease is None and self._effect_proof is None
                and self._approval._active is None and not self._stopped.is_set(),
                'OWNER_EFFECT_DESIGNATION_DENIED')
            frozen = decode_owned_cpu_request(request.canonical_wire)
            require(self._effect_serial < MAX_INTEGER,'OWNER_EFFECT_SEQUENCE_EXHAUSTED')
            self._effect_serial += 1
            designation = _EffectDesignation(frozen.canonical_wire,binding,capture,original_context,self._effect_serial)
            self._effect = designation
            try:self._require_effect(designation,original_context)
            except BaseException:
                designation.active = False
                self._effect = None
                raise
            return decode_owned_cpu_request(designation.wire)

    @contextmanager
    def retain_native_approval(self, request_wire, original_context):
        with self._effect_operation(original_context):
            designation,session = self._effect,self._approval._active
            require(designation is not None and type(request_wire) is bytes
                and request_wire == designation.wire and self._effect_lease is None
                and self._effect_proof is None and type(session) is NativeApprovalSession
                and session._owner is self._approval and session.mode == 'interactive'
                and not session._enrollment and not session._closed
                and session._context is original_context and session.request.canonical_wire == request_wire,
                'OWNER_EFFECT_APPROVAL_LEASE_DENIED')
            self._require_effect(designation,original_context)
            lease = _NativeEffectApprovalLease(self,designation,session,original_context)
            self._effect_lease = lease
        try:yield lease
        finally:
            lease.active = False
            if self._effect_lease is lease:self._effect_lease = None

    def retain_verified_effect(self, session, original_context):
        """Retain native provenance only; canonical approval is a separate call."""
        self._require_dispatch(original_context)
        require(not self._effect_busy and not self._effect_retaining,'OWNER_EFFECT_REENTRANT')
        designation = self._effect
        require(designation is not None and self._effect_proof is None
            and type(session) is NativeApprovalSession and session is self._approval._active
            and session._owner is self._approval and not session._enrollment
            and session.mode == 'interactive' and session._native_exited
            and session.native_facts.get('empty_job') is True and session.native_facts.get('exit_code') == 0
            and not session._closed and type(session._result) is NativeApprovalResult
            and session._result.reported_verified,'OWNER_EFFECT_GENUINE_CEREMONY_REQUIRED')
        self._effect_retaining = True
        try:
            NativeApprovalSession._require_gate_budget(session)
            transcript = session.transcript()  # Repeats only the actual retained NA2 lease.
            NativeApprovalSession._require_gate_budget(session)
            operation = self._effect_operation(original_context, retained_current=True)
            operation.__enter__()
            try:
                from ceta.contracts.real_effect import require_approval_binding
                request,_ = self._require_effect(designation,original_context)
                NativeApprovalSession._require_gate_budget(session)
                require(type(transcript) is NativeApprovalTranscript,'OWNER_EFFECT_TRANSCRIPT_REQUIRED')
                require_approval_binding(request,transcript,*self.clock())
                NativeApprovalSession._require_gate_budget(session)
                require(self._effect_lease is session._lease and self._effect_lease is not None
                    and self._effect_lease.active and self._effect_lease.helper is session.helper_evidence,
                    'OWNER_EFFECT_NATIVE_LEASE_INVALID')
                wire = transcript.canonical_wire
                self._effect_fence(designation,session)
                NativeApprovalSession._require_gate_budget(session)
                proof = _NativeEffectWitness(designation,session,original_context,wire)
            except BaseException as primary:
                # This local guard only unwinds its busy flag. Normal generator
                # exit avoids contextlib assigning a hostile primary traceback.
                try: operation.__exit__(None,None,None)
                except BaseException as secondary:
                    NativeApprovalSession._expose(session,primary,(secondary,))
                raise
            else:
                operation.__exit__(None,None,None)
            NativeApprovalSession._require_gate_budget(session)
            require(not session._stop.is_set() and not session._closed and not self._stopped.is_set(),
                'OWNER_EFFECT_STOPPED_OR_CHANGED')
            self._effect_proof = proof
            return transcript,proof
        except BaseException as primary:
            NativeApprovalSession._expose(session,primary,())
            raise
        finally:self._effect_retaining = False

    def require_owner_authority_current(self, phase, enrollment, effect_request, transcript,
                                        native_proof, peer, original_context):
        if phase not in ('APPROVE_CAP','APPROVE_RESTORE'):
            return super().require_owner_authority_current(phase,enrollment,effect_request,transcript,
                native_proof,peer,original_context)
        from ceta.contracts.real_effect import CAP_OPERATION,RESTORE_OPERATION,OwnedCpuRequest
        with self._effect_operation(original_context):
            proof,designation = self._effect_proof,self._effect
            require(type(proof) is _NativeEffectWitness and native_proof is proof and proof.active
                and designation is proof.designation and proof.context is original_context
                and type(effect_request) is OwnedCpuRequest and effect_request.canonical_wire == proof.wire
                and type(transcript) is NativeApprovalTranscript and transcript.canonical_wire == proof.transcript_wire,
                'OWNER_EFFECT_NATIVE_WITNESS_REQUIRED')
            require(type(enrollment) is EnrollmentRequest and self._expected is not None
                and enrollment.canonical_wire == self._expected.canonical_wire,
                'OWNER_SESSION_EXPECTED_ENROLLMENT_CHANGED')
            request,observed = self._require_effect(designation,original_context)
            require(request.operation == (CAP_OPERATION if phase == 'APPROVE_CAP' else RESTORE_OPERATION)
                and peer == observed.peer,'OWNER_EFFECT_PHASE_OR_PEER_CHANGED')
            session = proof.session
            require(session is self._approval._active and type(session._result) is NativeApprovalResult
                and session._result.reported_verified and session._native_exited
                and session.native_facts.get('empty_job') is True and session.native_facts.get('exit_code') == 0,
                'OWNER_EFFECT_GENUINE_CEREMONY_REQUIRED')
            require(self._effect_lease is session._lease and self._effect_lease is not None
                and self._effect_lease.active,'OWNER_EFFECT_NATIVE_LEASE_INVALID')
            self._effect_fence(designation,session)

    def request_stop(self):
        self._stopped.set()
        self._invalidate_effect()
        kernel = getattr(self, '_preparation_kernel', None)
        if kernel is not None and kernel._cpu_execution.owners is self:
            # Same short final-decision lane as the kernel lease. This trusted
            # cancellation capability grants no durable/public Stop authority.
            kernel._cpu_execution.cancel()
        return super().request_stop()

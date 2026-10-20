"""Native enrollment witness on the captured peer, clock, files and helper.

The canonical kernel issues authority. This owner binds its enrollment ports to
one measured native session and an opaque, locally retained ceremony witness.
Effect preparation/admission remain the inherited closed capabilities until the
separate native effect owner is composed and qualified.
"""
from contextlib import contextmanager
from pathlib import Path
import threading

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


def _expose(primary, owner):
    try:
        note = getattr(primary, 'add_note', None)
        if callable(note): note('Native enrollment-session custody remains available for explicit retirement.')
    except BaseException:
        pass
    BaseException.__dict__['__dict__'].__get__(primary).update(
        native_owner_session=owner, close_cleanup=owner.close)


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
        transcript = session.transcript()
        require(type(transcript) is NativeApprovalTranscript, 'OWNER_SESSION_TRANSCRIPT_REQUIRED')
        observed = self._require_native(self._expected,original_context,allow_expired=False)
        require(self._anchor is not None, 'OWNER_SESSION_CEREMONY_CLOCK_ANCHOR_REQUIRED')
        require_enrollment_transcript_binding(self._expected,self._expected,transcript,
            self._anchor,observed.current_clock)
        witness = _CeremonyWitness(session,original_context,self._expected.canonical_wire,
            enrollment_transcript_bytes(transcript))
        self._proof = witness
        return transcript,witness

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


class NativeCpuOwnerSession(NativeOwnerSession):
    """Selected genuine effect-approval owner; preparation/admission stay closed.

    The canonical kernel alone consumes ceremonies and issues authority. This
    class borrows CPB1/WT4 custody and retains actual NA2 evidence. Its objects
    cannot substitute for a kernel execution lease or open a native Set path.
    """
    def __init__(self, *args, **kwargs):
        self._effect = self._effect_lease = self._effect_proof = None
        self._effect_busy,self._effect_retaining,self._effect_serial = False,False,0
        super().__init__(*args,**kwargs)

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
                    _expose(primary,self)
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
            transcript = session.transcript()  # Repeats only the actual retained NA2 lease.
            with self._effect_operation(original_context, retained_current=True):
                from ceta.contracts.real_effect import require_approval_binding
                request,_ = self._require_effect(designation,original_context)
                require(type(transcript) is NativeApprovalTranscript,'OWNER_EFFECT_TRANSCRIPT_REQUIRED')
                require_approval_binding(request,transcript,*self.clock())
                require(self._effect_lease is session._lease and self._effect_lease is not None
                    and self._effect_lease.active and self._effect_lease.helper is session.helper_evidence,
                    'OWNER_EFFECT_NATIVE_LEASE_INVALID')
                wire = transcript.canonical_wire
                self._effect_fence(designation,session)
                proof = _NativeEffectWitness(designation,session,original_context,wire)
                self._effect_proof = proof
                return transcript,proof
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
        return super().request_stop()

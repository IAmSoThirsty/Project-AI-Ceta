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

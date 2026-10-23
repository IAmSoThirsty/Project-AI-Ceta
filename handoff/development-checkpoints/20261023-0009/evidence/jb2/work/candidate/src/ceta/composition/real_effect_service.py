"""Manual CPU journey on the original native runtime and authenticated context.

The trusted host retains a command session on its receiver thread. No context,
native proof, deployment selection, worker or permit is accepted from command
data. This module does not extend the ordinary development IPC profile.
"""
from dataclasses import dataclass
from functools import wraps
import secrets
import threading
import math
import time

from ceta.composition.native_cpu_runtime import NativeCpuRuntime
from ceta.contracts.kernel_transactions import BudgetVector, deadline_text, digest, identifier, require
from ceta.contracts.owner_enrollment import EnrollmentRequest, enrollment_transcript_bytes
from ceta.contracts.real_effect import (CAP_OPERATION, RESTORE_OPERATION, OwnedCpuRequest,
    approval_display_bytes, require_restoration_link)
from ceta.contracts.resource_management import ResourceVector
from ceta.contracts.temporal import Deadline, issue_deadline, require_clock_progress, require_deadline_current
from ceta.contracts.wire import ContractError
from ceta.contracts.workload_throttling import CpuRateLimit
from ceta.effects.native_cpu_binding import NativeCpuBinding
from ceta.kernel.owner_authority import owned_cpu_proposal

# Unmeasured engineering policy, not demonstrated scheduler or delivery bounds.
# Work expires before response handling; ceremonies also leave settlement time.
_RESPONSE_RESERVE_NS = 1_000_000_000
_SETTLEMENT_RESERVE_NS = 1_000_000_000


def _retain(primary, session, secondary=None):
    data = BaseException.__dict__['__dict__'].__get__(primary)
    dict.__setitem__(data, 'manual_real_effect_session', session)
    dict.__setitem__(data, 'manual_real_effect_budget', tuple(session._budget_trace))
    if secondary is not None:
        previous = dict.get(data, 'manual_real_effect_cleanup_errors', ())
        dict.__setitem__(data, 'manual_real_effect_cleanup_errors', previous + (secondary,))


def _custody(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except BaseException as primary:
            _retain(primary, self)
            raise
    return call


@dataclass(frozen=True)
class ManualEffectLimits:
    """Trusted profile declarations; native and canonical owners still decide."""
    authority_budget: BudgetVector
    recovery_budget: BudgetVector
    resource_limit: ResourceVector
    evidence_reserve_bytes: int
    required_outcome_bytes: int
    maximum_session_ns: int = 30_000_000_000
    maximum_effect_duration_ns: int = 1_000_000_000
    maximum_observation_age_ns: int = 5_000_000_000
    ceremony_timeout_ms: int = 20_000

    def __post_init__(self):
        require(type(self.authority_budget) is BudgetVector
            and type(self.recovery_budget) is BudgetVector
            and type(self.resource_limit) is ResourceVector,
            'MANUAL_PROFILE_TYPED_LIMITS_REQUIRED')
        self.authority_budget.__post_init__()
        self.recovery_budget.__post_init__()
        self.resource_limit.__post_init__()
        require(type(self.maximum_session_ns) is int
            and 1_000_000 <= self.maximum_session_ns <= 300_000_000_000,
            'MANUAL_PROFILE_SESSION_BOUND')
        require(type(self.ceremony_timeout_ms) is int
            and 20 <= self.ceremony_timeout_ms <= 20_000,
            'MANUAL_PROFILE_CEREMONY_BOUND')
        require(type(self.maximum_effect_duration_ns) is int
            and 1 <= self.maximum_effect_duration_ns <= 1_000_000_000,
            'MANUAL_PROFILE_EFFECT_BOUND')
        require(type(self.maximum_observation_age_ns) is int
            and 1 <= self.maximum_observation_age_ns <= 5_000_000_000,
            'MANUAL_PROFILE_OBSERVATION_BOUND')
        require(type(self.evidence_reserve_bytes) is int
            and 8192 <= self.evidence_reserve_bytes <= 1048576
            and type(self.required_outcome_bytes) is int
            and 4096 <= self.required_outcome_bytes <= 1048576,
            'MANUAL_PROFILE_EVIDENCE_BOUND')
        require(self.authority_budget.contains(self.recovery_budget),
            'MANUAL_PROFILE_RECOVERY_BUDGET')
        duration_ms = (self.maximum_effect_duration_ns + 999999) // 1000000
        for budget, effects, count in ((self.authority_budget, 2, 2), (self.recovery_budget, 1, 1)):
            values = budget.as_dict()
            require(values['max_effects'] == effects
                and values['max_model_calls'] == values['max_input_tokens'] == values['max_output_tokens'] == 0
                and count * duration_ms <= values['wall_time_ms'] <= self.maximum_session_ns // 1000000
                and values['max_bytes_read'] <= 16 * 1024 * 1024
                and values['max_bytes_written'] <= 1048576,
                'MANUAL_PROFILE_BUDGET_BOUND')
        available = self.authority_budget.subtract(self.recovery_budget).as_dict()
        require(self.authority_budget.as_dict()['max_bytes_written'] >= self.evidence_reserve_bytes
            and self.recovery_budget.as_dict()['max_bytes_written'] >= self.required_outcome_bytes
            and available['max_bytes_written'] >= self.required_outcome_bytes
            and available['wall_time_ms'] >= duration_ms,
            'MANUAL_PROFILE_OUTCOME_BUDGET')
        resource = self.resource_limit
        require(1 <= resource.cpu_milli <= 1000 and 1 <= resource.memory_bytes <= 64 * 1024 * 1024
            and max(8192, self.evidence_reserve_bytes) <= resource.storage_bytes <= 16 * 1024 * 1024
            and 2 * duration_ms <= resource.wall_time_ms <= self.maximum_session_ns // 1000000,
            'MANUAL_PROFILE_RESOURCE_BOUND')


class ManualRealEffectSession:
    """One live same-thread conversation; run ID is lookup data, never authority.

    ``profile`` is the concrete composition owner, not a command-supplied port.
    The receiver must keep its actual authenticated context live until close.
    Pending execution keeps this session and its original context guard owned.
    """
    def __init__(self, profile, original_context):
        from ceta.composition.real_effect_runtime import ManualRealEffectProfile
        require(type(profile) is ManualRealEffectProfile
            and type(profile.runtime) is NativeCpuRuntime,
            'MANUAL_PROFILE_CONCRETE_RUNTIME_REQUIRED')
        require(original_context is not None, 'MANUAL_PROFILE_CONTEXT_REQUIRED')
        self.profile, self.runtime = profile, profile.runtime
        self._context, self._thread = original_context, threading.get_ident()
        self._owner = self.runtime._owner
        self._kernel = self.runtime.kernel._kernel
        self._run_id = 'run:' + secrets.token_hex(16)
        self._task_id = 'task:' + secrets.token_hex(16)
        self._state = 'NEW'
        self._context_manager = None
        self._context_history = []
        self._context_entered = self._context_exit_attempted = False
        self._context_entry_attempted = False
        self._enrollment = self._enrollment_session = None
        self._enrollment_stage = 'NEW'
        self._enrollment_result = None
        self._binding = self._capture = None
        self._request = self._proposal = self._permit = self._proof = None
        self._approval_session = self._approval_result = None
        self._transcript_wire = None
        self._approval_stage = 'NEW'
        self._execution = self._outcome = None
        self._execution_attempted = False
        self._cap_request = None
        self._budget_deadline = self._budget_anchor = self._budget_current = None
        self._budget_started = self._budget_end = self._budget_last = None
        self._budget_failure = None
        self._budget_trace = []
        self._budget_resolution = max(1, math.ceil(time.get_clock_info('perf_counter').resolution*1_000_000_000))

    @property
    def run_id(self):
        return self._run_id

    @property
    def closed(self):
        return self._state == 'CLOSED'

    def _selected(self, run_id=None, *, bookkeeping=False):
        require(threading.get_ident() == self._thread,
            'MANUAL_PROFILE_ORIGINAL_THREAD_REQUIRED')
        require(self._context_entered and not self._context_exit_attempted
            and self._state in (('ACTIVE', 'PENDING', 'STOPPED') if bookkeeping else ('ACTIVE',)),
            'MANUAL_PROFILE_SESSION_UNAVAILABLE')
        require(run_id is None or type(run_id) is str and run_id == self._run_id,
            'MANUAL_PROFILE_RUN_ID_MISMATCH')
        self.profile.require_session(self)
        self.runtime._selected(self.runtime._store, self.runtime._codec,
            self.runtime._installation, self.runtime._registry, bookkeeping=bookkeeping)
        # The real registry rejects foreign threads, expired envelopes and peers.
        self.runtime._registry.authenticate(self._context)

    def __enter__(self):
        require(self._state == 'NEW' and threading.get_ident() == self._thread,
            'MANUAL_PROFILE_SESSION_SINGLE_ENTRY')
        self._state = 'ENTERING'
        self._context_manager = self._owner.native_context(self._context)
        self._context_entry_attempted = True
        try:
            self._context_manager.__enter__()
            self._context_entered = True
            self._state = 'ACTIVE'
            self._selected()
            self._start_budget()
            return self
        except BaseException as primary:
            self._state = 'PENDING'
            _retain(primary, self)
            raise

    def _deadline(self, sample):
        require(self._budget_deadline is not None, 'MANUAL_PROFILE_ORIGINAL_BUDGET_REQUIRED')
        require_deadline_current(self._budget_deadline, self._budget_anchor, sample)
        return self._budget_deadline

    def _start_budget(self):
        require(self._budget_deadline is None and self._budget_started is None,
            'MANUAL_PROFILE_BUDGET_SINGLE_ANCHOR')
        started = time.perf_counter_ns()
        self._budget_started = self._budget_last = started
        previous, current = self._owner.clock()
        require_clock_progress(previous, current)
        remaining, wall_expiry = self.runtime._registry.remaining_time(self._context)
        ended = time.perf_counter_ns()
        require(ended >= started, 'MANUAL_PROFILE_ELAPSED_ROLLBACK')
        charge = ended-started+2*self._budget_resolution
        lifetime = min(self.profile.limits.maximum_session_ns, remaining-charge)-_RESPONSE_RESERVE_NS
        require(lifetime > self._later_work_reserve(), 'MANUAL_PROFILE_JOINT_BUDGET_INSUFFICIENT')
        self._budget_deadline = issue_deadline(deadline_text(wall_expiry-_RESPONSE_RESERVE_NS),
            lifetime, previous, current)
        self._budget_anchor = self._budget_current = current
        # Only an elapsed duration crosses domains. No native/Python epochs are subtracted.
        self._budget_end = started+lifetime
        self._budget_last = ended
        self._budget_trace.append(dict(stage='ANCHOR',elapsed_started_ns=started,
            elapsed_ended_ns=ended,acquisition_charge_ns=charge,transport_remaining_ns=remaining,
            original_envelope_expiry_wall_ns=wall_expiry,deadline=self._budget_deadline,
            response_reserve_ns=_RESPONSE_RESERVE_NS,settlement_reserve_ns=_SETTLEMENT_RESERVE_NS))

    def _later_work_reserve(self):
        return 2*self.profile.limits.maximum_effect_duration_ns+_SETTLEMENT_RESERVE_NS

    def _remaining(self, stage, reserve=0):
        if self._budget_failure is not None:
            raise self._budget_failure
        try:
            require(self._budget_deadline is not None, 'MANUAL_PROFILE_ORIGINAL_BUDGET_REQUIRED')
            began = time.perf_counter_ns()
            require(began >= self._budget_last, 'MANUAL_PROFILE_ELAPSED_ROLLBACK')
            previous, current = self._owner.clock()
            require_clock_progress(self._budget_current, current)
            deadlines = [self._budget_deadline]
            if self._enrollment is not None: deadlines.append(self._enrollment.deadline)
            if self._request is not None: deadlines.append(self._request.deadline)
            native_remaining = []
            for deadline in deadlines:
                require_deadline_current(deadline, previous, current)
                native_remaining.extend((deadline.expires_monotonic_ns-current.monotonic_ns,
                    deadline.expires_wall_ns-current.latest_wall_ns))
            transport_remaining, wall_expiry = self.runtime._registry.remaining_time(self._context)
            ended = time.perf_counter_ns()
            require(ended >= began, 'MANUAL_PROFILE_ELAPSED_ROLLBACK')
            charge = ended-began+2*self._budget_resolution
            remaining = min(*native_remaining,transport_remaining-_RESPONSE_RESERVE_NS)-charge
            remaining = min(remaining,self._budget_end-ended)
            self._budget_last, self._budget_current = ended, current
            self._budget_trace.append(dict(stage=stage,elapsed_started_ns=began,elapsed_ended_ns=ended,
                acquisition_charge_ns=charge,native_remaining_ns=min(native_remaining),
                transport_remaining_ns=transport_remaining,original_envelope_expiry_wall_ns=wall_expiry,
                remaining_work_ns=remaining,reserved_later_ns=reserve))
            require(remaining > reserve, 'MANUAL_PROFILE_JOINT_BUDGET_EXPIRED')
            return remaining-reserve
        except BaseException as primary:
            self._budget_failure = primary
            _retain(primary,self)
            raise

    def _ceremony_timeout(self, stage):
        remaining = self._remaining(stage,self._later_work_reserve())
        milliseconds = min(self.profile.limits.ceremony_timeout_ms,remaining//1_000_000)
        require(milliseconds >= 20, 'MANUAL_PROFILE_CEREMONY_BUDGET_INSUFFICIENT')
        return milliseconds

    def _effect_deadline(self, enrollment):
        current = self._budget_current
        require_deadline_current(enrollment.deadline,self._budget_anchor,current)
        bounded = self._budget_deadline
        return Deadline(current.boot_id,current.durable_epoch,current.resume_generation,
            current.monotonic_ns,min(bounded.expires_monotonic_ns,enrollment.deadline.expires_monotonic_ns),
            current.earliest_wall_ns,min(bounded.expires_wall_ns,enrollment.deadline.expires_wall_ns))

    def _new_enrollment(self, prepared):
        observed = self.runtime._view.observe(self._context)
        native = prepared.enrollment_binding
        previous, current = self._owner.clock()
        require_clock_progress(previous, current)
        limits, configuration = self.profile.limits, self.runtime._configuration
        nonce = current.boot_id.rsplit(':session:', 1)[-1]
        return EnrollmentRequest(
            request_id='enrollment:' + secrets.token_hex(16),
            installation_id=self.runtime._installation, scope_id=configuration.scope_id,
            principal_id=observed.peer.principal_id, actor_session=observed.peer.session_id,
            owner_session_nonce=secrets.token_hex(16), clock_session_nonce=nonce,
            challenge_id=native.challenge_id, ceremony_nonce=native.ceremony_nonce,
            private_root=observed.private_root, database=observed.database,
            owner_facts=observed.owner_facts, helper_identity=native.helper.identity,
            ui_identity=native.ui_identity, policy_generation=0, authority_generation=0,
            policy_commitment=configuration.policy_commitment,
            source_commitment=configuration.code_binding.source_commitment,
            environment_commitment=configuration.code_binding.environment_commitment,
            helper_commitment=native.helper_commitment, ui_commitment=native.ui_commitment,
            adapter_commitment=self.profile.adapter_commitment,
            worker_image_commitment=self._owner._worker_commitment,
            authority_budget=limits.authority_budget, recovery_budget=limits.recovery_budget,
            resource_limit=limits.resource_limit, evidence_reserve_bytes=limits.evidence_reserve_bytes,
            maximum_session_ns=limits.maximum_session_ns,
            maximum_effect_duration_ns=limits.maximum_effect_duration_ns,
            maximum_observation_age_ns=limits.maximum_observation_age_ns,
            deadline=self._deadline(current))

    @_custody
    def enroll(self):
        self._selected()
        require(self._enrollment_stage in ('NEW', 'WAITING'),
            'MANUAL_PROFILE_ENROLLMENT_RECOVERY_REQUIRED')
        try:
            if self._enrollment_stage == 'NEW':
                self._enrollment_stage = 'PREPARATION_ATTEMPTED'
                prepared = self._owner.approval_owner.prepare_enrollment(
                    timeout_ms=self._ceremony_timeout('ENROLLMENT_HELPER'))
                self._enrollment_session = prepared
                self._remaining('ENROLLMENT_HELPER_RETURNED',self._later_work_reserve())
                self._enrollment = self._new_enrollment(prepared)
                self._owner.designate_enrollment(self._enrollment, prepared, self._context)
                self._enrollment_stage = 'CHALLENGE_ATTEMPTED'
                self._kernel.begin_owner_enrollment(self._enrollment.canonical_wire, self._context)
                self._remaining('ENROLLMENT_CHALLENGE_RETURNED',self._later_work_reserve())
                prepared.begin_enrollment(self._enrollment, original_context=self._context)
                self._enrollment_stage = 'WAITING'
            completed = self._enrollment_session.wait(
                self._ceremony_timeout('ENROLLMENT_WAIT') / 1000)
            self._remaining('ENROLLMENT_WAIT_RETURNED',self._later_work_reserve())
            if completed is None:
                return self.inspect()
            transcript, proof = self._owner.retain_verified_enrollment(
                self._enrollment_session, self._context)
            self._enrollment_stage = 'COMMIT_ATTEMPTED'
            self._enrollment_result = self._kernel.enroll_owner(self._enrollment.canonical_wire,
                enrollment_transcript_bytes(transcript), proof, self._context)
            self._enrollment_stage = 'ENROLLED'
            self._enrollment_session.close()
            self._remaining('ENROLLMENT_COMMIT_RETURNED',self._later_work_reserve())
            return self.inspect()
        except BaseException as primary:
            _retain(primary, self)
            raise

    @_custody
    def prepare(self, *, cpu_rate=None, restoration=False):
        self._selected()
        self._remaining('PREPARE',self._later_work_reserve())
        require(self._enrollment_stage == 'ENROLLED', 'MANUAL_PROFILE_ENROLLMENT_REQUIRED')
        require(self._request is None or self._execution is not None
            and self._execution.inspection()['closed'], 'MANUAL_PROFILE_REQUEST_STILL_OWNED')
        require(type(restoration) is bool, 'MANUAL_PROFILE_OPERATION_REQUIRED')
        require((restoration and cpu_rate is None and self._cap_request is not None)
            or (not restoration and self._cap_request is None and type(cpu_rate) is int
                and 1 <= cpu_rate <= 10000), 'MANUAL_PROFILE_CAP_OR_RESTORE_REQUIRED')
        if self._request is not None:
            # Retire the previous ceremony/designation through the existing
            # native-context boundary. Reenter only the SAME live receiver
            # context; no proof or request context is reconstructed.
            self._binding.close()
            self._context_exit_attempted = True
            previous = self._context_manager
            result = previous.__exit__(None, None, None)
            require(result is None or result is False, 'MANUAL_PROFILE_CONTEXT_SUPPRESSION_DENIED')
            self._context_history.append(previous)
            self._context_entered = False
            self._context_manager = self._owner.native_context(self._context)
            self._context_exit_attempted = False
            self._context_entry_attempted = True
            self._context_manager.__enter__()
            self._context_entered = True
        self._binding = self.profile.cpu_binding()
        self._remaining('BINDING_RETURNED',self._later_work_reserve())
        self._capture = self._binding.capture()
        self._remaining('CAPTURE_RETURNED',self._later_work_reserve())
        captured = self._capture.observation
        enrollment, limits = self._enrollment, self.profile.limits
        if restoration:
            original = self._cap_request.original_limit
            target = original
            budget = enrollment.recovery_budget
        else:
            original = captured.limit
            target = CpuRateLimit(5 | (captured.limit.control_flags & 8), cpu_rate)
            budget = enrollment.authority_budget.subtract(enrollment.recovery_budget)
        request = OwnedCpuRequest(
            request_id='request:' + secrets.token_hex(16), scope_id=enrollment.scope_id,
            task_id=self._task_id, proposal_id='proposal:' + secrets.token_hex(16),
            principal_id=enrollment.principal_id, actor_session=enrollment.actor_session,
            owner_session_nonce=enrollment.owner_session_nonce,
            operation=RESTORE_OPERATION if restoration else CAP_OPERATION,
            process_identity=captured.identity, job_digest=captured.job_digest,
            expected_limit=captured, target_limit=target, original_limit=original,
            task_revision=digest('manual-owned-cpu-task-v1', dict(task_id=self._task_id,
                scope_id=enrollment.scope_id, worker=enrollment.worker_image_commitment)),
            policy_commitment=enrollment.policy_commitment,
            adapter_commitment=enrollment.adapter_commitment,
            environment_commitment=enrollment.environment_commitment,
            source_commitment=enrollment.source_commitment,
            observer_commitment=self.runtime._configuration.observer._commitment,
            operation_budget=budget, required_outcome_bytes=limits.required_outcome_bytes,
            deadline=self._effect_deadline(enrollment), maximum_observation_age_ns=limits.maximum_observation_age_ns,
            maximum_duration_ns=limits.maximum_effect_duration_ns,
            consequences=('consequence:owned-worker-cpu-policy', 'consequence:independent-query',
                'consequence:canonical-evidence-write', 'consequence:separate-approved-restore'),
            restoration_of=self._cap_request.request_id if restoration else None,
            original_request_commitment=self._cap_request.input_commitment if restoration else None)
        if restoration:
            require_restoration_link(self._cap_request, request)
        self._owner.designate_effect(request, self._binding, self._capture, self._context)
        self._remaining('DESIGNATION_RETURNED',self._later_work_reserve())
        self._request, self._proposal = request, owned_cpu_proposal(self.runtime._codec, request)
        self._permit = self._proof = self._execution = self._outcome = None
        self._approval_session = self._approval_result = None
        self._transcript_wire = None
        self._approval_stage, self._execution_attempted = 'NEW', False
        return self.inspect()

    @_custody
    def approve(self, request_id):
        self._selected()
        require(self._request is not None and request_id == self._request.request_id,
            'MANUAL_PROFILE_REQUEST_ID_MISMATCH')
        require(self._approval_stage in ('NEW', 'WAITING', 'APPROVED_RECOVERED'),
            'MANUAL_PROFILE_APPROVAL_RECOVERY_REQUIRED')
        try:
            self._remaining('APPROVAL',self._later_work_reserve())
            if self._approval_stage == 'APPROVED_RECOVERED':
                # Only an explicit readback of the exact canonical approval can
                # reach here. The original proof/context is still required by
                # kernel preparation; this performs no ceremony/approval retry.
                self._approval_stage = 'PREPARATION_COMMIT_ATTEMPTED'
                result = self.runtime.kernel.prepare(self._proposal.original_wire, self._context)
                self._permit = result.record_wire
                self._approval_stage = 'PREPARED'
                self._remaining('RECOVERED_PREPARATION_RETURNED',self._later_work_reserve())
                return self.inspect()
            if self._approval_stage == 'NEW':
                self._approval_stage = 'CEREMONY_ATTEMPTED'
                self._approval_session = self._owner.approval_owner.begin_interactive(
                    self._request, original_context=self._context,
                    timeout_ms=self._ceremony_timeout('APPROVAL_HELPER'))
                self._approval_stage = 'WAITING'
            completed = self._approval_session.wait(self._ceremony_timeout('APPROVAL_WAIT') / 1000)
            self._remaining('APPROVAL_WAIT_RETURNED',self._later_work_reserve())
            if completed is None:
                return self.inspect()
            transcript, self._proof = self._owner.retain_verified_effect(
                self._approval_session, self._context)
            self._transcript_wire = transcript.canonical_wire
            self._approval_stage = 'APPROVAL_COMMIT_ATTEMPTED'
            self._approval_result = self._kernel.approve_owned_cpu(self._enrollment.request_id,
                self._request.canonical_wire, transcript.canonical_wire, self._proof, self._context)
            self._approval_stage = 'PREPARATION_COMMIT_ATTEMPTED'
            result = self.runtime.kernel.prepare(self._proposal.original_wire, self._context)
            self._permit = result.record_wire
            self._approval_stage = 'PREPARED'
            self._remaining('APPROVAL_COMMIT_RETURNED',self._later_work_reserve())
            return self.inspect()
        except BaseException as primary:
            _retain(primary, self)
            raise

    @_custody
    def execute(self, request_id):
        self._selected()
        require(self._request is not None and request_id == self._request.request_id
            and self._approval_stage == 'PREPARED' and not self._execution_attempted,
            'MANUAL_PROFILE_SINGLE_EXECUTION_REQUIRED')
        self._execution_attempted = True  # Retain ambiguous entry/return; never replay.
        try:
            self._remaining('EXECUTION_BEFORE_ADMISSION',self._later_work_reserve())
            self._execution = self._kernel.owned_cpu_execution(self._request.canonical_wire,
                self._permit, self._binding, self._capture, self._proof, self._context)
            with self._execution as lease:
                self._outcome = self.runtime.execute(lease)
            # An admitted attempt is reconciled/recorded by its original adapter
            # before this postcheck. Expiry never causes a retry or refund.
            self._remaining('EXECUTION_RETURNED')
            if self._request.operation == CAP_OPERATION:
                self._cap_request = self._request
            return self.inspect()
        except BaseException as primary:
            _retain(primary, self)
            raise

    def reconcile(self, request_id):
        self._selected(bookkeeping=True)
        if self._enrollment is not None and request_id == self._enrollment.request_id:
            state = self._kernel.recover_owner_enrollment(request_id, self._context).as_dict()
            if self._enrollment_stage == 'COMMIT_ATTEMPTED' and state['state'] == 'ENROLLED':
                self._enrollment_stage = 'ENROLLED'
                self._enrollment_session.close()
            # A reserved CHALLENGE is historical state, never an automatic retry.
            return self.inspect()
        require(self._request is not None and request_id == self._request.request_id,
            'MANUAL_PROFILE_REQUEST_ID_MISMATCH')
        try:
            if self._execution is not None:
                with self._execution.recover_outcome(self._context) as lease:
                    self._outcome = (lease.record_denied_outcome()
                        if lease.inspection()['denied_dispatch'] is not None
                        else self.runtime.reconcile(lease))
            elif self._approval_stage == 'APPROVAL_COMMIT_ATTEMPTED':
                state = self._kernel.recover_owner_enrollment(
                    self._enrollment.request_id, self._context).as_dict()
                key = 'cap_approval' if self._request.operation == CAP_OPERATION else 'restore_approval'
                row = state[key]
                require(type(row) is dict
                    and row['request_wire'] == self._request.canonical_wire.decode('utf8')
                    and row['transcript_wire'] == self._transcript_wire.decode('utf8'),
                    'MANUAL_PROFILE_EXACT_APPROVAL_NOT_COMMITTED')
                self._approval_stage = 'APPROVED_RECOVERED'
            elif self._approval_stage == 'PREPARATION_COMMIT_ATTEMPTED':
                self._permit = self.runtime.kernel.recover_preparation(
                    self._proposal.original_wire, self._context).original_wire
                # A recovered permit is data; the genuine proof/context must still pass.
                self._approval_stage = 'PREPARED'
            else:
                raise ContractError('MANUAL_PROFILE_NO_RECONCILABLE_INVOCATION')
            if (self._execution is not None and self._execution.inspection()['closed']
                    and self._request.operation == CAP_OPERATION):
                self._cap_request = self._request
            return self.inspect()
        except BaseException as primary:
            _retain(primary, self)
            raise

    def inspect(self):
        self._selected(bookkeeping=True)
        canonical = None
        if self._enrollment is not None and self._enrollment_stage not in ('NEW', 'PREPARATION_ATTEMPTED'):
            canonical = self._kernel.recover_owner_enrollment(
                self._enrollment.request_id, self._context).as_dict()
        custody = None
        if self._execution is not None:
            facts = self._execution.inspection()
            custody = {name: facts[name] for name in
                ('dispatch_admitted', 'closed', 'pending_cleanup', 'stopped', 'native_effect')}
        return dict(profile='ceta-owned-real-effect-v1', run_id=self._run_id,
            state=self._state, enrollment_stage=self._enrollment_stage,
            enrollment=canonical, approval_stage=self._approval_stage,
            request=None if self._request is None else self._request.as_dict(),
            full_display=None if self._request is None else approval_display_bytes(self._request).decode('utf8'),
            permit_wire=None if self._permit is None else self._permit.decode('utf8'),
            outcome=None if self._outcome is None else self._outcome.as_dict(), custody=custody)

    def stop(self, reason_ref):
        self._selected(bookkeeping=True)
        identifier(reason_ref)
        try:
            if self._enrollment is not None and self._enrollment_stage == 'ENROLLED':
                self._kernel.stop_owner_authority(self._enrollment.request_id, self._context, reason_ref)
        finally:
            self._owner.request_stop()
            self._state = 'STOPPED'
        return self.inspect()

    def close(self, primary=None):
        require(threading.get_ident() == self._thread, 'MANUAL_PROFILE_ORIGINAL_THREAD_REQUIRED')
        if self.closed:
            return
        if self._execution is not None and not self._execution.inspection()['closed']:
            self._state = 'PENDING'
            failure = ContractError('MANUAL_PROFILE_EXECUTION_CUSTODY_PENDING')
            _retain(failure, self)
            if primary is not None:
                _retain(primary, self, failure)
                return
            raise failure
        if self._context_exit_attempted:
            failure = ContractError('MANUAL_PROFILE_CONTEXT_RETIREMENT_UNCERTAIN')
            _retain(failure, self)
            if primary is not None:
                _retain(primary, self, failure)
                return
            raise failure
        try:
            if self._context_entry_attempted and not self._context_entered:
                raise ContractError('MANUAL_PROFILE_CONTEXT_ENTRY_UNCERTAIN')
            for session in (self._enrollment_session, self._approval_session):
                if session is not None:
                    session.close()
            if self._binding is not None:
                self._binding.close()
            if self._context_entered:
                self._context_exit_attempted = True
                kind = None if primary is None else type(primary)
                trace = None if primary is None else BaseException.__traceback__.__get__(primary)
                result = self._context_manager.__exit__(kind, primary, trace)
                require(result is None or result is False, 'MANUAL_PROFILE_CONTEXT_SUPPRESSION_DENIED')
            self._state = 'CLOSED'
            self.profile.retire_session(self)
        except BaseException as cleanup:
            self._state = 'PENDING'
            if primary is None:
                _retain(cleanup, self)
                raise
            _retain(primary, self, cleanup)

    def __exit__(self, kind, primary, trace):
        self.close(primary)
        return False

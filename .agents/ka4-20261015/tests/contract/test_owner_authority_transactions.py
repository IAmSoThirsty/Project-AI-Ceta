"""Real disposable SQLite; positive native authority is explicitly controlled.

No Hello ceremony, worker launch, process-policy effect, native approval or
public-runtime qualification is supplied by these provider fixtures.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import threading
import time
import unittest
import uuid
from unittest.mock import patch

from ceta.contracts.kernel_transactions import (BudgetVector, PeerIdentity, ZERO_BUDGET,
    basis_key, budget_key, control_wire, read_basis, read_budget)
from ceta.contracts.owner_enrollment import (EnrollmentRequest, NativeObjectIdentity,
    OwnerTokenFacts, enrollment_display_commitment, enrollment_transcript_bytes)
from ceta.contracts.real_effect import (CAP_OPERATION, RESTORE_OPERATION, NativeApprovalTranscript,
    OwnedCpuRequest, approval_display_commitment)
from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity, ResourceVector
from ceta.contracts.store_transactions import STORE_PROFILE, StoreKey
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.contracts.workload_throttling import CpuRateLimit, CpuRateObservation
from ceta.kernel.owner_authority import (OWNER_PROFILE, ceremony_key, enrollment_key,
    grant_key_for, owned_cpu_proposal)
from ceta.kernel.transactions import KernelTransactions
from ceta.store.journal import SqliteJournal

ROOT = Path(__file__).resolve().parents[2]
INSTALLATION, PROJECT = 'installation:owner-authority-fixture', 'project:owner-authority-fixture'
H = 'sha256:'+'a'*64
H2 = 'sha256:'+'b'*64
WALL = 1_792_000_000_000_000_000
BOOT = 'boot:12345678-1234-4234-8234-123456789abc:session:'+'1'*32
NATIVE_FIXTURES = []


def clock(value=1_100_000_000, **changes):
    return ClockSample(**dict(dict(boot_id=BOOT, durable_epoch=7, resume_generation=0,
        monotonic_ns=value, wall_time_ns=WALL+value, uncertainty_ns=0, wall_trusted=True), **changes))


def budget(effects=2, **changes):
    return BudgetVector.from_dict(dict(dict(wall_time_ms=10000, max_model_calls=0, max_effects=effects,
        max_input_tokens=0, max_output_tokens=0, max_bytes_read=16384, max_bytes_written=16384), **changes))


def enrollment_request():
    """Same DATA_ONLY facts as EN1, with this fixture's designated scopes."""
    process = ProcessResourceIdentity(101, 100, H)
    path = r'\\?\Volume{12345678-1234-4234-8234-123456789abc}\CETA\private\fixture'
    facts = OwnerTokenFacts(process, 'S-1-5-21-1-2-3-1001', 'S-1-5-5-1-2', '0'*16,
        0, '0'*16, '0'*16, 1, 0, 'S-1-16-8192', 0, 1, 0, 0, ())
    return EnrollmentRequest(request_id='enrollment:fixture', installation_id=INSTALLATION, scope_id=PROJECT,
        principal_id='owner:fixture', actor_session='session:owner-fixture', owner_session_nonce='2'*32,
        clock_session_nonce='1'*32, challenge_id='challenge:enroll', ceremony_nonce='3'*32,
        private_root=NativeObjectIdentity(path, 'directory', '0'*16, '0'*32),
        database=NativeObjectIdentity(path+r'\history.sqlite3', 'file', '0'*16, '0'*31+'1'),
        owner_facts=facts, helper_identity=ProcessResourceIdentity(102, 100, H),
        ui_identity=ProcessResourceIdentity(103, 100, H), policy_generation=0, authority_generation=0,
        policy_commitment=H, source_commitment=H, environment_commitment=H, helper_commitment=H,
        ui_commitment=H, adapter_commitment=H, worker_image_commitment=H,
        authority_budget=budget(), recovery_budget=budget(1, wall_time_ms=5000, max_bytes_read=8192, max_bytes_written=8192),
        resource_limit=ResourceVector(1000, 1048576, 1048576, 10000), evidence_reserve_bytes=8192,
        maximum_session_ns=60_000_000_000, maximum_effect_duration_ns=1_000_000_000,
        maximum_observation_age_ns=5_000_000_000,
        deadline=Deadline(BOOT, 7, 0, 1_000_000_000, 61_000_000_000, WALL+1_000_000_000, WALL+61_000_000_000))


def enrollment_transcript(request):
    return NativeApprovalTranscript(request.challenge_id, request.ceremony_nonce, request.input_commitment,
        enrollment_display_commitment(request), request.principal_id, request.actor_session,
        request.ui_identity, request.ui_commitment, request.helper_identity, request.helper_commitment,
        clock(1_050_000_000), 0, 0)


def effect_request(enrollment, *, restore=None, **changes):
    process = ProcessResourceIdentity(104, 100, H)
    original, target = CpuRateLimit(0, 0), CpuRateLimit.hard_cap(100)
    restoring = restore is not None
    expected = target if restoring else original
    values = dict(request_id='request:restore' if restoring else 'request:cap', scope_id=enrollment.scope_id,
        task_id='task:owned-cpu', proposal_id='proposal:restore' if restoring else 'proposal:cap',
        principal_id=enrollment.principal_id, actor_session=enrollment.actor_session,
        owner_session_nonce=enrollment.owner_session_nonce, operation=RESTORE_OPERATION if restoring else CAP_OPERATION,
        process_identity=process, job_digest=H, expected_limit=CpuRateObservation(process, H, ObservationState.MEASURED,
            expected, 1, 1_020_000_000), target_limit=original if restoring else target, original_limit=original,
        task_revision=H, policy_commitment=H, adapter_commitment=H, environment_commitment=H,
        source_commitment=H, observer_commitment=H, operation_budget=budget(1, wall_time_ms=1000,
            max_bytes_read=8192, max_bytes_written=8192), required_outcome_bytes=4096,
        deadline=enrollment.deadline, maximum_observation_age_ns=5_000_000_000, maximum_duration_ns=1_000_000_000,
        consequences=('consequence:owned-worker-cap',), restoration_of=None if restore is None else restore.request_id,
        original_request_commitment=None if restore is None else restore.input_commitment)
    return OwnedCpuRequest(**dict(values, **changes))


def effect_transcript(enrollment, request, **changes):
    # A later prepared approval helper has new lifetimes but the enrolled code.
    values = dict(challenge_id='challenge:restore' if request.operation == RESTORE_OPERATION else 'challenge:cap',
        ceremony_nonce='5'*32 if request.operation == RESTORE_OPERATION else '4'*32,
        request_commitment=request.input_commitment, displayed_commitment=approval_display_commitment(request),
        principal_id=request.principal_id, actor_session=request.actor_session,
        ui_identity=ProcessResourceIdentity(105, 101, H), ui_commitment=enrollment.ui_commitment,
        helper_identity=ProcessResourceIdentity(106, 101, H), helper_commitment=enrollment.helper_commitment,
        observed_clock=clock(1_050_000_000), native_hresult=0, native_result=0)
    return NativeApprovalTranscript(**dict(values, **changes))


class ControlledOwners:
    """Private object registry and actual RLock are controlled, not native proof."""
    def __init__(self, request):
        self.context = object(); self.request = request
        self.peer = PeerIdentity(request.principal_id, request.actor_session)
        self.current = True; self.proofs = {}; self.prepared = {}; self.lock = threading.RLock()
        self.samples = (clock(1_000_000_000), clock()); self.calls = []; self.on_check = None
        self.on_clock = None; self.return_value = None

    def authenticate(self, context):
        with self.lock:
            if context is not self.context or not self.current: raise ContractError('CONTROLLED_CONTEXT_DENIED')
            return self.peer

    def owner_enrollment_expected(self, context):
        self.authenticate(context)
        return self.request

    def clock(self):
        if self.on_clock is not None: self.on_clock()
        return self.samples

    def proof(self, phase, request, transcript):
        token = object()
        self.proofs[token] = (phase, self.request.canonical_wire,
            None if request is None else request.canonical_wire, transcript.canonical_wire)
        return token

    def require_owner_authority_current(self, phase, enrollment, request, transcript, proof, peer, context):
        with self.lock:
            self.calls.append(phase)
            if self.on_check is not None: self.on_check(phase)
            if self.authenticate(context) != peer or enrollment.canonical_wire != self.request.canonical_wire:
                raise ContractError('CONTROLLED_BINDING_DENIED')
            if phase in ('ENROLL', 'APPROVE_CAP', 'APPROVE_RESTORE'):
                if self.proofs.get(proof) != (phase, enrollment.canonical_wire,
                        None if request is None else request.canonical_wire, transcript.canonical_wire):
                    raise ContractError('CONTROLLED_PROOF_DENIED')
            return self.return_value

    def require_prepared_basis(self, proposal, basis, peer):
        if not self.current or peer != self.peer or self.prepared.get(proposal.record_id) != basis:
            raise ContractError('CONTROLLED_PREPARED_DENIED')

    def require_admission(self, permit, basis, peer):
        if not self.current or peer != self.peer or self.prepared.get(permit.as_dict()['proposal_ref']) != basis:
            raise ContractError('CONTROLLED_ADMISSION_DENIED')


class BarrierJournal(SqliteJournal):
    barrier = None
    after_commit = None

    def commit(self, *args, **kwargs):
        if self.barrier is not None: self.barrier.wait(timeout=5)
        result = super().commit(*args, **kwargs)
        if self.after_commit is not None: self.after_commit()
        return result


class Fixture:
    def __init__(self, schema):
        self.request = enrollment_request(); self.owners = ControlledOwners(self.request)
        self.root = ROOT/'.agents/fixtures/kernel-owner-authority'/uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=False)
        self.codec = RecordCodec(schema); self.fault = None
        self.store = BarrierJournal(self.root, self.codec, (INSTALLATION, PROJECT), create=True,
                                   profile=STORE_PROFILE, before_commit=self.inject)
        self.kernel = KernelTransactions(self.store, self.codec, INSTALLATION, self.owners)
        NATIVE_FIXTURES.append(self)

    def inject(self):
        if self.fault is not None: self.fault()

    def close(self):
        self.store.close()

    def cell(self, key):
        return self.store.snapshot((key,))[0]

    def row(self):
        return strict_loads(self.cell(enrollment_key(INSTALLATION, self.request.request_id)).value_wire)

    def begin(self):
        return self.kernel.begin_owner_enrollment(self.request.canonical_wire, self.owners.context)

    def enroll(self):
        transcript = enrollment_transcript(self.request)
        proof = self.owners.proof('ENROLL', None, transcript)
        return self.kernel.enroll_owner(self.request.canonical_wire, enrollment_transcript_bytes(transcript), proof, self.owners.context)

    def approve(self, request=None, transcript=None, proof=None):
        request = request or effect_request(self.request); transcript = transcript or effect_transcript(self.request, request)
        phase = 'APPROVE_CAP' if request.operation == CAP_OPERATION else 'APPROVE_RESTORE'
        proof = self.owners.proof(phase, request, transcript) if proof is None else proof
        return self.kernel.approve_owned_cpu(self.request.request_id, request.canonical_wire,
            transcript.canonical_wire, proof, self.owners.context)

    def allow_basis(self, field='cap_approval'):
        data = self.row()[field]; parsed = self.codec.decode(data['proposal_wire'].encode('utf-8'))
        self.owners.prepared[parsed.record_id] = data['basis_wire'].encode('utf-8')
        return parsed.canonical_wire

    def controlled_control_change(self, **changes):
        """Explicit adversarial fixture write through the actual canonical store."""
        cell = self.cell(self.kernel._control); value = strict_loads(cell.value_wire)
        value.update(changes)
        decision = self.codec.decode(self.store.replay(INSTALLATION, 0, 1)[0].payload_wire).as_dict()
        decision.update(record_id='decision:'+uuid.uuid4().hex, reason_codes=['CONTROLLED_FAULT_INJECTION'])
        self.kernel._commit(self.codec.decode(canonical_bytes(decision)), 'event:'+uuid.uuid4().hex,
            'kernel.fixture.control.fault', self.owners.peer, clock(), {cell.key: cell},
            {cell.key: canonical_bytes(value)}, self.request.policy_commitment)


class OwnerAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT/'contracts/schemas/records.schema.json').read_bytes())

    def fixture(self, enrolled=False):
        value = Fixture(self.schema); self.addCleanup(value.close)
        if enrolled: value.begin(); value.enroll()
        return value

    def test_challenge_is_pending_and_creates_no_grant(self):
        f = self.fixture(); result = f.begin()
        self.assertEqual(f.row()['state'], 'CHALLENGE')
        self.assertEqual(f.codec.decode(result.record_wire).as_dict()['outcome'], 'SEEK_AUTHORITY')
        self.assertEqual(f.cell(grant_key_for(f.request)).generation, 0)
        self.assertEqual(strict_loads(f.cell(f.kernel._control).value_wire)['authority_generation'], 0)

    def test_enrollment_consumes_challenge_and_advances_exact_generation(self):
        f = self.fixture(); f.begin(); result = f.enroll()
        self.assertEqual(f.row()['state'], 'ENROLLED'); self.assertEqual(f.row()['authority_generation'], 1)
        self.assertEqual(f.row()['enrollment_transcript_wire'], enrollment_transcript_bytes(enrollment_transcript(f.request)).decode())
        for kind, value in (('challenge', f.request.challenge_id), ('nonce', f.request.ceremony_nonce)):
            self.assertEqual(strict_loads(f.cell(ceremony_key(INSTALLATION, kind, value)).value_wire)['state'], 'CONSUMED')
        self.assertEqual(f.codec.decode(result.record_wire).as_dict()['outcome'], 'ALLOW')
        self.assertEqual(f.cell(grant_key_for(f.request)).generation, 0)

    def test_default_owner_and_missing_capability_are_closed(self):
        f = self.fixture(); closed = KernelTransactions(f.store, f.codec, INSTALLATION)
        with self.assertRaises(ContractError): closed.begin_owner_enrollment(f.request.canonical_wire, object())
        f.owners.require_owner_authority_current = None
        with self.assertRaisesRegex(ContractError, 'PROVIDER_UNAVAILABLE'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_boolean_native_decision_cannot_commit(self):
        f = self.fixture(); f.owners.return_value = True
        with self.assertRaisesRegex(ContractError, 'DECISION_INVALID'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_expected_enrollment_and_wrong_original_context_are_denied(self):
        f = self.fixture(); altered = replace(f.request, source_commitment=H2)
        with self.assertRaisesRegex(ContractError, 'EXPECTED_ENROLLMENT_CHANGED'):
            f.kernel.begin_owner_enrollment(altered.canonical_wire, f.owners.context)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_DENIED'):
            f.kernel.begin_owner_enrollment(f.request.canonical_wire, object())
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_reported_verified_data_without_registered_proof_is_denied(self):
        f = self.fixture(); f.begin(); transcript = enrollment_transcript(f.request)
        for proof in (True, False, object(), 'sha256:'+'a'*64):
            with self.subTest(proof_type=type(proof).__name__), self.assertRaisesRegex(ContractError, 'PROOF_DENIED'):
                f.kernel.enroll_owner(f.request.canonical_wire, enrollment_transcript_bytes(transcript), proof, f.owners.context)
        self.assertEqual(f.row()['state'], 'CHALLENGE')

    def test_duplicate_challenge_and_enrollment_are_not_reissued(self):
        f = self.fixture(); f.begin()
        with self.assertRaisesRegex(ContractError, 'ALREADY_DESIGNATED'): f.begin()
        f.enroll()
        with self.assertRaisesRegex(ContractError, 'NOT_PENDING'): f.enroll()
        self.assertEqual(f.row()['authority_generation'], 1)

    def test_cancelled_or_wrong_domain_enrollment_transcript_is_denied(self):
        f = self.fixture(); f.begin(); transcript = enrollment_transcript(f.request)
        with self.assertRaisesRegex(ContractError, 'TRANSCRIPT_FIELDS'):
            f.kernel.enroll_owner(f.request.canonical_wire, transcript.canonical_wire, object(), f.owners.context)
        cancelled = replace(transcript, native_result=6); proof = f.owners.proof('ENROLL', None, cancelled)
        with self.assertRaisesRegex(ContractError, 'REPORTED_VERIFIED_REQUIRED'):
            f.kernel.enroll_owner(f.request.canonical_wire, enrollment_transcript_bytes(cancelled), proof, f.owners.context)
        self.assertEqual(f.row()['state'], 'CHALLENGE')

    def test_cap_approval_writes_grant_budget_basis_and_real_events_atomically(self):
        f = self.fixture(True); request = effect_request(f.request); f.approve(request)
        row = f.row(); grant_key = grant_key_for(f.request)
        grant = f.codec.decode(f.cell(grant_key).value_wire).as_dict()
        self.assertEqual(grant['operation_classes'], [CAP_OPERATION, RESTORE_OPERATION])
        self.assertEqual(grant['delegation'], 'PROHIBITED'); self.assertEqual(grant['grantee_id'], f.request.principal_id)
        vectors = read_budget(f.cell(budget_key(grant_key)).value_wire, budget_key(grant_key))
        self.assertEqual(vectors, (f.request.authority_budget, f.request.recovery_budget, ZERO_BUDGET, ZERO_BUDGET))
        basis, key, read_set = read_basis(row['cap_approval']['basis_wire'].encode('utf-8'), f.codec)
        self.assertEqual(key, grant_key); self.assertEqual(read_set.authority_generation, 1)
        self.assertEqual(basis['owner_input_commitment'], request.input_commitment)
        self.assertEqual(owned_cpu_proposal(f.codec, request).canonical_wire, row['cap_approval']['proposal_wire'].encode())
        events = [f.codec.decode(item.event_wire).as_dict()['event_type'] for item in f.store.replay(INSTALLATION, 0, 128)]
        self.assertNotIn('kernel.development.allocation', events)
        f.store.validate(); f.store.store_position()

    def test_effect_ceremony_cannot_reuse_enrollment_challenge_or_nonce(self):
        f = self.fixture(True); request = effect_request(f.request)
        for changed in (dict(challenge_id=f.request.challenge_id), dict(ceremony_nonce=f.request.ceremony_nonce)):
            with self.subTest(changed=changed), self.assertRaisesRegex(ContractError, 'CEREMONY_REUSED'):
                f.approve(request, effect_transcript(f.request, request, **changed))
        self.assertIsNone(f.row()['cap_approval'])

    def test_cap_replay_and_a_second_worker_do_not_expand_authority(self):
        f = self.fixture(True); request = effect_request(f.request); f.approve(request)
        for candidate in (request, replace(request, request_id='request:other', proposal_id='proposal:other')):
            with self.subTest(request=candidate.request_id), self.assertRaisesRegex(ContractError, 'ALREADY_APPROVED'):
                f.approve(candidate)
        self.assertIsNone(f.row()['restore_approval'])

    def test_policy_source_session_image_and_budget_mismatches_deny(self):
        f = self.fixture(True)
        changes = [dict(policy_commitment=H2), dict(source_commitment=H2), dict(owner_session_nonce='9'*32),
            dict(maximum_observation_age_ns=f.request.maximum_observation_age_ns+1),
            dict(operation_budget=budget(1, wall_time_ms=6000, max_bytes_read=8192, max_bytes_written=8192))]
        request = effect_request(f.request)
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaises(ContractError): f.approve(replace(request, **changed))
        process = replace(request.process_identity, image_digest=H2)
        wrong = replace(request, process_identity=process, expected_limit=replace(request.expected_limit, identity=process))
        with self.assertRaisesRegex(ContractError, 'WORKER_IMAGE'): f.approve(wrong)
        self.assertIsNone(f.row()['cap_approval'])

    def test_fresh_helpers_keep_code_binding_and_require_new_proof(self):
        f = self.fixture(True); request = effect_request(f.request)
        transcript = effect_transcript(f.request, request, helper_commitment=H2)
        with self.assertRaisesRegex(ContractError, 'APPROVAL_CODE'): f.approve(request, transcript)
        transcript = effect_transcript(f.request, request)
        self.assertNotEqual(transcript.helper_identity, f.request.helper_identity)
        f.approve(request, transcript)
        self.assertIsNotNone(f.row()['cap_approval'])

    def test_existing_prepare_consume_uses_new_basis_but_never_dispatches(self):
        f = self.fixture(True); f.approve(); proposal = f.allow_basis()
        prepared = f.kernel.prepare(proposal, f.owners.context)
        consumed = f.kernel.consume(prepared.record_wire, f.owners.context)
        self.assertEqual(f.codec.decode(consumed.record_wire).as_dict()['status'], 'CONSUMED')
        with self.assertRaises(ContractError): f.kernel.consume(prepared.record_wire, f.owners.context)
        with self.assertRaisesRegex(ContractError, 'RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE'): f.kernel.require_runtime_admission()

    def test_restore_requires_consumed_cap_and_its_separate_approval(self):
        f = self.fixture(True); cap = effect_request(f.request); f.approve(cap)
        restore = effect_request(f.request, restore=cap)
        with self.assertRaises(ContractError): f.approve(restore)
        prepared = f.kernel.prepare(f.allow_basis(), f.owners.context)
        with self.assertRaisesRegex(ContractError, 'NOT_CANONICALLY_CONSUMED'): f.approve(restore)
        f.kernel.consume(prepared.record_wire, f.owners.context)
        f.approve(restore)
        grant = grant_key_for(f.request)
        limit, recovery, held, charged = read_budget(f.cell(budget_key(grant)).value_wire, budget_key(grant))
        self.assertEqual((recovery, held, charged), (ZERO_BUDGET, ZERO_BUDGET, cap.operation_budget))
        final = f.kernel.prepare(f.allow_basis('restore_approval'), f.owners.context)
        f.kernel.consume(final.record_wire, f.owners.context)
        self.assertEqual(read_budget(f.cell(budget_key(grant)).value_wire, budget_key(grant))[3].as_dict()['max_effects'], 2)
        with self.assertRaisesRegex(ContractError, 'ALREADY_APPROVED'): f.approve(restore)

    def test_wrong_restore_parent_cannot_unlock_reserved_budget(self):
        f = self.fixture(True); cap = effect_request(f.request); f.approve(cap)
        restore = effect_request(f.request, restore=cap, original_request_commitment=H2)
        with self.assertRaisesRegex(ContractError, 'RESTORATION_LINK_MISMATCH'): f.approve(restore)
        self.assertEqual(read_budget(f.cell(budget_key(grant_key_for(f.request))).value_wire,
            budget_key(grant_key_for(f.request)))[1], f.request.recovery_budget)

    def test_stop_before_enrollment_consumes_no_proof_and_blocks_new_authority(self):
        f = self.fixture(); f.begin(); f.kernel.stop_owner_authority(f.request.request_id, f.owners.context, 'reason:stop')
        self.assertEqual(f.row()['state'], 'STOPPED')
        with self.assertRaises(ContractError): f.enroll()
        with self.assertRaises(ContractError): f.begin()

    def test_stop_after_approval_revokes_grant_and_invalidates_preparation(self):
        f = self.fixture(True); f.approve(); proposal = f.allow_basis()
        f.kernel.stop_owner_authority(f.request.request_id, f.owners.context, 'reason:stop')
        self.assertEqual(f.row()['state'], 'STOPPED'); self.assertEqual(f.row()['authority_generation'], 2)
        self.assertEqual(f.codec.decode(f.cell(grant_key_for(f.request)).value_wire).as_dict()['status'], 'REVOKED')
        with self.assertRaises(ContractError): f.kernel.prepare(proposal, f.owners.context)
        with self.assertRaises(ContractError): f.approve()

    def test_revocation_is_durable_and_recovery_never_reissues(self):
        f = self.fixture(True); f.approve()
        f.kernel.revoke_owner_authority(f.request.request_id, f.owners.context, 'reason:revoke')
        before = f.store.position(INSTALLATION)
        state = f.kernel.recover_owner_enrollment(f.request.request_id, f.owners.context)
        self.assertEqual(state.as_dict()['state'], 'REVOKED'); self.assertEqual(f.store.position(INSTALLATION), before)

    def test_clock_boot_resume_epoch_rollback_and_stale_are_denied(self):
        for changes in (dict(boot_id='boot:other'), dict(resume_generation=1), dict(durable_epoch=8),
                        dict(value=999_999_999), dict(value=61_000_000_000), dict(wall_trusted=False)):
            with self.subTest(changes=changes):
                f = self.fixture(); f.owners.samples = (clock(1_000_000_000), clock(**changes))
                with self.assertRaises(ContractError): f.begin()
                self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_last_clock_revocation_is_seen_by_combined_native_predicate(self):
        f = self.fixture(); f.owners.on_clock = lambda: setattr(f.owners, 'current', False)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_DENIED'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_slow_native_return_is_denied_without_commit(self):
        f = self.fixture(); f.owners.on_check = lambda phase: time.sleep(.055)
        with self.assertRaisesRegex(ContractError, 'TOO_SLOW'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_precommit_revocation_rolls_back_all_cells_and_events(self):
        f = self.fixture(); f.fault = lambda: setattr(f.owners, 'current', False)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_DENIED'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)
        self.assertEqual(f.cell(enrollment_key(INSTALLATION, f.request.request_id)).generation, 0)

    def test_control_exceptions_rollback_exact_primary_and_all_prefixes(self):
        for kind in (KeyboardInterrupt, SystemExit):
            with self.subTest(kind=kind.__name__):
                f = self.fixture(); primary = kind('controlled primary')
                def fail(): raise primary
                f.fault = fail
                with self.assertRaises(kind) as caught: f.begin()
                self.assertIs(caught.exception, primary)
                self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)
                self.assertEqual(f.cell(enrollment_key(INSTALLATION, f.request.request_id)).generation, 0)

    def test_enrollment_fault_cannot_partially_consume_challenge(self):
        f = self.fixture(); f.begin()
        def fail(): raise RuntimeError('after native SQLite inserts')
        f.fault = fail
        with self.assertRaisesRegex(RuntimeError, 'SQLite'): f.enroll()
        self.assertEqual(f.row()['state'], 'CHALLENGE')
        self.assertEqual(strict_loads(f.cell(ceremony_key(INSTALLATION, 'nonce', f.request.ceremony_nonce)).value_wire)['state'], 'RESERVED')
        f.fault = None; f.enroll(); self.assertEqual(f.row()['state'], 'ENROLLED')

    def test_postcommit_denial_preserves_committed_tombstone_for_recovery(self):
        f = self.fixture(); f.store.after_commit = lambda: setattr(f.owners, 'current', False)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_DENIED'): f.begin()
        self.assertEqual(f.row()['state'], 'CHALLENGE')
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 1)
        f.owners.current = True; f.store.after_commit = None
        with self.assertRaisesRegex(ContractError, 'ALREADY_DESIGNATED'): f.begin()
        self.assertEqual(f.kernel.recover_owner_enrollment(f.request.request_id, f.owners.context).as_dict()['state'], 'CHALLENGE')

    def test_concurrent_first_enrollment_has_one_real_sqlite_winner(self):
        f = self.fixture(); other = BarrierJournal(f.root, f.codec, (INSTALLATION, PROJECT), profile=STORE_PROFILE)
        self.addCleanup(other.close); second = KernelTransactions(other, f.codec, INSTALLATION, f.owners)
        barrier = threading.Barrier(2); f.store.barrier = barrier; other.barrier = barrier
        def run(kernel):
            try: kernel.begin_owner_enrollment(f.request.canonical_wire, f.owners.context); return 'COMMITTED'
            except ContractError: return 'DENIED'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, (f.kernel, second)))
        self.assertEqual(sorted(results), ['COMMITTED', 'DENIED'])
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 1)

    def test_concurrent_cap_approvals_have_one_grant_and_one_ceremony(self):
        f = self.fixture(True); request = effect_request(f.request); transcript = effect_transcript(f.request, request)
        proof = f.owners.proof('APPROVE_CAP', request, transcript)
        other = BarrierJournal(f.root, f.codec, (INSTALLATION, PROJECT), profile=STORE_PROFILE)
        self.addCleanup(other.close); second = KernelTransactions(other, f.codec, INSTALLATION, f.owners)
        barrier = threading.Barrier(2); f.store.barrier = barrier; other.barrier = barrier
        def run(kernel):
            try:
                kernel.approve_owned_cpu(f.request.request_id, request.canonical_wire, transcript.canonical_wire, proof, f.owners.context)
                return 'COMMITTED'
            except ContractError: return 'DENIED'
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, (f.kernel, second)))
        self.assertEqual(sorted(results), ['COMMITTED', 'DENIED']); self.assertEqual(f.cell(grant_key_for(f.request)).generation, 1)

    def test_reopen_preserves_consumed_nonce_and_never_replays_approval(self):
        f = self.fixture(True); f.approve(); proposal = f.allow_basis()
        prepared = f.kernel.prepare(proposal, f.owners.context); f.kernel.consume(prepared.record_wire, f.owners.context)
        before = f.store.position(INSTALLATION); f.store.close()
        f.store = BarrierJournal(f.root, f.codec, (INSTALLATION, PROJECT), profile=STORE_PROFILE)
        f.kernel = KernelTransactions(f.store, f.codec, INSTALLATION, f.owners)
        recovered = f.kernel.recover_owner_enrollment(f.request.request_id, f.owners.context)
        self.assertEqual(recovered.as_dict()['cap_approval']['proposal_wire'], proposal.decode())
        self.assertEqual(f.store.position(INSTALLATION), before)
        with self.assertRaises(ContractError): f.enroll()
        with self.assertRaises(ContractError): f.kernel.consume(prepared.record_wire, f.owners.context)

    def test_fresh_kernel_with_old_data_and_no_provider_remains_closed(self):
        f = self.fixture(True); f.approve(); before = f.store.position(INSTALLATION)
        closed = KernelTransactions(f.store, f.codec, INSTALLATION)
        with self.assertRaises(ContractError): closed.recover_owner_enrollment(f.request.request_id, object())
        with self.assertRaises(ContractError): closed.require_runtime_admission()
        self.assertEqual(f.store.position(INSTALLATION), before)

    def test_missing_and_malformed_expected_provider_cannot_allocate(self):
        for result in (None, True, object()):
            with self.subTest(result_type=type(result).__name__):
                f = self.fixture(); f.owners.owner_enrollment_expected = lambda context: result
                with self.assertRaisesRegex(ContractError, 'EXPECTED_ENROLLMENT_REQUIRED'): f.begin()
                self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)
        f = self.fixture(); f.owners.owner_enrollment_expected = None
        with self.assertRaisesRegex(ContractError, 'PROVIDER_UNAVAILABLE'): f.begin()

    def test_nonzero_bootstrap_generations_and_unregistered_project_are_denied(self):
        for changes in (dict(authority_generation=1), dict(policy_generation=1), dict(scope_id='project:unregistered')):
            with self.subTest(changes=changes):
                f = self.fixture(); f.request = replace(f.request, **changes); f.owners.request = f.request
                with self.assertRaises(ContractError): f.begin()
                self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_copied_native_identity_is_not_the_designated_expected_root(self):
        f = self.fixture(); copied = replace(f.request, private_root=replace(f.request.private_root, file_id_hex='8'*32))
        with self.assertRaisesRegex(ContractError, 'EXPECTED_ENROLLMENT_CHANGED'):
            f.kernel.begin_owner_enrollment(copied.canonical_wire, f.owners.context)
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_enrollment_helper_and_ui_lifetimes_are_exact(self):
        f = self.fixture(); f.begin()
        for name in ('helper_identity', 'ui_identity'):
            original = enrollment_transcript(f.request)
            transcript = replace(original, **{name:replace(getattr(original, name), creation_time=101)})
            proof = f.owners.proof('ENROLL', None, transcript)
            with self.subTest(name=name), self.assertRaisesRegex(ContractError, 'TRANSCRIPT_OWNER_MISMATCH'):
                f.kernel.enroll_owner(f.request.canonical_wire, enrollment_transcript_bytes(transcript), proof, f.owners.context)
        self.assertEqual(f.row()['state'], 'CHALLENGE')

    def test_changed_authority_fence_policy_or_environment_cannot_rebase_approval(self):
        for changed in (dict(authority_generation=2), dict(fence_generation=2),
                        dict(policy_commitment=H2), dict(environment_commitment=H2)):
            with self.subTest(changed=changed):
                f = self.fixture(True); f.controlled_control_change(**changed)
                with self.assertRaisesRegex(ContractError, 'CURRENT_CONTROL_CHANGED'): f.approve()
                self.assertIsNone(f.row()['cap_approval'])

    def test_future_and_stale_native_preconditions_are_not_zero_observations(self):
        for observed in (1_100_000_001, 1):
            with self.subTest(observed=observed):
                f = self.fixture(True); request = effect_request(f.request)
                request = replace(request, expected_limit=replace(request.expected_limit, observed_monotonic_ns=observed),
                    maximum_observation_age_ns=100_000_000)
                with self.assertRaisesRegex(ContractError, 'OBSERVATION_STALE'): f.approve(request)
                self.assertIsNone(f.row()['cap_approval'])

    def test_malformed_clock_instance_is_revalidated_before_comparison(self):
        f = self.fixture(); bad = clock(); object.__setattr__(bad, 'monotonic_ns', True)
        f.owners.samples = (clock(1_000_000_000), bad)
        with self.assertRaisesRegex(ContractError, 'INVALID_TEMPORAL_INTEGER'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_individually_progressing_clock_pair_cannot_roll_back_guard_highwater(self):
        f = self.fixture(); f.owners.samples = (clock(1_000_000_000), clock(2_000_000_000))
        def reset(phase):
            if len(f.owners.calls) == 1: f.owners.samples = (clock(1_000_000_000), clock(1_500_000_000))
        f.owners.on_check = reset
        with self.assertRaisesRegex(ContractError, 'MONOTONIC_ROLLBACK'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_callback_elapsed_time_cannot_outlive_a_still_current_sample(self):
        f = self.fixture(); deadline = replace(f.request.deadline,
            expires_monotonic_ns=1_100_100_000, expires_wall_ns=WALL+1_100_100_000)
        f.request = replace(f.request, deadline=deadline); f.owners.request = f.request
        f.owners.on_check = lambda phase: time.sleep(.003)
        with self.assertRaisesRegex(ContractError, 'DEADLINE_ELAPSED'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_final_external_callback_is_combined_current_owner_predicate(self):
        f = self.fixture(); trace = []
        authenticate, sample, combined = f.owners.authenticate, f.owners.clock, f.owners.require_owner_authority_current
        def auth(context): trace.append('authenticate'); return authenticate(context)
        def current_clock(): trace.append('clock'); return sample()
        def predicate(*args):
            value = combined(*args); trace.append('combined'); return value
        f.owners.authenticate, f.owners.clock, f.owners.require_owner_authority_current = auth, current_clock, predicate
        f.begin(); self.assertEqual(trace[-1], 'combined'); self.assertEqual(trace.count('combined'), 3)

    def test_approval_failure_rolls_back_both_scope_streams_and_every_projection(self):
        f = self.fixture(True); before = tuple(f.store.position(scope) for scope in (INSTALLATION, PROJECT))
        def fail(): raise RuntimeError('controlled approval fault')
        f.fault = fail
        with self.assertRaisesRegex(RuntimeError, 'approval fault'): f.approve()
        self.assertEqual(tuple(f.store.position(scope) for scope in (INSTALLATION, PROJECT)), before)
        self.assertIsNone(f.row()['cap_approval']); self.assertEqual(f.cell(grant_key_for(f.request)).generation, 0)
        f.fault = None; f.approve(); self.assertIsNotNone(f.row()['cap_approval'])

    def test_precommit_enrollment_revocation_does_not_burn_ceremony(self):
        f = self.fixture(); f.begin(); f.fault = lambda: setattr(f.owners, 'current', False)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_DENIED'): f.enroll()
        self.assertEqual(f.row()['state'], 'CHALLENGE')
        self.assertEqual(strict_loads(f.cell(ceremony_key(INSTALLATION, 'nonce', f.request.ceremony_nonce)).value_wire)['state'], 'RESERVED')

    def test_postcommit_enrollment_denial_keeps_consumed_ceremony_and_generation(self):
        f = self.fixture(); f.begin(); f.store.after_commit = lambda: setattr(f.owners, 'current', False)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_DENIED'): f.enroll()
        self.assertEqual(f.row()['state'], 'ENROLLED'); self.assertEqual(f.row()['authority_generation'], 1)
        f.owners.current = True; f.store.after_commit = None
        with self.assertRaisesRegex(ContractError, 'NOT_PENDING'): f.enroll()

    def test_postcommit_approval_denial_retains_grant_but_never_reapproves(self):
        f = self.fixture(True); f.store.after_commit = lambda: setattr(f.owners, 'current', False)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_DENIED'): f.approve()
        self.assertEqual(f.cell(grant_key_for(f.request)).generation, 1); self.assertIsNotNone(f.row()['cap_approval'])
        f.owners.current = True; f.store.after_commit = None
        with self.assertRaisesRegex(ContractError, 'ALREADY_APPROVED'): f.approve()
        self.assertIsNotNone(f.kernel.recover_owner_enrollment(f.request.request_id, f.owners.context).as_dict()['cap_approval'])

    def test_stop_keeps_unknown_held_liability_and_burns_no_new_effect(self):
        f = self.fixture(True); f.approve(); prepared = f.kernel.prepare(f.allow_basis(), f.owners.context)
        grant = grant_key_for(f.request); before = read_budget(f.cell(budget_key(grant)).value_wire, budget_key(grant))
        f.kernel.stop_owner_authority(f.request.request_id, f.owners.context, 'reason:stop-held')
        with self.assertRaises(ContractError): f.kernel.consume(prepared.record_wire, f.owners.context)
        self.assertEqual(read_budget(f.cell(budget_key(grant)).value_wire, budget_key(grant)), before)
        self.assertEqual(before[3], ZERO_BUDGET); self.assertEqual(before[2].as_dict()['max_effects'], 1)

    def test_expired_read_only_recovery_does_not_refresh_old_authority(self):
        f = self.fixture(True); f.approve(); before = tuple(f.store.position(scope) for scope in (INSTALLATION, PROJECT))
        f.owners.samples = (clock(70_000_000_000), clock(71_000_000_000))
        state = f.kernel.recover_owner_enrollment(f.request.request_id, f.owners.context)
        self.assertEqual(state.as_dict()['state'], 'ENROLLED')
        self.assertEqual(tuple(f.store.position(scope) for scope in (INSTALLATION, PROJECT)), before)
        restore = effect_request(f.request, restore=effect_request(f.request))
        with self.assertRaises(ContractError): f.approve(restore)
        with self.assertRaises(ContractError): f.kernel.require_runtime_admission()

    def test_restore_rejects_semantically_wrong_durable_consumption_index(self):
        from ceta.contracts.kernel_transactions import intent_key
        f = self.fixture(True); cap = effect_request(f.request); f.approve(cap)
        prepared = f.kernel.prepare(f.allow_basis(), f.owners.context)
        consumed = f.kernel.consume(prepared.record_wire, f.owners.context)
        permit = f.codec.decode(consumed.record_wire).as_dict()
        key = intent_key(PROJECT, permit['record_id']); cell = f.cell(key)
        value = strict_loads(cell.value_wire); value['consumption']['event_id'] = 'event:wrong-index'
        decision = f.codec.decode(f.store.replay(INSTALLATION, 0, 1)[0].payload_wire).as_dict()
        decision.update(record_id='decision:'+uuid.uuid4().hex, scope_id=PROJECT, reason_codes=['CONTROLLED_SEMANTIC_FAULT'])
        f.kernel._commit(f.codec.decode(canonical_bytes(decision)), 'event:'+uuid.uuid4().hex,
            'kernel.fixture.consumption.fault', f.owners.peer, clock(), {key: cell},
            {key: canonical_bytes(value)}, f.request.policy_commitment)
        f.store.store_position()
        with self.assertRaisesRegex(ContractError, 'CONSUMPTION_INDEX_INVALID'):
            f.approve(effect_request(f.request, restore=cap))

    def test_elapsed_counter_rollback_does_not_commit(self):
        f = self.fixture()
        with patch('ceta.kernel.owner_authority.time.perf_counter_ns', side_effect=(1000, 999)):
            with self.assertRaisesRegex(ContractError, 'ELAPSED_COUNTER_INVALID'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_elapsed_resolution_charge_denies_zero_tick_deadline(self):
        f = self.fixture()
        f.request = replace(f.request, deadline=replace(f.request.deadline,
            expires_monotonic_ns=1_100_000_001, expires_wall_ns=WALL+1_100_000_001))
        f.owners.request = f.request
        with patch('ceta.kernel.owner_authority.time.perf_counter_ns', side_effect=(1000, 1000)):
            with self.assertRaisesRegex(ContractError, 'DEADLINE_ELAPSED'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)

    def test_unavailable_elapsed_clock_denies_without_allocating(self):
        f = self.fixture()
        with patch('ceta.kernel.owner_authority.time.get_clock_info', side_effect=OSError('controlled unavailable')):
            with self.assertRaisesRegex(ContractError, 'ELAPSED_CLOCK_UNAVAILABLE'): f.begin()
        self.assertEqual(f.store.position(INSTALLATION).next_sequence, 0)


if __name__ == '__main__': unittest.main()

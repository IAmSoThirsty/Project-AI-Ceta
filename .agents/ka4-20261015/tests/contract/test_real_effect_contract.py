"""Controlled contract data; none of these fixtures authenticate a real ceremony."""
from dataclasses import replace
import json
import unittest

from ceta.contracts.kernel_transactions import BUDGET_FIELDS, BudgetVector
from ceta.contracts.real_effect import (CAP_OPERATION, RESTORE_OPERATION, CpuEffectObservation,
    NativeApprovalTranscript, OwnedCpuRequest, approval_display_bytes, approval_display_commitment,
    compare_cpu_observation, decode_cpu_effect_observation, decode_native_approval_transcript,
    decode_owned_cpu_request, require_approval_binding, require_restoration_link)
from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError, MAX_INTEGER, canonical_bytes, strict_loads
from ceta.contracts.workload_throttling import CpuRateLimit, CpuRateObservation

HASH = 'sha256:' + 'a' * 64
OTHER = 'sha256:' + 'b' * 64
MONO, WALL = 1_000_000_000, 1_700_000_000_000_000_000


def clock(delta=0):
    return ClockSample('boot:fixture', 1, 0, MONO + delta, WALL + delta, 1, True)


def request():
    identity = ProcessResourceIdentity(11, 33, HASH)
    expected = CpuRateObservation(identity, HASH, ObservationState.MEASURED, CpuRateLimit(0, 7), 0, MONO)
    budget = BudgetVector.from_dict({name: 1000 if name == 'wall_time_ms' else 1 if name == 'max_effects'
        else 8192 if name == 'max_bytes_written' else 0 for name in BUDGET_FIELDS})
    return OwnedCpuRequest('effect:one', 'scope:one', 'task:one', 'proposal:one', 'principal:one',
        'session:one', 'nonce:one', CAP_OPERATION, identity, HASH, expected, CpuRateLimit.hard_cap(1000),
        expected.limit, HASH, HASH, HASH, HASH, HASH, HASH, budget, 8192,
        Deadline('boot:fixture', 1, 0, MONO, MONO + 10_000_000_000, WALL - 1, WALL + 10_000_000_000),
        500_000_000, 100_000_000, ('cpu:reduced', 'restore:separate', 'cleanup:owned'))


def transcript(item):
    return NativeApprovalTranscript('challenge:one', 'ceremony:one', item.input_commitment,
        approval_display_commitment(item), item.principal_id, item.actor_session,
        ProcessResourceIdentity(22, 44, HASH), HASH, ProcessResourceIdentity(23, 45, HASH), HASH,
        clock(100), 0, 0)


def observation(item):
    return CpuEffectObservation(item.input_commitment, item.request_id, item.process_identity, item.job_digest,
        ProcessResourceIdentity(22, 44, OTHER), item.observer_commitment, 1, clock(100),
        ObservationState.MEASURED, item.target_limit, 'LIVE_IN_OWNED_JOB')


class RealEffectContractTests(unittest.TestCase):
    def test_complete_request_exact_roundtrip_and_detached_return_values(self):
        item = request(); decoded = decode_owned_cpu_request(item.canonical_wire)
        self.assertEqual(decoded, item); self.assertEqual(decoded.input_commitment, item.input_commitment)
        value = decoded.as_dict(); value['process_identity']['pid'] = 999
        value['consequences'].append('injected'); value['operation_budget']['max_effects'] = 99
        self.assertEqual(decoded, item); self.assertEqual(decode_owned_cpu_request(item.canonical_wire), item)

    def test_every_independent_request_binding_changes_the_complete_commitment(self):
        item = request()
        changes = {'request_id': 'effect:two', 'scope_id': 'scope:two', 'task_id': 'task:two',
            'proposal_id': 'proposal:two', 'principal_id': 'principal:two', 'actor_session': 'session:two',
            'owner_session_nonce': 'nonce:two', 'target_limit': CpuRateLimit.hard_cap(999),
            'task_revision': OTHER, 'policy_commitment': OTHER, 'adapter_commitment': OTHER,
            'environment_commitment': OTHER, 'source_commitment': OTHER, 'observer_commitment': OTHER,
            'required_outcome_bytes': 4096, 'maximum_duration_ns': 99_000_000,
            'maximum_observation_age_ns': 400_000_000, 'consequences': ('cpu:reduced',),
            'deadline': replace(item.deadline, expires_monotonic_ns=MONO + 9_000_000_000)}
        for name, value in changes.items():
            with self.subTest(name=name): self.assertNotEqual(replace(item, **{name: value}).input_commitment, item.input_commitment)
        expected = replace(item.expected_limit, version=1)
        self.assertNotEqual(replace(item, expected_limit=expected).input_commitment, item.input_commitment)

    def test_notification_flags_preserved_and_only_effective_reduction_allowed(self):
        item = request()
        for bad in (CpuRateLimit(0, 0), CpuRateLimit.hard_cap(10000), CpuRateLimit(13, 1000)):
            with self.subTest(bad=bad), self.assertRaises(ContractError): replace(item, target_limit=bad)
        prior = CpuRateLimit(13, 5000)
        current = replace(item.expected_limit, limit=prior)
        valid = replace(item, expected_limit=current, original_limit=prior, target_limit=CpuRateLimit(13, 1000))
        self.assertEqual(decode_owned_cpu_request(valid.canonical_wire), valid)
        with self.assertRaises(ContractError): replace(valid, target_limit=CpuRateLimit(5, 1000))

    def test_unavailable_and_wrong_target_preconditions_are_rejected(self):
        item = request()
        bad = replace(item.expected_limit, state=ObservationState.UNAVAILABLE, limit=None, reason='query:unavailable')
        with self.assertRaises(ContractError): replace(item, expected_limit=bad)
        with self.assertRaises(ContractError): replace(item, process_identity=ProcessResourceIdentity(12, 34, HASH))
        with self.assertRaises(ContractError): replace(item, job_digest=OTHER)

    def test_boolean_integer_overflow_and_unknown_shape_rejected(self):
        item = request()
        for name, value in [('required_outcome_bytes', True), ('maximum_duration_ns', False),
                ('maximum_observation_age_ns', 2**63), ('operation', True), ('consequences', ([],))]:
            with self.subTest(name=name), self.assertRaises(ContractError): replace(item, **{name: value})
        for mutate in (lambda v: v.update(approved=True), lambda v: v['deadline'].update(extra=1),
                       lambda v: v['process_identity'].update(pid=True), lambda v: v.update(consequences='cpu:reduced')):
            value = item.as_dict(); mutate(value)
            with self.assertRaises(ContractError): decode_owned_cpu_request(canonical_bytes(value))

    def test_required_single_effect_and_outcome_wall_budgets_are_conserved(self):
        item = request()
        for field, value in [('max_effects', 0), ('max_effects', 2), ('max_bytes_written', 4096), ('wall_time_ms', 1)]:
            values = item.operation_budget.as_dict(); values[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                replace(item, operation_budget=BudgetVector.from_dict(values))

    def test_duplicates_noncanonical_invalid_utf8_and_size_are_rejected(self):
        item = request(); wire = item.canonical_wire
        duplicate = wire.replace(b'{', b'{"profile":"injected",', 1)
        for bad in (duplicate, json.dumps(item.as_dict(), indent=2).encode(), b'\xff', b' ' * 32769, b''):
            with self.subTest(size=len(bad)), self.assertRaises(ContractError): decode_owned_cpu_request(bad)

    def test_distinct_restoration_binds_original_policy_and_parent_commitment(self):
        item = request()
        current = replace(item.expected_limit, limit=item.target_limit, version=1)
        restore = replace(item, request_id='restore:one', operation=RESTORE_OPERATION, expected_limit=current,
            target_limit=item.original_limit, restoration_of=item.request_id, original_request_commitment=item.input_commitment)
        require_restoration_link(item, restore)
        self.assertEqual(decode_owned_cpu_request(restore.canonical_wire), restore)
        for bad in (replace(restore, original_request_commitment=OTHER), replace(restore, scope_id='scope:two')):
            with self.assertRaises(ContractError): require_restoration_link(item, bad)
        with self.assertRaises(ContractError): replace(restore, request_id=item.request_id)
        with self.assertRaises(ContractError): replace(restore, target_limit=CpuRateLimit(0, 0))

    def test_complete_display_binds_exact_request_and_commitment(self):
        item = request(); display = strict_loads(approval_display_bytes(item))
        self.assertEqual(display['request'], item.as_dict()); self.assertEqual(display['request_commitment'], item.input_commitment)
        self.assertNotEqual(approval_display_commitment(item), approval_display_commitment(replace(item, request_id='effect:two')))

    def test_native_transcript_roundtrip_and_reported_results_are_data(self):
        item = request(); value = transcript(item)
        self.assertEqual(decode_native_approval_transcript(value.canonical_wire), value)
        self.assertEqual(value.reported_outcome, 'REPORTED_VERIFIED')
        self.assertEqual(replace(value, native_result=6).reported_outcome, 'REPORTED_CANCELLED')
        self.assertEqual(replace(value, native_result=None, native_hresult=-2147467259).reported_outcome, 'REPORTED_UNAVAILABLE')
        for native in range(1, 6): self.assertEqual(replace(value, native_result=native).reported_outcome, 'REPORTED_UNAVAILABLE')

    def test_transcript_rejects_boolean_success_and_hresult_result_contradictions(self):
        value = transcript(request())
        for change in ({'native_result': False}, {'native_hresult': False}, {'native_result': 7},
                       {'native_hresult': -1}, {'native_hresult': 1}, {'native_method': 'fake:approved'}):
            with self.subTest(change=change), self.assertRaises(ContractError): replace(value, **change)
        encoded = value.as_dict(); encoded['approved'] = True
        with self.assertRaises(ContractError): decode_native_approval_transcript(canonical_bytes(encoded))

    def test_declared_approval_binding_rejects_display_principal_session_and_cancel(self):
        item = request(); value = transcript(item)
        require_approval_binding(item, value, clock(), clock(200))
        for bad in (replace(value, displayed_commitment=OTHER), replace(value, principal_id='principal:two'),
                    replace(value, actor_session='session:two'), replace(value, native_result=6)):
            with self.assertRaises(ContractError): require_approval_binding(item, bad, clock(), clock(200))

    def test_approval_restart_resume_rollback_and_expiry_deny(self):
        item = request(); value = transcript(item)
        for changed in (replace(clock(200), boot_id='boot:two'), replace(clock(200), durable_epoch=2),
                        replace(clock(200), resume_generation=1), clock(-1), clock(10_000_000_000)):
            with self.assertRaises(ContractError): require_approval_binding(item, value, clock(), changed)

    def test_independent_observation_roundtrip_and_exact_match_discrepancy(self):
        item = request(); observed = observation(item)
        self.assertEqual(decode_cpu_effect_observation(observed.canonical_wire), observed)
        self.assertEqual(compare_cpu_observation(item, observed, clock(), clock(200), minimum_sequence=1), 'VERIFIED_MATCH')
        wrong = replace(observed, limit=CpuRateLimit.hard_cap(999))
        self.assertEqual(compare_cpu_observation(item, wrong, clock(), clock(200), minimum_sequence=1), 'DISCREPANCY')

    def test_measured_zero_or_disabled_and_unavailable_are_distinct(self):
        item = request(); observed = observation(item)
        disabled = replace(observed, limit=CpuRateLimit(0, 0))
        self.assertEqual(compare_cpu_observation(item, disabled, clock(), clock(200), minimum_sequence=1), 'DISCREPANCY')
        unavailable = replace(observed, state=ObservationState.UNAVAILABLE, limit=None, reason='query:failed')
        self.assertEqual(compare_cpu_observation(item, unavailable, clock(), clock(200), minimum_sequence=1), 'UNAVAILABLE')
        with self.assertRaises(ContractError): replace(unavailable, limit=CpuRateLimit(0, 0))

    def test_target_exit_or_membership_loss_never_verifies_job_policy_as_live_effect(self):
        item = request(); observed = observation(item)
        for target in ('EXITED', 'NOT_IN_OWNED_JOB', 'UNAVAILABLE'):
            changed = replace(observed, target_state=target)
            self.assertEqual(compare_cpu_observation(item, changed, clock(), clock(200), minimum_sequence=1), 'UNAVAILABLE')

    def test_same_pid_different_creation_is_not_a_simultaneous_separate_observer(self):
        item = request(); observed = observation(item)
        with self.assertRaises(ContractError): replace(observed, observer_identity=replace(item.process_identity, creation_time=34))

    def test_observer_wrong_request_job_code_or_target_rejected(self):
        item = request(); observed = observation(item)
        for change in ({'request_commitment': OTHER}, {'operation_id': 'effect:two'}, {'job_digest': OTHER},
                       {'observer_commitment': OTHER}, {'identity': ProcessResourceIdentity(12, 34, HASH)}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                compare_cpu_observation(item, replace(observed, **change), clock(), clock(200), minimum_sequence=1)

    def test_stale_future_replayed_wrong_boot_or_untrusted_observation_denied(self):
        item = request(); observed = observation(item)
        for change in ({'clock': clock(300)}, {'clock': replace(clock(100), boot_id='boot:two')},
                       {'clock': replace(clock(100), wall_trusted=False)}, {'sequence': 0}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                compare_cpu_observation(item, replace(observed, **change), clock(), clock(200), minimum_sequence=1)
        with self.assertRaises(ContractError): compare_cpu_observation(item, observed, clock(), clock(600_000_000), minimum_sequence=1)
        with self.assertRaises(ContractError): compare_cpu_observation(item, observed, clock(), clock(200), minimum_sequence=True)

    def test_nested_object_tampering_is_revalidated_before_commitment(self):
        item = request(); before = item.input_commitment
        object.__setattr__(item.target_limit, 'value', True)
        with self.assertRaises(ContractError): item.canonical_wire
        with self.assertRaises(ContractError): item.input_commitment
        self.assertTrue(before.startswith('sha256:'))

    def test_observation_target_creation_time_exact_wire_boundaries(self):
        item = request()
        for value in (1, MAX_INTEGER):
            identity = replace(item.process_identity, creation_time=value)
            changed = replace(item, process_identity=identity, expected_limit=replace(item.expected_limit, identity=identity))
            observed = observation(changed)
            self.assertEqual(decode_cpu_effect_observation(observed.canonical_wire), observed)
            self.assertEqual(compare_cpu_observation(changed, observed, clock(), clock(200), minimum_sequence=1), 'VERIFIED_MATCH')
        for value in (MAX_INTEGER + 1, 2**64 - 1):
            identity = replace(item.process_identity, creation_time=value)
            with self.assertRaisesRegex(ContractError, 'EFFECT_PROCESS_WIRE_RANGE'):
                replace(observation(item), identity=identity)

    def test_observation_observer_creation_time_exact_wire_boundaries(self):
        item = request(); observed = observation(item)
        for value in (1, MAX_INTEGER):
            changed = replace(observed, observer_identity=replace(observed.observer_identity, creation_time=value))
            self.assertEqual(decode_cpu_effect_observation(changed.canonical_wire), changed)
            self.assertEqual(compare_cpu_observation(item, changed, clock(), clock(200), minimum_sequence=1), 'VERIFIED_MATCH')
        for value in (MAX_INTEGER + 1, 2**64 - 1):
            identity = replace(observed.observer_identity, creation_time=value)
            with self.assertRaisesRegex(ContractError, 'EFFECT_PROCESS_WIRE_RANGE'):
                replace(observed, observer_identity=identity)

    def test_observation_zero_creation_time_rejected_in_both_wire_roles(self):
        observed = observation(request())
        for role in ('identity', 'observer_identity'):
            value = observed.as_dict(); value[role]['creation_time'] = 0
            with self.assertRaisesRegex(ContractError, 'RESOURCE_PROCESS_IDENTITY_INVALID'):
                decode_cpu_effect_observation(canonical_bytes(value))

    def test_unavailable_observation_cannot_hide_out_of_range_identity(self):
        observed = observation(request())
        for role in ('identity', 'observer_identity'):
            identity = replace(getattr(observed, role), creation_time=MAX_INTEGER + 1)
            with self.assertRaisesRegex(ContractError, 'EFFECT_PROCESS_WIRE_RANGE'):
                replace(observed, **{role: identity}, state=ObservationState.UNAVAILABLE, limit=None, reason='query:unavailable')


if __name__ == '__main__':
    unittest.main()

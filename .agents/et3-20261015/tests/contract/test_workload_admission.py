"""Measured-profile decisions and owner-port conformance, without fake integration."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import hashlib
import itertools
import threading
import unittest

from ceta.contracts.resource_management import AdmissionState, BudgetEnvelope, PressureLevel, ReservationResult, ResourceVector
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError, canonical_bytes
from ceta.resource.admission import (
    AdmissionRequest, MeasuredWorkloadProfile, ObservedWorkloadUsage,
    WorkloadAdmissionController, WorkloadEstimate, WorkloadPlanningDecision, WorkloadPlanningFacts,
    WorkloadRequirementEstimator, WorkloadShape, plan_budget_concurrency, plan_concurrency, plan_concurrency_with_facts,
)
from ceta.resource.budget import project_workload_budget


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def vector(value):
    return ResourceVector(value, value, value, value)


ZERO = vector(0)
NOW = 100_000_000


def profile(name="one", *, peak=10, shape=None, steady=None):
    return MeasuredWorkloadProfile("workload." + name, "profile." + name, digest("revision." + name),
                                  digest("source." + name), NOW - 10,
                                  (vector(peak),), 900, workload_shape=shape,
                                  steady_samples=(vector(steady),) if steady is not None else None)


def estimate(name="one", *, peak=10, shape=None, steady=None, margin=0):
    measured = profile(name, peak=peak, shape=shape, steady=steady)
    estimator = WorkloadRequirementEstimator((measured,), clock=lambda: NOW, headroom_milli=margin)
    return estimator.estimate(measured.workload_id, expected_profile_revision=measured.profile_revision,
                              expected_workload_shape=shape)


def budget(*, limit=100, control=10, measured=10, reserved=10, generation=7):
    return BudgetEnvelope("budget.one", vector(limit), vector(control), vector(measured), vector(reserved), generation)


def request(*, estimated=None, envelope=None, **changes):
    return replace(AdmissionRequest("request.one", envelope or budget(), estimated or estimate(),
                                    4, NOW, True, PressureLevel.NORMAL), **changes)


class RecordingPort:
    """Controlled port for wire tests only; no reservation/store integration claim."""
    def __init__(self, result=None, error=None):
        self.requests, self._lock, self.error = [], threading.Lock(), error
        self.result = result if result is not None else ReservationResult(AdmissionState.ADMITTED, "reservation.one", 7, ())

    def reserve(self, item):
        with self._lock:
            self.requests.append(item)
        if self.error is not None:
            raise self.error
        return self.result


class AdmissionBoundaryTests(unittest.TestCase):
    def test_future_profile_never_reaches_owner(self):
        port = RecordingPort()
        outcome = WorkloadAdmissionController(port, clock=lambda: NOW).admit(
            request(estimated=replace(estimate(), observed_monotonic_ns=NOW + 1)))
        self.assertEqual((outcome.state, outcome.reason_codes), (AdmissionState.STALE, ("WORKLOAD_PROFILE_STALE",)))
        self.assertEqual(port.requests, [])

    def test_profile_expired_since_estimation_never_reaches_owner(self):
        port = RecordingPort()
        outcome = WorkloadAdmissionController(port, clock=lambda: NOW, maximum_profile_age_ns=9).admit(request())
        self.assertEqual(outcome.reason_codes, ("WORKLOAD_PROFILE_STALE",))
        self.assertEqual(port.requests, [])

    def test_exact_profile_age_boundary_is_inclusive(self):
        port = RecordingPort()
        outcome = WorkloadAdmissionController(port, clock=lambda: NOW, maximum_profile_age_ns=10).admit(request())
        self.assertEqual(outcome.state, AdmissionState.ADMITTED)
        self.assertEqual(len(port.requests), 1)

    def test_preparation_delay_expires_capacity_before_dispatch(self):
        port = RecordingPort()
        clock = iter((NOW, NOW + 101))
        outcome = WorkloadAdmissionController(port, clock=lambda: next(clock), maximum_observation_age_ns=100).admit(request())
        self.assertEqual(outcome.reason_codes, ("ADMISSION_INPUT_EXPIRED_DURING_PREPARATION",))
        self.assertFalse(port.requests)

    def test_preparation_delay_expires_profile_before_dispatch(self):
        port = RecordingPort()
        clock = iter((NOW, NOW + 1))
        outcome = WorkloadAdmissionController(port, clock=lambda: next(clock), maximum_profile_age_ns=10).admit(request())
        self.assertEqual(outcome.reason_codes, ("ADMISSION_INPUT_EXPIRED_DURING_PREPARATION",))
        self.assertFalse(port.requests)

    def test_clock_rollback_during_preparation_closes_dispatch(self):
        port = RecordingPort()
        clock = iter((NOW, NOW - 1))
        outcome = WorkloadAdmissionController(port, clock=lambda: next(clock)).admit(request())
        self.assertEqual(outcome.state, AdmissionState.STALE)
        self.assertFalse(port.requests)

    def test_unqualified_confidence_has_no_owner_effect(self):
        port = RecordingPort()
        controller = WorkloadAdmissionController(port, clock=lambda: NOW, minimum_confidence_milli=800)
        for confidence in (0, 799):
            with self.subTest(confidence=confidence):
                result = controller.admit(request(estimated=replace(estimate(), confidence_milli=confidence)))
                self.assertEqual(result.reason_codes, ("WORKLOAD_PROFILE_CONFIDENCE_INSUFFICIENT",))
        self.assertFalse(port.requests)

    def test_confidence_threshold_boundary_and_equal_generation_are_permitted(self):
        port = RecordingPort()
        result = WorkloadAdmissionController(port, clock=lambda: NOW, minimum_confidence_milli=900).admit(request())
        self.assertEqual(result, port.result)
        self.assertEqual((result.generation, port.requests[0].expected_generation), (7, 7))

    def test_unrepresentable_margin_is_uncertain_without_owner_call(self):
        port = RecordingPort()
        huge = replace(estimate(), requirements=vector(2**63 - 1), uncertainty_milli=1)
        result = WorkloadAdmissionController(port, clock=lambda: NOW).admit(request(estimated=huge))
        self.assertEqual(result.reason_codes, ("WORKLOAD_ESTIMATE_BOUND_EXCEEDED",))
        self.assertFalse(port.requests)

    def test_invalid_request_and_port_fail_before_dispatch(self):
        port = RecordingPort()
        with self.assertRaises(ContractError) as raised:
            WorkloadAdmissionController(port).admit(object())
        self.assertEqual(raised.exception.code, "RESOURCE_ADMISSION_REQUEST_REQUIRED")
        with self.assertRaises(ContractError) as raised:
            WorkloadAdmissionController(object())
        self.assertEqual(raised.exception.code, "RESOURCE_RESERVATION_PORT_REQUIRED")
        self.assertFalse(port.requests)

    def test_unhashable_unknown_estimate_state_returns_canonical_validation_error(self):
        with self.assertRaises(ContractError) as raised:
            replace(estimate(), state=[])
        self.assertEqual(raised.exception.code, "RESOURCE_WORKLOAD_ESTIMATE_INVALID")

    def test_invalid_policy_never_dispatches(self):
        for changes in ({"maximum_profile_age_ns": 0}, {"maximum_profile_age_ns": True},
                        {"minimum_confidence_milli": 0}, {"minimum_confidence_milli": 1001}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                WorkloadAdmissionController(RecordingPort(), **changes)

    def test_malformed_owner_result_has_no_automatic_retry(self):
        port = RecordingPort(result=object())
        with self.assertRaises(ContractError) as raised:
            WorkloadAdmissionController(port, clock=lambda: NOW).admit(request())
        self.assertEqual(raised.exception.code, "RESOURCE_RESERVATION_RESULT_REQUIRED")
        self.assertEqual(len(port.requests), 1)

    def test_corrupt_typed_owner_result_is_not_admission(self):
        result = ReservationResult(AdmissionState.ADMITTED, "reservation.one", 7, ())
        object.__setattr__(result, "generation", None)
        port = RecordingPort(result)
        with self.assertRaises(ContractError) as raised:
            WorkloadAdmissionController(port, clock=lambda: NOW).admit(request())
        self.assertEqual(raised.exception.code, "RESOURCE_BUDGET_GENERATION_INVALID")
        self.assertEqual(len(port.requests), 1)

    def test_owner_denial_passes_through_exactly(self):
        for state in AdmissionState:
            if state is AdmissionState.ADMITTED:
                continue
            result = ReservationResult(state, None, None, ("OWNER_EXACT_REASON",))
            with self.subTest(state=state):
                port = RecordingPort(result)
                self.assertIs(WorkloadAdmissionController(port, clock=lambda: NOW).admit(request()), result)

    def test_owner_errors_remain_uncertain_dispatch_without_retry(self):
        for error in (OSError("owner fault"), TimeoutError("dispatch may have committed"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                port = RecordingPort(error=error)
                with self.assertRaises(type(error)) as raised:
                    WorkloadAdmissionController(port, clock=lambda: NOW).admit(request())
                self.assertIs(raised.exception, error)
                self.assertEqual(len(port.requests), 1)

    def test_concurrent_request_identity_and_generation_remain_owner_inputs(self):
        port = RecordingPort(ReservationResult(AdmissionState.STALE, None, None, ("OWNER_CONFLICT",)))
        controller = WorkloadAdmissionController(port, clock=lambda: NOW)
        original = request()
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = tuple(pool.map(controller.admit, (original,) * 32))
        self.assertEqual(outcomes, (port.result,) * 32)
        self.assertEqual(len(port.requests), 32)
        self.assertEqual({(item.request_id, item.budget_id, item.expected_generation, item.observation_sequence)
                          for item in port.requests}, {("request.one", "budget.one", 7, 4)})
        self.assertEqual(original.budget, budget())


class MeasuredShapeTests(unittest.TestCase):
    def setUp(self):
        self.shape = WorkloadShape("model.chat", digest("model"), digest("configuration"), 2048, "TOKENS", 2)
        self.profile = profile(shape=self.shape, steady=3)
        self.estimator = WorkloadRequirementEstimator((self.profile,), clock=lambda: NOW, headroom_milli=100)

    def get_estimate(self, shape=None):
        return self.estimator.estimate(self.profile.workload_id, expected_profile_revision=self.profile.profile_revision,
                                       expected_workload_shape=shape)

    def test_exact_shape_separates_measured_peak_steady_and_uncertainty(self):
        item = self.get_estimate(self.shape)
        self.assertEqual((item.requirements, item.steady_requirements, item.conservative_requirements),
                         (vector(10), vector(3), vector(11)))
        self.assertEqual((item.workload_shape, item.confidence_milli), (self.shape, 900))

    def test_missing_shape_does_not_reuse_model_measurements(self):
        item = self.get_estimate()
        self.assertEqual((item.state, item.requirements, item.reason_code),
                         ("UNRESOLVED", None, "WORKLOAD_SHAPE_REQUIRED"))

    def test_new_model_input_configuration_or_concurrency_needs_measurement(self):
        changes = ({"model_revision": digest("other-model")}, {"configuration_digest": digest("new-configuration")},
                   {"input_units": 2049}, {"input_unit": "BYTES"}, {"concurrency": 3}, {"workload_class": "model.embedding"})
        for change in changes:
            with self.subTest(change=change):
                item = self.get_estimate(replace(self.shape, **change))
                self.assertEqual((item.requirements, item.reason_code), (None, "WORKLOAD_SHAPE_UNQUALIFIED"))

    def test_legacy_profile_cannot_qualify_a_declared_new_shape(self):
        legacy = profile()
        item = WorkloadRequirementEstimator((legacy,), clock=lambda: NOW).estimate(
            legacy.workload_id, expected_profile_revision=legacy.profile_revision, expected_workload_shape=self.shape)
        self.assertEqual(item.reason_code, "WORKLOAD_SHAPE_UNQUALIFIED")

    def test_missing_steady_measurements_remain_unknown(self):
        self.assertIsNone(estimate().steady_requirements)

    def test_steady_measurement_bounds_and_identity_are_validated(self):
        for changes in ({"steady_samples": (vector(11),)}, {"steady_samples": ()},
                        {"steady_samples": [vector(1)]}, {"workload_shape": object()}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(self.profile, **changes)

    def test_legacy_snapshot_commitment_bytes_are_preserved(self):
        item = profile()
        payload = {"workload_id": item.workload_id, "profile_id": item.profile_id,
                   "profile_revision": item.profile_revision, "source_digest": item.source_digest,
                   "observed_monotonic_ns": item.observed_monotonic_ns, "samples": [[10, 10, 10, 10]],
                   "confidence_milli": 900, "calibration_count": 0}
        expected = "sha256:" + hashlib.sha256(b"CETA:resource-profile-snapshot:v1\0" + canonical_bytes(payload)).hexdigest()
        self.assertEqual(item.snapshot_commitment, expected)
        self.assertNotEqual(item.snapshot_commitment, replace(item, workload_shape=self.shape).snapshot_commitment)

    def test_shape_or_steady_byte_drift_invalidates_profile_commitment(self):
        for changed in (replace(self.profile, workload_shape=replace(self.shape, concurrency=1)),
                        replace(self.profile, steady_samples=(vector(4),))):
            self.assertNotEqual(changed.snapshot_commitment, self.profile.snapshot_commitment)

    def test_calibration_preserves_exact_shape_and_measured_steady_lineage(self):
        preceding = self.get_estimate(self.shape)
        observation = ObservedWorkloadUsage(self.profile.workload_id, self.profile.profile_id,
                      self.profile.profile_revision, self.profile.source_digest, NOW - 1,
                      vector(12), self.shape, vector(4))
        outcome = self.estimator.calibrate(observation, preceding)
        self.assertEqual(outcome.comparison.exceeded_dimensions, ("CPU", "MEMORY", "STORAGE", "WALL_TIME"))
        self.assertEqual((outcome.profile.workload_shape, outcome.profile.steady_samples),
                         (self.shape, (vector(3), vector(4))))
        item = WorkloadRequirementEstimator((outcome.profile,), clock=lambda: NOW).estimate(
            self.profile.workload_id, expected_profile_revision=self.profile.profile_revision,
            expected_workload_shape=self.shape)
        self.assertEqual((item.requirements, item.steady_requirements), (vector(12), vector(4)))
        self.assertEqual(len(self.profile.samples), 1)

    def test_calibration_without_new_steady_observation_preserves_unknown(self):
        observation = ObservedWorkloadUsage(self.profile.workload_id, self.profile.profile_id,
                      self.profile.profile_revision, self.profile.source_digest, NOW - 1, vector(12), self.shape)
        outcome = self.estimator.calibrate(observation, self.get_estimate(self.shape))
        self.assertIsNone(outcome.profile.steady_samples)

    def test_calibration_rejects_cross_shape_measurement(self):
        observation = ObservedWorkloadUsage(self.profile.workload_id, self.profile.profile_id,
                      self.profile.profile_revision, self.profile.source_digest, NOW - 1, vector(12),
                      replace(self.shape, input_units=4096))
        with self.assertRaises(ContractError) as raised:
            self.estimator.calibrate(observation, self.get_estimate(self.shape))
        self.assertEqual(raised.exception.code, "RESOURCE_WORKLOAD_SHAPE_MISMATCH")

    def test_replayed_commitment_cannot_hide_changed_estimate_content(self):
        original = self.get_estimate(self.shape)
        observation = ObservedWorkloadUsage(self.profile.workload_id, self.profile.profile_id,
                      self.profile.profile_revision, self.profile.source_digest, NOW - 1, vector(12), self.shape)
        for change in ({"requirements": vector(9)}, {"steady_requirements": vector(2)},
                       {"uncertainty_milli": 0}, {"observed_monotonic_ns": NOW - 9}, {"confidence_milli": 1}):
            with self.subTest(change=change):
                result = self.estimator.calibrate(observation, replace(original, **change))
                self.assertEqual((result.state, result.profile, result.reason_code),
                                 ("UNAVAILABLE", None, "PRECEDING_ESTIMATE_UNAVAILABLE"))

    def test_unrepresentable_conservative_peak_is_not_a_precise_estimate(self):
        item = profile(peak=2**63 - 1)
        result = WorkloadRequirementEstimator((item,), clock=lambda: NOW, headroom_milli=1).estimate(
            item.workload_id, expected_profile_revision=item.profile_revision)
        self.assertEqual((result.state, result.requirements, result.reason_code),
                         ("UNRESOLVED", None, "ESTIMATE_BOUND_EXCEEDED"))

    def test_shape_bounds_and_boolean_numbers_are_rejected(self):
        for change in ({"input_units": True}, {"input_units": -1}, {"input_units": 2**63},
                       {"concurrency": True}, {"concurrency": 0}, {"concurrency": 257}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                replace(self.shape, **change)

    def test_calibration_counter_bound_is_explicit_without_profile_mutation(self):
        full = replace(self.profile, calibration_count=2**31 - 1)
        estimator = WorkloadRequirementEstimator((full,), clock=lambda: NOW, headroom_milli=100)
        preceding = estimator.estimate(full.workload_id, expected_profile_revision=full.profile_revision,
                                       expected_workload_shape=self.shape)
        observation = ObservedWorkloadUsage(full.workload_id, full.profile_id, full.profile_revision,
                                            full.source_digest, NOW - 1, vector(12), self.shape)
        with self.assertRaises(ContractError) as raised:
            estimator.calibrate(observation, preceding)
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_CALIBRATION_BOUND_EXCEEDED")
        self.assertEqual(full.calibration_count, 2**31 - 1)

    def test_concurrent_shape_estimation_preserves_one_input_snapshot(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            values = tuple(pool.map(lambda _: self.get_estimate(self.shape), range(32)))
        self.assertEqual(values, (values[0],) * 32)
        self.assertEqual(self.profile.samples, (vector(10),))


class BudgetProjectionTests(unittest.TestCase):
    def test_estimates_are_distinct_from_measured_reserved_and_control(self):
        original = budget()
        result = project_workload_budget(original, vector(60), expected_generation=7)
        self.assertEqual((result.limit, result.control_reserve, result.measured_use, result.reserved_use,
                          result.estimated_use, result.remaining),
                         (vector(100), vector(10), vector(10), vector(10), vector(60), vector(10)))
        self.assertEqual(original, budget())
        with self.assertRaises(FrozenInstanceError):
            result.estimated_use = ZERO

    def test_expected_generation_rejects_stale_projection_without_extra_capacity(self):
        result = project_workload_budget(budget(), vector(1), expected_generation=6)
        self.assertEqual((result.accepted, result.reason_codes, result.remaining),
                         (False, ("BUDGET_GENERATION_STALE",), None))

    def test_exact_remaining_capacity_fits_and_one_more_is_rejected(self):
        self.assertEqual(project_workload_budget(budget(), vector(70), expected_generation=7).remaining, ZERO)
        rejected = project_workload_budget(budget(), vector(71), expected_generation=7)
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.reason_codes, ("COMPUTE_BUDGET_EXHAUSTED", "MEMORY_BUDGET_EXHAUSTED",
                                                "STORAGE_BUDGET_EXHAUSTED", "EXECUTION_TIME_BUDGET_EXHAUSTED"))

    def test_projection_rejects_fabricated_remaining_or_measured_values(self):
        result = project_workload_budget(budget(), vector(60), expected_generation=7)
        for change in ({"remaining": vector(100)}, {"estimated_use": vector(80)},
                       {"observed_generation": 8}, {"measured_use": vector(100)}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                replace(result, **change)

    def test_generation_projection_is_pure_under_concurrent_reconstruction(self):
        original = budget()
        with ThreadPoolExecutor(max_workers=8) as pool:
            values = tuple(pool.map(lambda _: project_workload_budget(original, vector(70), expected_generation=7), range(32)))
        self.assertEqual(values, (values[0],) * 32)
        self.assertEqual(original.allocatable, vector(70))


class FifoBoundaryTests(unittest.TestCase):
    def test_duplicate_identity_is_rejected_even_if_profiles_differ(self):
        first = estimate()
        for second in (first, replace(first, source_digest=digest("other"))):
            with self.subTest(second=second.source_digest), self.assertRaises(ContractError) as raised:
                plan_concurrency((first, second), vector(100), control_reserve=ZERO)
            self.assertEqual(raised.exception.code, "RESOURCE_PLAN_DUPLICATE_WORKLOAD")

    def test_overflowing_candidate_sum_is_capacity_rejection(self):
        maximum = 2**63 - 1
        first, second = estimate("first", peak=maximum - 1), estimate("second", peak=2)
        self.assertEqual(plan_concurrency((first, second), vector(maximum), control_reserve=ZERO), (first,))

    def test_unrepresentable_margin_stops_fifo_without_exception(self):
        first = replace(estimate(), requirements=vector(2**63 - 1), uncertainty_milli=1)
        self.assertEqual(plan_concurrency((first,), vector(2**63 - 1), control_reserve=ZERO), ())

    def test_queue_is_bounded_before_planning(self):
        items = tuple(estimate(str(i), peak=0) for i in range(257))
        with self.assertRaises(ContractError) as raised:
            plan_concurrency(items, vector(100), control_reserve=ZERO)
        self.assertEqual(raised.exception.code, "RESOURCE_PLAN_INPUT_INVALID")

    def test_reserved_control_memory_cannot_be_used_by_background_prefix(self):
        first = estimate(peak=91)
        self.assertEqual(plan_concurrency((first,), vector(100), control_reserve=vector(10)), ())

    def test_capacity_only_result_rejects_fabricated_use_and_duplicate_selection(self):
        result = plan_concurrency_with_facts((estimate(),), vector(100), control_reserve=vector(10))
        for change in ({"used": vector(1)}, {"admitted": result.admitted * 2}, {"awaiting_owner_inputs": "unknown"}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                replace(result, **change)


class OwnerFactPlanningTests(unittest.TestCase):
    def setUp(self):
        self.previous = ClockSample("boot.one", 1, 2, NOW - 10, NOW - 10, 0, True)
        self.current = replace(self.previous, monotonic_ns=NOW, wall_time_ns=NOW)

    def facts(self, item, *, queued=1, priority=0, **changes):
        result = WorkloadPlanningFacts(item.workload_id, item.profile_snapshot_commitment, 3, queued,
                                        priority, True, (), False)
        return replace(result, **changes)

    def plan(self, items, facts=None, **changes):
        inputs = dict(expected_budget_generation=7, facts=facts or tuple(self.facts(item) for item in items),
                      expected_owner_generation=3, previous_clock=self.previous, current_clock=self.current)
        inputs.update(changes)
        return plan_budget_concurrency(items, budget(), **inputs)

    def test_budget_plan_conserves_every_distinct_quantity(self):
        first, second = estimate("first", peak=40), estimate("second", peak=30)
        result = self.plan((first, second))
        self.assertEqual((result.selected, result.estimated_use, result.remaining), ((first, second), vector(70), ZERO))
        self.assertEqual(result.budget, budget())
        self.assertEqual({item.state for item in result.decisions}, {"PROPOSED"})

    def test_independent_dimensions_cannot_borrow_storage_or_control_memory(self):
        item = replace(estimate(), requirements=ResourceVector(1, 10, 71, 1))
        result = self.plan((item,))
        self.assertEqual(result.decisions[0].reason_codes, ("WORKLOAD_CAPACITY_EXHAUSTED",))
        self.assertFalse(result.selected)
        self.assertEqual(result.remaining, vector(70))

    def test_empty_facts_and_excessive_queue_are_rejected_before_proposal(self):
        for items, facts in (((estimate(),), ()),
                             (tuple(estimate(str(i), peak=0) for i in range(257)), ())):
            with self.subTest(size=len(items)), self.assertRaises(ContractError):
                plan_budget_concurrency(items, budget(), expected_budget_generation=7, facts=facts,
                    expected_owner_generation=3, previous_clock=self.previous, current_clock=self.current)

    def test_oldest_workload_precedes_newer_high_priority(self):
        old, new = estimate("old", peak=60), estimate("new", peak=20)
        result = self.plan((new, old), (self.facts(new, queued=20, priority=1000), self.facts(old, queued=10, priority=-1000)))
        self.assertEqual(result.selected, (old,))
        self.assertEqual(result.decisions[-1].reason_codes, ("WORKLOAD_CAPACITY_EXHAUSTED",))

    def test_capacity_blocked_eligible_head_defers_smaller_newcomer(self):
        old, new = estimate("old", peak=71), estimate("new", peak=1)
        result = self.plan((new, old), (self.facts(new, queued=20), self.facts(old, queued=10)))
        self.assertFalse(result.selected)
        self.assertEqual(tuple(item.reason_codes for item in result.decisions),
                         (("WORKLOAD_CAPACITY_EXHAUSTED",), ("OLDER_WORKLOAD_AWAITS_CAPACITY",)))

    def test_equal_time_priority_deadline_identity_order_is_deterministic(self):
        a, b, c = estimate("a", peak=1), estimate("b", peak=1), estimate("c", peak=1)
        deadline = Deadline("boot.one", 1, 2, NOW - 1, NOW + 2_000_000, NOW - 1, NOW + 2_000_000)
        facts = (self.facts(a, priority=0), self.facts(b, priority=1), self.facts(c, priority=0, deadline=deadline))
        for perm in itertools.permutations((a, b, c)):
            result = self.plan(perm, tuple(reversed(facts)))
            self.assertEqual(result.selected, (b, c, a))

    def test_conflicting_file_key_defers_only_incompatible_workload(self):
        a, b, c = estimate("a"), estimate("b"), estimate("c")
        result = self.plan((a, b, c), (self.facts(a, queued=1, shared_file_keys=("file.one",)),
                      self.facts(b, queued=2, shared_file_keys=("file.one",)),
                      self.facts(c, queued=3, shared_file_keys=("file.two",))))
        self.assertEqual(result.selected, (a, c))
        self.assertEqual(result.decisions[1].reason_codes, ("SHARED_FILE_CONFLICT",))

    def test_unknown_or_false_authority_cannot_be_proposed(self):
        item = estimate()
        for readiness, code in ((None, "AWAITING_OWNER_AUTHORITY_READINESS_INPUT"), (False, "OWNER_AUTHORITY_NOT_READY")):
            with self.subTest(readiness=readiness):
                result = self.plan((item,), (self.facts(item, authority_ready=readiness),))
                self.assertFalse(result.selected)
                self.assertEqual(result.decisions[0].reason_codes, (code,))

    def test_unknown_file_conflicts_cannot_be_assumed_empty(self):
        item = estimate()
        result = self.plan((item,), (self.facts(item, shared_file_keys=None),))
        self.assertFalse(result.selected)
        self.assertEqual(result.decisions[0].reason_codes, ("AWAITING_OWNER_SHARED_FILE_CONFLICT_INPUT",))

    def test_cancelled_entry_remains_cancelled_after_capacity_becomes_available(self):
        item = estimate()
        original_facts = (self.facts(item, cancelled=True),)
        first = self.plan((item,), original_facts)
        larger = plan_budget_concurrency((item,), budget(limit=1000), expected_budget_generation=7,
                  facts=original_facts, expected_owner_generation=3, previous_clock=self.previous, current_clock=self.current)
        self.assertEqual((first.selected, larger.selected), ((), ()))
        self.assertEqual(larger.decisions[0].state, "CANCELLED")

    def test_stale_budget_generation_invalidates_plan(self):
        result = self.plan((estimate(),), expected_budget_generation=6)
        self.assertFalse(result.selected)
        self.assertEqual(result.decisions[0].reason_codes, ("BUDGET_GENERATION_STALE",))

    def test_mixed_or_stale_owner_generation_invalidates_entire_cut(self):
        a, b = estimate("a"), estimate("b")
        result = self.plan((a, b), (self.facts(a), self.facts(b, owner_generation=2)))
        self.assertFalse(result.selected)
        self.assertEqual({item.reason_codes for item in result.decisions}, {("PLANNING_OWNER_GENERATION_STALE",)})

    def test_changed_profile_snapshot_is_stale_without_mutating_other_candidates(self):
        a, b = estimate("a"), estimate("b")
        result = self.plan((a, b), (self.facts(a, profile_snapshot_commitment=digest("other")), self.facts(b)))
        self.assertEqual(result.selected, (b,))
        self.assertEqual(result.decisions[0].state, "STALE")

    def test_future_or_expired_profile_never_enters_current_proposal(self):
        for timestamp in (NOW + 1, NOW - 101):
            with self.subTest(timestamp=timestamp):
                item = replace(estimate(), observed_monotonic_ns=timestamp)
                result = self.plan((item,), maximum_profile_age_ns=100)
                self.assertFalse(result.selected)
                self.assertEqual(result.decisions[0].reason_codes, ("WORKLOAD_PROFILE_STALE",))

    def test_zero_confidence_is_not_known_admission_capacity(self):
        item = replace(estimate(), confidence_milli=0)
        result = self.plan((item,))
        self.assertFalse(result.selected)
        self.assertEqual(result.decisions[0].state, "UNRESOLVED")

    def test_unknown_estimate_remains_unresolved_despite_owner_ready_flag(self):
        item = WorkloadEstimate("workload.unknown", None, 1000, "unavailable", "UNRESOLVED", reason_code="PROFILE_UNKNOWN")
        facts = WorkloadPlanningFacts(item.workload_id, digest("unknown"), 3, 1, 0, True, (), False)
        result = self.plan((item,), (facts,))
        self.assertFalse(result.selected)
        self.assertEqual(result.decisions[0].state, "UNRESOLVED")

    def test_future_queue_time_is_stale(self):
        item = estimate()
        result = self.plan((item,), (self.facts(item, queued=NOW + 1),))
        self.assertEqual(result.decisions[0].reason_codes, ("PLANNING_QUEUE_TIME_IN_FUTURE",))

    def test_deadline_beyond_estimated_duration_is_required(self):
        item = estimate(peak=10)
        deadline = Deadline("boot.one", 1, 2, NOW - 1, NOW + 5_000_000, NOW - 1, NOW + 5_000_000)
        denied = self.plan((item,), (self.facts(item, deadline=deadline),))
        accepted = self.plan((item,), (self.facts(item, deadline=replace(deadline,
                                expires_monotonic_ns=NOW + 10_000_000, expires_wall_ns=NOW + 10_000_000)),))
        self.assertFalse(denied.selected)
        self.assertEqual(denied.decisions[0].reason_codes, ("DEADLINE_BUDGET_EXCEEDED",))
        self.assertEqual(accepted.selected, (item,))

    def test_expired_and_epoch_changed_deadlines_stay_denied(self):
        item = estimate()
        deadlines = (Deadline("boot.one", 1, 2, NOW - 10, NOW, NOW - 10, NOW),
                     Deadline("boot.other", 1, 2, NOW - 10, NOW + 1_000_000, NOW - 10, NOW + 1_000_000))
        for deadline in deadlines:
            with self.subTest(deadline=deadline.boot_id):
                result = self.plan((item,), (self.facts(item, deadline=deadline),))
                self.assertFalse(result.selected)
                self.assertEqual(result.decisions[0].state, "BLOCKED")

    def test_untrusted_or_rolled_back_time_invalidates_even_deadlineless_plan(self):
        for current in (replace(self.current, wall_trusted=False), replace(self.current, boot_id="other.boot"),
                        replace(self.current, resume_generation=3), replace(self.current, monotonic_ns=NOW - 11)):
            with self.subTest(current=current):
                result = self.plan((estimate(),), current_clock=current)
                self.assertFalse(result.selected)
                self.assertEqual(result.decisions[0].state, "STALE")

    def test_overflow_is_rejected_by_remaining_capacity_comparison(self):
        a, b = estimate("a", peak=2**63 - 2), estimate("b", peak=2)
        result = plan_budget_concurrency((a, b), budget(limit=2**63 - 1, control=0, measured=0, reserved=0),
                  expected_budget_generation=7, facts=(self.facts(a, queued=1), self.facts(b, queued=2)),
                  expected_owner_generation=3, previous_clock=self.previous, current_clock=self.current)
        self.assertEqual(result.selected, (a,))
        self.assertEqual(result.remaining, vector(1))

    def test_unrepresentable_margin_produces_unresolved_decision(self):
        item = replace(estimate(), requirements=vector(2**63 - 1), uncertainty_milli=1)
        result = self.plan((item,))
        self.assertFalse(result.selected)
        self.assertEqual(result.decisions[0].reason_codes, ("WORKLOAD_ESTIMATE_BOUND_EXCEEDED",))

    def test_membership_or_duplicate_input_is_rejected(self):
        a, b = estimate("a"), estimate("b")
        for items, facts in (((a, a), (self.facts(a), self.facts(a))),
                             ((a, b), (self.facts(a), self.facts(a))),
                             ((a,), (self.facts(b),))):
            with self.subTest(items=items), self.assertRaises(ContractError):
                self.plan(items, facts)

    def test_fact_bounds_do_not_allow_boolean_generation_or_unknown_enum(self):
        item = self.facts(estimate())
        for change in ({"owner_generation": True}, {"priority": True}, {"priority": 1001},
                       {"cancelled": None}, {"authority_ready": "yes"}, {"shared_file_keys": ("key",) * 2},
                       {"shared_file_keys": tuple("key." + str(i) for i in range(65))}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                replace(item, **change)

    def test_unknown_unhashable_decision_state_is_a_stable_validation_error(self):
        with self.assertRaises(ContractError) as raised:
            WorkloadPlanningDecision("workload.one", [], ("bad",))
        self.assertEqual(raised.exception.code, "RESOURCE_PLANNING_DECISION_INVALID")

    def test_result_cannot_claim_selection_without_conservation_and_decision(self):
        result = self.plan((estimate(),))
        for change in ({"estimated_use": ZERO}, {"remaining": vector(100)}, {"decisions": ()},
                       {"selected": result.selected * 2}, {"expected_budget_generation": 6}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                replace(result, **change)

    def test_reconstruction_and_concurrent_plan_are_deterministic_and_pure(self):
        items = (estimate("a", peak=30), estimate("b", peak=40), estimate("c", peak=1))
        facts = tuple(self.facts(item, queued=index) for index, item in enumerate(items))
        expected = self.plan(items, facts)
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = tuple(pool.map(lambda _: self.plan(tuple(reversed(items)), tuple(reversed(facts))), range(64)))
        self.assertEqual(outcomes, (expected,) * 64)
        self.assertEqual(self.plan(items, facts), expected)
        self.assertEqual(expected.budget, budget())
        self.assertEqual(tuple(item.requirements for item in items), (vector(30), vector(40), vector(1)))


if __name__ == "__main__":
    unittest.main()

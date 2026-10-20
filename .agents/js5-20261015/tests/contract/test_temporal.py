"""Injected clock fixtures test predicates, not OS clock trust or permit use."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError
from ceta.contracts.temporal import (
    ClockSample, Deadline, NS_PER_SECOND, issue_deadline, require_clock_progress,
    require_deadline_current, utc_nanoseconds,
)
from ceta.contracts.wire import MAX_INTEGER


class TemporalTests(unittest.TestCase):
    def setUp(self):
        self.start = ClockSample("boot:fixture:1", 4, 0, 100 * NS_PER_SECOND,
                                 utc_nanoseconds("2026-10-06T21:00:00Z"), 0, True)
        self.deadline = issue_deadline("2026-10-06T21:00:10Z", 20 * NS_PER_SECOND,
                                       self.start, self.start)

    def reject(self, code, fn, *args):
        with self.assertRaises(ContractError) as raised:
            fn(*args)
        self.assertEqual(raised.exception.code, code)

    def test_exact_nanoseconds_offsets_and_before_epoch(self):
        self.assertEqual(utc_nanoseconds("1970-01-01T00:00:00Z"), 0)
        self.assertEqual(utc_nanoseconds("1969-12-31T23:59:59.999999999Z"), -1)
        self.assertEqual(utc_nanoseconds("2026-10-06T21:00:00.123456789Z") - self.start.wall_time_ns, 123456789)
        for text in ("2026-10-06T23:00:00+02:00", "2026-10-06T19:00:00-02:00",
                     "2026-10-06T21:00:00+00:00"):
            self.assertEqual(utc_nanoseconds(text), self.start.wall_time_ns)
        self.assertEqual(utc_nanoseconds("2000-02-29T00:00:00Z"), 951782400 * NS_PER_SECOND)

    def test_reject_unknown_offset_leap_second_invalid_calendar_and_rounded_precision(self):
        self.reject("UNKNOWN_UTC_OFFSET", utc_nanoseconds, "2026-10-06T21:00:00-00:00")
        for text in ("2026-02-29T21:00:00Z", "2026-10-06T21:00:60Z", "0000-01-01T00:00:00Z",
                     "2026-10-06T21:00:00.1234567890Z", "2026-10-06T21:00:00+24:00",
                     "2026-10-06T21:00:00", "2026-10-06t21:00:00z", None, [], True):
            with self.subTest(value=text):
                self.reject("INVALID_DATE_TIME", utc_nanoseconds, text)
        self.reject("INVALID_TEMPORAL_INTEGER", utc_nanoseconds, "9999-12-31T23:59:59Z")

    def test_issue_is_bounded_by_wall_expiry_and_maximum_lifetime(self):
        self.assertEqual(self.deadline.expires_monotonic_ns, 110 * NS_PER_SECOND)
        capped = issue_deadline("2026-10-06T22:00:00Z", 2 * NS_PER_SECOND, self.start, self.start)
        self.assertEqual(capped.expires_monotonic_ns, 102 * NS_PER_SECOND)
        self.assertEqual(capped.expires_wall_ns, self.start.wall_time_ns + 2 * NS_PER_SECOND)

    def test_valid_until_exact_monotonic_or_wall_boundary(self):
        before = replace(self.start, monotonic_ns=self.deadline.expires_monotonic_ns - 1,
                         wall_time_ns=self.deadline.expires_wall_ns - 1)
        require_deadline_current(self.deadline, self.start, before)
        for current in (replace(before, monotonic_ns=self.deadline.expires_monotonic_ns),
                        replace(before, wall_time_ns=self.deadline.expires_wall_ns)):
            self.reject("DEADLINE_EXPIRED_OR_UNCERTAIN", require_deadline_current,
                        self.deadline, before, current)

    def test_uncertainty_shortens_issuance_and_rejects_ambiguous_expiry(self):
        uncertain = replace(self.start, uncertainty_ns=2 * NS_PER_SECOND)
        deadline = issue_deadline("2026-10-06T21:00:10Z", 20 * NS_PER_SECOND, uncertain, uncertain)
        self.assertEqual(deadline.expires_monotonic_ns, 108 * NS_PER_SECOND)
        current = replace(uncertain, wall_time_ns=self.start.wall_time_ns + 9 * NS_PER_SECOND)
        self.reject("DEADLINE_EXPIRED_OR_UNCERTAIN", require_deadline_current, deadline, uncertain, current)
        self.reject("DEADLINE_EXPIRED_OR_UNCERTAIN", issue_deadline,
                    "2026-10-06T21:00:02Z", 20 * NS_PER_SECOND, uncertain, uncertain)

    def test_clock_rollback_cannot_extend_deadline(self):
        rolled_back = replace(self.start, monotonic_ns=101 * NS_PER_SECOND,
                              wall_time_ns=self.start.wall_time_ns - NS_PER_SECOND)
        self.reject("WALL_CLOCK_ROLLBACK", require_deadline_current, self.deadline, self.start, rolled_back)
        self.reject("WALL_CLOCK_ROLLBACK", issue_deadline,
                    "2026-10-06T21:00:10Z", 20 * NS_PER_SECOND, self.start, rolled_back)

    def test_rollback_within_uncertainty_still_cannot_extend_monotonic_limit(self):
        start = replace(self.start, uncertainty_ns=NS_PER_SECOND)
        deadline = issue_deadline("2026-10-06T21:00:10Z", 20 * NS_PER_SECOND, start, start)
        now = replace(start, wall_time_ns=start.wall_time_ns - NS_PER_SECOND,
                      monotonic_ns=deadline.expires_monotonic_ns)
        self.reject("DEADLINE_EXPIRED_OR_UNCERTAIN", require_deadline_current, deadline, start, now)

    def test_restart_epoch_change_and_resume_invalidate_existing_deadline(self):
        for field, value, code in (("boot_id", "boot:fixture:2", "BOOT_CHANGED"),
                                   ("durable_epoch", 5, "TIME_EPOCH_CHANGED"),
                                   ("resume_generation", 1, "RESUME_GENERATION_CHANGED")):
            current = replace(self.start, **{field: value})
            with self.subTest(field=field):
                self.reject(code, require_deadline_current, self.deadline, current, current)
                self.reject(code, require_clock_progress, self.start, current)

    def test_missing_trusted_time_denies_issue_and_validation(self):
        unavailable = replace(self.start, wall_trusted=False)
        self.reject("TRUSTED_TIME_UNAVAILABLE", issue_deadline,
                    "2026-10-06T21:00:10Z", NS_PER_SECOND, self.start, unavailable)
        self.reject("TRUSTED_TIME_UNAVAILABLE", require_deadline_current,
                    self.deadline, unavailable, self.start)

    def test_prior_sample_and_issued_sample_reject_monotonic_rollback(self):
        earlier = replace(self.start, monotonic_ns=self.start.monotonic_ns - 1)
        self.reject("MONOTONIC_ROLLBACK", require_clock_progress, self.start, earlier)
        self.reject("MONOTONIC_ROLLBACK", require_deadline_current, self.deadline, earlier, earlier)

    def test_deadline_remembers_wall_anchor_even_if_previous_sample_is_replaced(self):
        earlier = replace(self.start, wall_time_ns=self.start.wall_time_ns - NS_PER_SECOND)
        self.reject("WALL_CLOCK_ROLLBACK", require_deadline_current, self.deadline, earlier, earlier)

    def test_exact_types_bounds_zero_lifetime_and_overflow(self):
        for field in ("durable_epoch", "resume_generation", "monotonic_ns", "wall_time_ns", "uncertainty_ns"):
            for value in (True, 1.5, None, MAX_INTEGER + 1):
                with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                    replace(self.start, **{field: value})
        for value in (True, 0, -1, 1.5, None):
            with self.subTest(lifetime=value), self.assertRaises(ContractError):
                issue_deadline("2026-10-06T21:00:10Z", value, self.start, self.start)
        overflow = replace(self.start, monotonic_ns=MAX_INTEGER)
        self.reject("INVALID_TEMPORAL_INTEGER", issue_deadline,
                    "2026-10-06T21:00:10Z", NS_PER_SECOND, overflow, overflow)
        with self.assertRaises(ContractError):
            replace(self.start, wall_time_ns=MAX_INTEGER, uncertainty_ns=1)
        with self.assertRaises(ContractError):
            replace(self.start, wall_trusted="true")

    def test_expired_preparation_is_never_reissued(self):
        for expiry in ("2026-10-06T20:59:59Z", "2026-10-06T21:00:00Z"):
            self.reject("DEADLINE_EXPIRED_OR_UNCERTAIN", issue_deadline,
                        expiry, NS_PER_SECOND, self.start, self.start)

    def test_clock_and_deadline_are_immutable_and_malformed_objects_rejected(self):
        with self.assertRaises(FrozenInstanceError):
            self.start.wall_trusted = True
        with self.assertRaises(FrozenInstanceError):
            self.deadline.expires_monotonic_ns += NS_PER_SECOND
        self.reject("CLOCK_SAMPLE_REQUIRED", require_clock_progress, {}, self.start)
        self.reject("DEADLINE_REQUIRED", require_deadline_current, {}, self.start, self.start)
        with self.assertRaises(ContractError):
            replace(self.deadline, expires_monotonic_ns=self.deadline.issued_monotonic_ns)
        with self.assertRaises(ContractError):
            Deadline([], 0, 0, 1, 2, 1, 2)


if __name__ == "__main__":
    unittest.main()

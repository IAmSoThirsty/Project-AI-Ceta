
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from ceta.governance.rules import (MAX_APPROVALS, GovernanceError, Registry, approve_transition)  # noqa: E402

FIX = ROOT / 'tests' / 'fixtures' / 'governance'
RAW = (FIX / 'test-rule-set.json').read_bytes()
PIN = (FIX / 'test-rule-set.sha256').read_text(encoding='ascii').strip()
RULE_SET_DIGEST = hashlib.sha256(RAW).hexdigest()
DIGEST = hashlib.sha256(b'transition-proposal').hexdigest()
OTHER = hashlib.sha256(b'other-proposal').hexdigest()
ELIGIBLE = frozenset({'p1', 'p2'})

def ok(approval):
    return True

def ap(pid, digest=DIGEST):
    return {'principal_id': pid, 'proposal_digest': digest}

def run(approvals, eligible=ELIGIBLE, threshold=2, now=5, window=(0, 10), verifier=ok, digest=DIGEST):
    return approve_transition(digest, approvals, eligible, threshold, now, window[0], window[1], verifier=verifier)

class QuorumPositiveTests(unittest.TestCase):
    def test_positive_two_distinct_eligible_principals_meet_threshold(self):
        r = run([ap('p1'), ap('p2')])
        self.assertTrue(r.approved)
        self.assertEqual(r.reasons[0], 'quorum_met:2/2')

class QuorumBoundaryTests(unittest.TestCase):
    def test_boundary_one_short_of_threshold_not_approved(self):
        r = run([ap('p1')])
        self.assertFalse(r.approved)
        self.assertEqual(r.reasons[0], 'quorum_not_met:1/2')

    def test_boundary_threshold_one_single_approver_approved(self):
        self.assertTrue(run([ap('p1')], threshold=1).approved)

    def test_boundary_threshold_zero_rejected(self):
        with self.assertRaises(GovernanceError) as ctx:
            run([ap('p1')], threshold=0)
        self.assertEqual(ctx.exception.code, 'malformed')

    def test_boundary_validity_start_inclusive(self):
        self.assertTrue(run([ap('p1'), ap('p2')], now=0).approved)

    def test_boundary_validity_end_inclusive(self):
        self.assertTrue(run([ap('p1'), ap('p2')], now=10).approved)

    def test_boundary_after_validity_end_refused(self):
        r = run([ap('p1'), ap('p2')], now=11)
        self.assertFalse(r.approved)
        self.assertEqual(r.reasons, ('outside_validity',))

    def test_boundary_before_validity_start_refused(self):
        r = run([ap('p1'), ap('p2')], now=-1)
        self.assertFalse(r.approved)
        self.assertEqual(r.reasons, ('outside_validity',))

    def test_boundary_approval_list_bound_enforced(self):
        with self.assertRaises(GovernanceError) as ctx:
            run([ap('p1')] * (MAX_APPROVALS + 1))
        self.assertEqual(ctx.exception.code, 'malformed')

class QuorumNegativeTests(unittest.TestCase):
    def test_negative_duplicate_principal_counts_once(self):
        r = run([ap('p1'), ap('p1')])
        self.assertFalse(r.approved)
        self.assertEqual(r.reasons[0], 'quorum_not_met:1/2')

    def test_negative_ineligible_principal_not_counted(self):
        r = run([ap('p1'), ap('mallory')])
        self.assertFalse(r.approved)
        self.assertIn('ineligible_principal', r.reasons)

    def test_negative_wrong_proposal_not_counted(self):
        r = run([ap('p1'), ap('p2', OTHER)])
        self.assertFalse(r.approved)
        self.assertIn('wrong_proposal:p2', r.reasons)

    def test_negative_failed_signature_not_counted(self):
        r = run([ap('p1'), ap('p2')], verifier=lambda a: a['principal_id'] != 'p2')
        self.assertFalse(r.approved)
        self.assertIn('bad_signature:p2', r.reasons)

    def test_negative_verifier_exception_not_counted(self):
        def broken(approval):
            raise RuntimeError('verifier down')
        r = run([ap('p1'), ap('p2')], verifier=broken)
        self.assertFalse(r.approved)

    def test_negative_no_verifier_blocks_as_unpinned(self):
        r = run([ap('p1'), ap('p2')], verifier=None)
        self.assertFalse(r.approved)
        self.assertEqual(r.reasons, ('signature_profile_unpinned',))

    def test_negative_non_object_approval_ignored(self):
        r = run(['junk', ap('p1'), ap('p2')])
        self.assertTrue(r.approved)
        self.assertIn('ineligible_principal', r.reasons)

    def test_negative_eligible_must_be_set(self):
        with self.assertRaises(GovernanceError) as ctx:
            approve_transition(DIGEST, [], ['p1'], 1, 0, 0, 10, verifier=ok)
        self.assertEqual(ctx.exception.code, 'malformed')

    def test_negative_malformed_digest_rejected(self):
        with self.assertRaises(GovernanceError) as ctx:
            approve_transition('xyz', [], set(), 1, 0, 0, 10, verifier=ok)
        self.assertEqual(ctx.exception.code, 'malformed')

class QuorumRecoveryTests(unittest.TestCase):
    def test_recovery_replayed_approvals_do_not_double_count(self):
        self.assertFalse(run([ap('p1'), ap('p1')]).approved)
        self.assertTrue(run([ap('p1'), ap('p1'), ap('p2')]).approved)

    def test_recovery_expired_window_not_revived_by_retry(self):
        approvals = [ap('p1'), ap('p2')]
        self.assertTrue(run(approvals, now=5).approved)
        self.assertFalse(run(approvals, now=11).approved)

    def test_recovery_expired_approval_cannot_activate_rule_set(self):
        approvals = [{'principal_id': p, 'proposal_digest': RULE_SET_DIGEST} for p in ('p1', 'p2')]
        expired = approve_transition(RULE_SET_DIGEST, approvals, ELIGIBLE, 2, 11, 0, 10, verifier=ok)
        reg = Registry(now=lambda: 5)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(RAW, PIN, expired)
        self.assertEqual(ctx.exception.code, 'unapproved_transition')
        self.assertIsNone(reg.active())

if __name__ == '__main__':
    unittest.main()

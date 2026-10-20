
# Hostile-review regressions for Subsystem 01: forged approvals and alias double counting.
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from ceta.governance.rules import (GovernanceError, Registry, TransitionApproval, approve_transition)  # noqa: E402

FIX = ROOT / 'tests' / 'fixtures' / 'governance'
RAW = (FIX / 'test-rule-set.json').read_bytes()
PIN = (FIX / 'test-rule-set.sha256').read_text(encoding='ascii').strip()
DIGEST = hashlib.sha256(RAW).hexdigest()
ELIGIBLE = frozenset({'p1', 'p2'})



def ok(approval):
    return True



def ap(pid, digest=DIGEST):
    return {'principal_id': pid, 'proposal_digest': digest}



class ForgedApprovalTests(unittest.TestCase):
    def test_negative_directly_constructed_approval_refused(self):
        forged = TransitionApproval(DIGEST, True, (), 0, 10, nonce='x')
        reg = Registry(now=lambda: 5)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(RAW, PIN, forged)
        self.assertEqual(ctx.exception.code, 'unapproved_transition')
        self.assertIsNone(reg.active())

    def test_negative_forged_seal_refused(self):
        forged = TransitionApproval(DIGEST, True, (), 0, 10, nonce='x', seal='0'*64)
        reg = Registry(now=lambda: 5)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(RAW, PIN, forged)
        self.assertEqual(ctx.exception.code, 'unapproved_transition')
        self.assertIsNone(reg.active())

    def test_positive_issued_approval_accepted(self):
        issued = approve_transition(DIGEST, [ap('p1'), ap('p2')], ELIGIBLE, 2, 5, 0, 10, verifier=ok)
        reg = Registry(now=lambda: 5)
        reg.activate(RAW, PIN, issued)
        self.assertEqual(reg.active().version, 1)



class AliasQuorumTests(unittest.TestCase):
    ALIASES = {'alice': 'p1', 'p1': 'p1'}

    def test_regression_two_aliases_of_one_principal_count_once(self):
        r = approve_transition(DIGEST, [ap('alice'), ap('p1')], ELIGIBLE, 2, 5, 0, 10, verifier=ok, aliases=self.ALIASES)
        self.assertFalse(r.approved)
        self.assertEqual(r.reasons[0], 'quorum_not_met:1/2')
        self.assertIn('duplicate_principal:p1', r.reasons)

    def test_positive_alias_resolves_to_second_distinct_principal(self):
        r = approve_transition(DIGEST, [ap('alice'), ap('p2')], ELIGIBLE, 2, 5, 0, 10, verifier=ok, aliases=self.ALIASES)
        self.assertTrue(r.approved)

    def test_negative_unknown_alias_is_ineligible(self):
        r = approve_transition(DIGEST, [ap('mallory'), ap('p2')], ELIGIBLE, 2, 5, 0, 10, verifier=ok, aliases=self.ALIASES)
        self.assertFalse(r.approved)
        self.assertIn('ineligible_principal', r.reasons)

    def test_negative_malformed_alias_map_rejected(self):
        with self.assertRaises(GovernanceError) as ctx:
            approve_transition(DIGEST, [], ELIGIBLE, 2, 5, 0, 10, verifier=ok, aliases=['x'])
        self.assertEqual(ctx.exception.code, 'malformed')



if __name__ == '__main__':
    unittest.main()

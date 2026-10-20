
# Regression tests for Subsystem 01 remediation: unmet rules are never dropped, False and zero facts are judged correctly, approvals have a validity window and are single-use.
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from ceta.governance.rules import (ALLOW, DENY, GovernanceError, Registry, approve_transition, evaluate, load_rule_set)  # noqa: E402



def raw_of(rules, version=1):
    doc = {'constitution_id': 'TEST-FIXTURE-ONLY', 'version': version, 'rules': rules}
    return (json.dumps(doc, sort_keys=True) + chr(10)).encode('utf-8')



def ok(approval):
    return True



class UnmetRuleRegressionTests(unittest.TestCase):
    def test_regression_unconditional_allow_plus_unmet_deny_is_not_allow(self):
        raw = raw_of([
            {'id': 'R-A', 'action': 'read', 'effect': 'allow', 'precedence': 1},
            {'id': 'R-D', 'action': 'read', 'effect': 'deny', 'precedence': 5, 'requires': ['subject_id']},
        ])
        rs = load_rule_set(raw, hashlib.sha256(raw).hexdigest())
        decision, reasons = evaluate(rs, 'read')
        self.assertNotEqual(decision, ALLOW)
        self.assertEqual(decision, DENY)
        self.assertIn('missing_fact:R-D:subject_id', reasons)

    def test_positive_permitted_read_allowed_when_facts_present(self):
        raw = raw_of([
            {'id': 'R-A', 'action': 'read', 'effect': 'allow', 'precedence': 1},
            {'id': 'R-R', 'action': 'read', 'effect': 'allow', 'precedence': 1, 'requires': ['subject_id']},
        ])
        rs = load_rule_set(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(evaluate(rs, 'read', {'subject_id': 'u1'})[0], ALLOW)
        self.assertEqual(evaluate(rs, 'read')[0], DENY)

    def test_negative_false_fact_treated_as_absent(self):
        raw = raw_of([{'id': 'R-R', 'action': 'read', 'effect': 'allow', 'precedence': 1, 'requires': ['subject_id']}])
        rs = load_rule_set(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(evaluate(rs, 'read', {'subject_id': False})[0], DENY)

    def test_boundary_zero_fact_is_present(self):
        raw = raw_of([{'id': 'R-R', 'action': 'read', 'effect': 'allow', 'precedence': 1, 'requires': ['subject_id']}])
        rs = load_rule_set(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(evaluate(rs, 'read', {'subject_id': 0})[0], ALLOW)



class ApprovalWindowReplayTests(unittest.TestCase):
    RAW = raw_of([{'id': 'R-A', 'action': 'read', 'effect': 'allow', 'precedence': 1}])
    PIN = hashlib.sha256(RAW).hexdigest()
    RAW2 = raw_of([{'id': 'R-A', 'action': 'read', 'effect': 'allow', 'precedence': 1}], version=2)
    PIN2 = hashlib.sha256(RAW2).hexdigest()

    def approval(self, digest, now=5, window=(0, 10)):
        return approve_transition(digest, [{'principal_id': 'p1', 'proposal_digest': digest}], frozenset({'p1'}), 1, now, window[0], window[1], verifier=ok)

    def test_positive_activation_inside_window_consumes_approval(self):
        reg = Registry(now=lambda: 5)
        ap = self.approval(self.PIN)
        reg.activate(self.RAW, self.PIN, ap)
        self.assertEqual(reg.active().version, 1)
        self.assertTrue(ap.consumed)

    def test_boundary_window_start_and_end_inclusive(self):
        for t in (0, 10):
            reg = Registry(now=lambda t=t: t)
            reg.activate(self.RAW, self.PIN, self.approval(self.PIN))
            self.assertIsNotNone(reg.active())

    def test_negative_approval_used_after_window_is_refused(self):
        reg = Registry(now=lambda: 11)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(self.RAW, self.PIN, self.approval(self.PIN))
        self.assertEqual(ctx.exception.code, 'outside_validity')
        self.assertIsNone(reg.active())

    def test_negative_approval_used_before_window_is_refused(self):
        reg = Registry(now=lambda: -1)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(self.RAW, self.PIN, self.approval(self.PIN))
        self.assertEqual(ctx.exception.code, 'outside_validity')

    def test_negative_second_use_of_same_approval_is_refused(self):
        reg = Registry(now=lambda: 5)
        ap = self.approval(self.PIN)
        reg.activate(self.RAW, self.PIN, ap)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(self.RAW, self.PIN, ap)
        self.assertEqual(ctx.exception.code, 'approval_replayed')

    def test_recovery_window_refusal_keeps_current_revision(self):
        clock = {'t': 5}
        reg = Registry(now=lambda: clock['t'])
        reg.activate(self.RAW, self.PIN, self.approval(self.PIN))
        clock['t'] = 11
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(self.RAW2, self.PIN2, self.approval(self.PIN2))
        self.assertEqual(ctx.exception.code, 'outside_validity')
        self.assertEqual(reg.active().version, 1)
        self.assertEqual(reg.last_refusal, 'outside_validity')



if __name__ == '__main__':
    unittest.main()

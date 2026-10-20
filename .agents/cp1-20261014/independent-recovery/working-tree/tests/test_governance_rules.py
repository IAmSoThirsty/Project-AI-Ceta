# Subsystem 01 rule loader and evaluator tests (CETA-01.01.03, CETA-01.02.02). Positive, negative, boundary, recovery.
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from ceta.governance.rules import (ALLOW, DENY, HUMAN, MAX_BYTES, GovernanceError, Registry, approve_transition, evaluate, load_rule_set)  # noqa: E402

FIX = ROOT / 'tests' / 'fixtures' / 'governance'
RAW = (FIX / 'test-rule-set.json').read_bytes()
PIN = (FIX / 'test-rule-set.sha256').read_text(encoding='ascii').strip()
DIGEST = hashlib.sha256(RAW).hexdigest()


def make_raw(version=1, extra_rule=None):
    doc = json.loads(RAW.decode('utf-8'))
    doc['version'] = version
    if extra_rule is not None:
        doc['rules'].append(extra_rule)
    return (json.dumps(doc, indent=2, sort_keys=True) + chr(10)).encode('utf-8')


def pin_of(raw):
    return hashlib.sha256(raw).hexdigest()


def approval_for(digest, principals=('p1',), threshold=1, now=5, window=(0, 10), verifier=lambda a: True):
    approvals = [{'principal_id': p, 'proposal_digest': digest} for p in principals]
    return approve_transition(digest, approvals, set(principals), threshold, now, window[0], window[1], verifier=verifier)


class PositiveTests(unittest.TestCase):
    def test_positive_fixture_loads_with_pin(self):
        rs = load_rule_set(RAW, PIN)
        self.assertEqual(rs.version, 1)
        self.assertEqual(rs.digest, DIGEST)
        self.assertEqual(len(rs.rules), 6)

    def test_positive_permitted_read_is_allowed(self):
        rs = load_rule_set(RAW, PIN)
        decision, reasons = evaluate(rs, 'read', {'subject_id': 'u1'})
        self.assertEqual(decision, ALLOW)
        self.assertEqual(reasons, ('R-READ-1',))

    def test_positive_export_without_facts_allowed(self):
        rs = load_rule_set(RAW, PIN)
        self.assertEqual(evaluate(rs, 'export')[0], ALLOW)

    def test_positive_higher_precedence_deny_wins(self):
        rs = load_rule_set(RAW, PIN)
        decision, reasons = evaluate(rs, 'admin')
        self.assertEqual(decision, DENY)
        self.assertEqual(reasons, ('R-ADMIN-DENY',))


class NegativeTests(unittest.TestCase):
    def test_negative_missing_identity_fact_is_not_truthy_default(self):
        rs = load_rule_set(RAW, PIN)
        decision, reasons = evaluate(rs, 'read')
        self.assertEqual(decision, DENY)
        self.assertIn('missing_fact:R-READ-1:subject_id', reasons)

    def test_negative_empty_string_fact_treated_as_missing(self):
        rs = load_rule_set(RAW, PIN)
        self.assertEqual(evaluate(rs, 'read', {'subject_id': ''})[0], DENY)

    def test_negative_conflicting_top_precedence_requires_human(self):
        rs = load_rule_set(RAW, PIN)
        decision, reasons = evaluate(rs, 'write', {'subject_id': 'u1'})
        self.assertEqual(decision, HUMAN)
        self.assertIn('conflict:R-WRITE-ALLOW', reasons)
        self.assertIn('conflict:R-WRITE-DENY', reasons)

    def test_negative_no_active_rule_set_denies_everything(self):
        self.assertEqual(evaluate(None, 'read', {'subject_id': 'u1'}), (DENY, ('no_active_rule_set',)))

    def test_negative_unknown_action_denied(self):
        rs = load_rule_set(RAW, PIN)
        self.assertEqual(evaluate(rs, 'delete_everything'), (DENY, ('no_matching_rule',)))

    def test_negative_non_object_facts_rejected(self):
        rs = load_rule_set(RAW, PIN)
        with self.assertRaises(GovernanceError) as ctx:
            evaluate(rs, 'read', ['subject_id'])
        self.assertEqual(ctx.exception.code, 'malformed')

class BoundaryTests(unittest.TestCase):
    def test_boundary_empty_bytes_rejected(self):
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(b'', PIN)
        self.assertEqual(ctx.exception.code, 'bounds')

    def test_boundary_one_byte_over_max_rejected(self):
        big = bytes([32]) * (MAX_BYTES + 1)
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(big, pin_of(big))
        self.assertEqual(ctx.exception.code, 'bounds')

    def test_boundary_pin_must_be_64_ascii_chars(self):
        for bad in ('', 'abc', PIN[:-1], PIN + '0'):
            with self.assertRaises(GovernanceError) as ctx:
                load_rule_set(RAW, bad)
            self.assertEqual(ctx.exception.code, 'unpinned')

    def test_boundary_uppercase_pin_accepted(self):
        self.assertEqual(load_rule_set(RAW, PIN.upper()).digest, DIGEST)

    def test_boundary_duplicate_rule_id_rejected(self):
        raw = make_raw(extra_rule={'id': 'R-READ-1', 'action': 'read', 'effect': 'deny', 'precedence': 9})
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(raw, pin_of(raw))
        self.assertEqual(ctx.exception.code, 'duplicate_rule')

    def test_negative_unknown_effect_rejected(self):
        raw = make_raw(extra_rule={'id': 'R-X', 'action': 'read', 'effect': 'maybe', 'precedence': 1})
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(raw, pin_of(raw))
        self.assertEqual(ctx.exception.code, 'malformed')

    def test_negative_non_object_root_rejected(self):
        raw = b'[1,2,3]'
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(raw, pin_of(raw))
        self.assertEqual(ctx.exception.code, 'malformed')

    def test_negative_non_utf8_rejected(self):
        raw = bytes([255, 254, 0])
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(raw, pin_of(raw))
        self.assertEqual(ctx.exception.code, 'malformed')

    def test_negative_empty_rule_list_rejected(self):
        raw = (json.dumps({'constitution_id': 'X', 'version': 1, 'rules': []}) + chr(10)).encode('utf-8')
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(raw, pin_of(raw))
        self.assertEqual(ctx.exception.code, 'malformed')

    def test_boundary_version_zero_rejected(self):
        raw = make_raw(version=0)
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(raw, pin_of(raw))
        self.assertEqual(ctx.exception.code, 'malformed')

class RecoveryTests(unittest.TestCase):
    def test_recovery_tampered_bytes_fail_pin(self):
        tampered = RAW.replace(b'R-READ-1', b'R-READ-2')
        with self.assertRaises(GovernanceError) as ctx:
            load_rule_set(tampered, PIN)
        self.assertEqual(ctx.exception.code, 'digest_mismatch')

    def test_recovery_corrupted_reload_clears_active_set_no_fallback(self):
        reg = Registry(now=lambda: 5)
        reg.activate(RAW, PIN, approval_for(DIGEST))
        self.assertIsNotNone(reg.active())
        tampered = RAW.replace(b'R-READ-1', b'R-READ-2')
        with self.assertRaises(GovernanceError):
            reg.activate(tampered, PIN, approval_for(DIGEST))
        self.assertIsNone(reg.active())
        self.assertEqual(evaluate(reg.active(), 'read', {'subject_id': 'u'}), (DENY, ('no_active_rule_set',)))

    def test_recovery_rollback_refused_keeps_current_revision(self):
        reg = Registry(now=lambda: 5)
        raw2 = make_raw(version=2)
        reg.activate(raw2, pin_of(raw2), approval_for(pin_of(raw2)))
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(RAW, PIN, approval_for(DIGEST))
        self.assertEqual(ctx.exception.code, 'version_rollback')
        self.assertEqual(reg.active().version, 2)
        self.assertEqual(reg.last_refusal, 'version_rollback')

    def test_recovery_same_version_different_content_is_conflict(self):
        reg = Registry(now=lambda: 5)
        reg.activate(RAW, PIN, approval_for(DIGEST))
        other = make_raw(version=1, extra_rule={'id': 'R-EXTRA', 'action': 'export', 'effect': 'deny', 'precedence': 2})
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(other, pin_of(other), approval_for(pin_of(other)))
        self.assertEqual(ctx.exception.code, 'version_conflict')
        self.assertEqual(reg.active().digest, DIGEST)

    def test_recovery_reactivating_same_revision_is_idempotent(self):
        reg = Registry(now=lambda: 5)
        first = reg.activate(RAW, PIN, approval_for(DIGEST))
        again = reg.activate(RAW, PIN, approval_for(DIGEST))
        self.assertIs(first, again)
        self.assertEqual(len(reg.history), 1)

    def test_recovery_unapproved_activation_refused(self):
        reg = Registry(now=lambda: 5)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(RAW, PIN, approval_for(DIGEST, verifier=None))
        self.assertEqual(ctx.exception.code, 'unapproved_transition')
        self.assertIsNone(reg.active())

    def test_recovery_approval_bound_to_other_digest_refused(self):
        reg = Registry(now=lambda: 5)
        raw2 = make_raw(version=2)
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(raw2, pin_of(raw2), approval_for(DIGEST))
        self.assertEqual(ctx.exception.code, 'unapproved_transition')

if __name__ == '__main__':
    unittest.main()

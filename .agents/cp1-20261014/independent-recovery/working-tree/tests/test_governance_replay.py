# Hostile-review H-14 regression for Subsystem 01: an old approved packet re-run after its revision was superseded.
import hashlib, json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from ceta.governance.rules import GovernanceError, Registry, approve_transition
FIX = ROOT / 'tests' / 'fixtures' / 'governance'
RAW = (FIX / 'test-rule-set.json').read_bytes()
PIN = (FIX / 'test-rule-set.sha256').read_text(encoding='ascii').strip()
DIGEST = hashlib.sha256(RAW).hexdigest()
ELIGIBLE = frozenset({'p1', 'p2'})
def ok(approval):
    return True
def approve(digest, start=0, end=10):
    packet = [{'principal_id': p, 'proposal_digest': digest} for p in ('p1', 'p2')]
    return approve_transition(digest, packet, ELIGIBLE, 2, 5, start, end, verifier=ok)
def make_v2():
    obj = json.loads(RAW.decode('utf-8'))
    obj['version'] = 2
    raw = json.dumps(obj, sort_keys=True).encode('utf-8')
    return raw, hashlib.sha256(raw).hexdigest()
class OldPacketReplayTests(unittest.TestCase):
    def setUp(self):
        self.raw2, self.digest2 = make_v2()
    def test_regression_old_packet_rerun_after_supersede_is_refused(self):
        reg = Registry(now=lambda: 5)
        reg.activate(RAW, PIN, approve(DIGEST))
        reg.activate(self.raw2, self.digest2, approve(self.digest2))
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(RAW, PIN, approve(DIGEST))
        self.assertEqual(ctx.exception.code, 'approval_replayed')
        self.assertEqual(reg.active().version, 2)
        self.assertEqual(reg.last_refusal, 'approval_replayed')
    def test_negative_old_packet_widened_window_refused_as_rollback(self):
        reg = Registry(now=lambda: 5)
        reg.activate(RAW, PIN, approve(DIGEST))
        reg.activate(self.raw2, self.digest2, approve(self.digest2))
        with self.assertRaises(GovernanceError) as ctx:
            reg.activate(RAW, PIN, approve(DIGEST, 0, 20))
        self.assertEqual(ctx.exception.code, 'version_rollback')
        self.assertEqual(reg.active().version, 2)
    def test_recovery_reactivating_current_revision_is_idempotent(self):
        reg = Registry(now=lambda: 5)
        reg.activate(self.raw2, self.digest2, approve(self.digest2))
        same = reg.activate(self.raw2, self.digest2, approve(self.digest2))
        self.assertIs(same, reg.active())
        self.assertEqual(len(reg.history), 1)
if __name__ == '__main__':
    unittest.main()

# Governance demo for Subsystem 01. Run: set PYTHONPATH=src then python -m ceta.governance
# Uses the hash-pinned TEST FIXTURE only. It is not constitutional text (blocker B-03).
# The verifier is an injected test stub. The signature profile is unpinned (blocker B-04).
import hashlib
import sys
from pathlib import Path
from ceta.governance.rules import GovernanceError, Registry, approve_transition, evaluate

ROOT = Path(__file__).resolve().parents[3]
FIX = ROOT / 'tests' / 'fixtures' / 'governance'
ELIGIBLE = frozenset({'p1', 'p2'})



def stub(approval):
    return True



def packet(d):
    return [{'principal_id': 'p1', 'proposal_digest': d}, {'principal_id': 'p2', 'proposal_digest': d}]



def quorum(d):
    return approve_transition(d, packet(d), ELIGIBLE, 2, 5, 0, 10, verifier=stub)



def main():
    raw = (FIX / 'test-rule-set.json').read_bytes()
    pin = (FIX / 'test-rule-set.sha256').read_text(encoding='ascii').strip()
    d = hashlib.sha256(raw).hexdigest()
    print('python ' + sys.version.split()[0])
    print('fixture: tests/fixtures/governance/test-rule-set.json (TEST FIXTURE ONLY)')
    print('pin_match: ' + str(d == pin))
    ap = quorum(d)
    print('case_i quorum approved=' + str(ap.approved) + ' reasons=' + str(list(ap.reasons)))
    reg = Registry(now=lambda: 5)
    reg.activate(raw, pin, ap)
    print('case_i activated version=' + str(reg.active().version))
    print('case_i read subject_present=' + str(evaluate(reg.active(), 'read', {'subject_id': 'u1'})[0]))
    print('case_i read subject_absent=' + str(evaluate(reg.active(), 'read', {})[0]))
    reg2 = Registry(now=lambda: 5)
    try:
        reg2.activate(raw + b' ', pin, quorum(d))
        print('case_ii tampered: UNEXPECTED ACCEPT')
    except GovernanceError as exc:
        print('case_ii tampered rejected code=' + exc.code)
    print('case_iii no rule set decision=' + str(evaluate(None, 'read', {'subject_id': 'u1'})[0]))
    return 0



if __name__ == '__main__':
    sys.exit(main())

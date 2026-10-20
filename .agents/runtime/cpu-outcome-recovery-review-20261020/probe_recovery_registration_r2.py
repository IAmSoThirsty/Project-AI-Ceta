"""Independent actual-method repair probes; pure objects, no native/SQLite work."""
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
import ast
import hashlib
import json
import sys
import threading
from unittest.mock import patch

F = Path('T:/00-Active/Project-AI-CETA')
Q = F/'.agents/cpu-outcome-recovery-r4-20261020'
OLD = F/'.agents/cpu-outcome-recovery-20261017'
A = F/'.agents/runtime/cpu-outcome-recovery-repair-20261020'
R = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(A/'MANIFEST.json') == 'aa1ee89d9d0d63051b090590fea1d4391f9a4aad77ff8d8e92c6bfd04abe270e'
manifest = json.loads((A/'MANIFEST.json').read_bytes())
prior = json.loads((F/'.agents/runtime/cpu-outcome-recovery-20261017/cut-r3/MANIFEST.json').read_bytes())
changed = sorted(name for name in set(prior['payload_hashes']) | set(manifest['payload_hashes'])
    if prior['payload_hashes'].get(name) != manifest['payload_hashes'].get(name))
assert changed == ['src/ceta/kernel/cpu_execution.py', 'tests/contract/test_cpu_recovery_registration.py']
assert all(sha(Q/name) == expected for name, expected in manifest['payload_hashes'].items())
old_tree = ast.parse((OLD/'src/ceta/kernel/cpu_execution.py').read_bytes())
new_tree = ast.parse((Q/'src/ceta/kernel/cpu_execution.py').read_bytes())
old_cls = next(n for n in old_tree.body if isinstance(n, ast.ClassDef) and n.name == '_CpuExecutionCoordinator')
new_cls = next(n for n in new_tree.body if isinstance(n, ast.ClassDef) and n.name == '_CpuExecutionCoordinator')
new_method = next(n for n in new_cls.body if isinstance(n, ast.FunctionDef) and n.name == 'claim_recovery_liveness')
old_cls.body = [new_method if isinstance(n, ast.FunctionDef) and n.name == new_method.name else n for n in old_cls.body]
assert ast.dump(old_tree) == ast.dump(new_tree)
blocked = []
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.startfile', 'sqlite3.connect',
                 'socket.__new__', 'socket.bind', 'socket.connect'):
        blocked.append(event); raise RuntimeError('REVIEW_PURE_SCOPE_ONLY')
sys.addaudithook(audit)
sys.path.insert(0, str(Q/'src'))
import ceta.kernel.cpu_execution as module
from ceta.kernel.cpu_outcome_recovery import _CpuOutcomeRecovery

class FaultMap(dict):
    def __init__(self, primary=None, *, after=False, cleanup=None):
        super().__init__(); self.primary, self.after, self.cleanup = primary, after, cleanup
    def __setitem__(self, key, value):
        if self.after: super().__setitem__(key, value)
        if self.primary is not None: raise self.primary
        if not self.after: super().__setitem__(key, value)
    def __delitem__(self, key):
        if self.cleanup is not None: raise self.cleanup
        super().__delitem__(key)

class HostilePrimary(BaseException):
    def __setattr__(self, name, value): raise RuntimeError('attribute hook forbidden')

def fixture():
    c = object.__new__(module._CpuExecutionCoordinator)
    c.owners, c.store = object(), object()
    c.kernel = SimpleNamespace(_owners=c.owners, _store=c.store)
    c.active, c.mutating = None, 0
    lease = object.__new__(module._RetainedCpuExecution)
    lease._owner, lease._recovery = c, object()
    lease._called, lease._dispatching = True, False
    lease._thread, lease._closed = threading.get_ident(), True
    lease._pending_cleanup, lease._cleanup_failure = False, None
    return c, lease

def maps(owners, stores, mutations=None):
    return patch.multiple(module, _ACTIVE_OWNERS=owners, _ACTIVE_STORES=stores,
        _MUTATING_OWNERS={} if mutations is None else mutations[0],
        _MUTATING_STORES={} if mutations is None else mutations[1])

checks = []
def publication_case(name, which, after, primary):
    c, lease = fixture()
    owners = FaultMap(primary, after=after) if which == 'owner' else {}
    stores = FaultMap(primary, after=after) if which == 'store' else {}
    with maps(owners, stores):
        try: c.claim_recovery_liveness(lease)
        except BaseException as error: assert error is primary
        else: raise AssertionError('failure swallowed')
        assert not owners and not stores and c.active is None
        assert not lease._pending_cleanup
        c.require_selected_coordinator()
    checks.append(dict(name=name, passed=True, primary_preserved=True, exact_rows_retired=True))

for which in ('owner', 'store'):
    for after in (False, True):
        publication_case(f'{which} publication '+('after' if after else 'before'), which, after, MemoryError())
for kind in (KeyboardInterrupt, SystemExit):
    for after in (False, True):
        publication_case(f'{kind.__name__} store '+('after' if after else 'before'), 'store', after, kind())
for failing_cleanup in ('owner', 'store', 'hostile-primary'):
    c, lease = fixture()
    primary = HostilePrimary() if failing_cleanup == 'hostile-primary' else MemoryError()
    secondary = RuntimeError('cleanup refusal')
    owners = FaultMap(cleanup=secondary if failing_cleanup != 'store' else None)
    stores = FaultMap(primary, after=True, cleanup=secondary if failing_cleanup == 'store' else None)
    with maps(owners, stores):
        try: c.claim_recovery_liveness(lease)
        except BaseException as error: assert error is primary
        else: raise AssertionError('failure swallowed')
        data = BaseException.__dict__['__dict__'].__get__(primary)
        assert lease in data['cpu_registration_custody']
        assert data['cpu_registration_cleanup_failures'][0][0] is secondary
        assert lease._pending_cleanup and lease._cleanup_failure is secondary
        assert c.active is None and (owners or stores)
        owners.cleanup = stores.cleanup = None
        c.release_liveness(lease)
        assert not owners and not stores
        c.require_selected_coordinator()
    checks.append(dict(name='uncertain cleanup '+failing_cleanup, passed=True,
        primary_preserved=True, exact_lease_attached=True, explicit_cleanup_retry_succeeded=True))
for foreign in (False, True):
    c, lease = fixture()
    winner_c, winner = fixture()
    if not foreign:
        winner_c = c; winner._owner = c; c.active = winner
    else:
        winner_c.owners, winner_c.store = c.owners, c.store
        winner_c.kernel = SimpleNamespace(_owners=c.owners, _store=c.store)
        winner_c.active = winner
    row = (c.owners, c.store, winner_c, winner)
    owners, stores = {id(c.owners): row}, {id(c.store): row}
    with maps(owners, stores):
        try: c.claim_recovery_liveness(lease)
        except module.ContractError: pass
        else: raise AssertionError('busy winner not refused')
        assert owners[id(c.owners)] is row and stores[id(c.store)] is row
        assert c.active is (None if foreign else winner)
        winner_c.release_liveness(winner)
        assert not owners and not stores
    checks.append(dict(name='preserve '+('foreign coordinator' if foreign else 'valid local winner'), passed=True))
for which in ('owner', 'store'):
    c, lease = fixture(); owners, stores = {}, {}
    mutations = ({id(c.owners): object()}, {}) if which == 'owner' else ({}, {id(c.store): object()})
    with maps(owners, stores, mutations):
        try: c.claim_recovery_liveness(lease)
        except module.ContractError: pass
        else: raise AssertionError('mutation conflict not refused')
        assert not owners and not stores and c.active is None
    checks.append(dict(name='preserve '+which+' mutation exclusion', passed=True))
c, lease = fixture(); owners, stores = {}, {}
with maps(owners, stores):
    c.claim_recovery_liveness(lease)
    assert c.active is lease and owners[id(c.owners)][3] is lease and stores[id(c.store)][3] is lease
    c.release_liveness(lease)
    assert not owners and not stores and c.active is None
checks.append(dict(name='successful exact claim and release', passed=True))
assert len(checks) == 16

# Investigate the verifier's repeated exact-private-claim hypothesis separately.
c, lease = fixture(); owners, stores = {}, {}
with maps(owners, stores):
    c.claim_recovery_liveness(lease)
    try: c.claim_recovery_liveness(lease)
    except module.ContractError as error: assert 'CPU_RECOVERY_LIVENESS_BUSY' in str(error)
    else: raise AssertionError('private repeat not refused')
    private_withdraws = not owners and not stores and c.active is None
    assert private_withdraws
c, lease = fixture(); owners, stores = {}, {}
with maps(owners, stores):
    c.claim_recovery_liveness(lease)
    original_recovery = lease._recovery
    lease._context, lease._used, lease._dispatch = object(), True, True
    lease._permit, lease._attempt, lease._recovery_history = object(), object(), ()
    public = _CpuOutcomeRecovery(lease, lease._context)
    try: public.__enter__()
    except module.ContractError as error: assert 'CPU_RECOVERY_ORIGINAL_ATTEMPT_REQUIRED' in str(error)
    else: raise AssertionError('public repeat not refused')
    assert c.active is lease and owners[id(c.owners)][3] is lease and stores[id(c.store)][3] is lease
    assert lease._recovery is original_recovery
    c.release_liveness(lease)
    assert not owners and not stores
assert not blocked
assert all(sha(Q/name) == expected for name, expected in manifest['payload_hashes'].items())
record = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    manifest_sha256=sha(A/'MANIFEST.json'), production_method_sha256=manifest['payload_hashes']['src/ceta/kernel/cpu_execution.py'],
    changed_paths=changed, only_production_AST_change='claim_recovery_liveness',
    checks=checks, passed_repair_cases=16, failed_repair_cases=0,
    original_reproduction_now_retired=True,
    additional_edge=dict(direct_exact_private_repeat_withdraws_existing_rows=private_withdraws,
        actual_public_repeat_guard_preserves_rows=True,
        classification='requires separate follow-up work; internal defensive gap, no public failure path established',
        evidence_scope='Actual private method and actual public recovery entry guard, synthetic typed objects.',
        suggestion='Before changing cleanup, distinguish a new registration publication from pre-existing exact-lease liveness.'),
    candidate_payloads=375, candidate_hashes_unchanged=True, native_operations=0,
    sqlite_connections=0, prohibited_events=blocked,
    limitations=['Pure actual-method probes with synthetic correctly typed custody.',
        'Public/native/cross-process recovery acceptance remains open.'])
path = R/'REGISTRATION-REPAIR-PROOFS-R2.json'
with path.open('x', encoding='utf8') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
print(json.dumps(dict(path=str(path), sha256=sha(path), passed=16,
    private_repeat_observed=True, public_repeat_preserves_custody=True)))

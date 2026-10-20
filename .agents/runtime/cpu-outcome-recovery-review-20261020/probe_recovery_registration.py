"""Pure actual-method failure injection; synthetic custody, no SQLite or native calls."""
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
import hashlib
import json
import sys
import threading

F = Path('T:/00-Active/Project-AI-CETA')
Q = F/'.agents/cpu-outcome-recovery-20261017'
R = Path(__file__).resolve().parent
source = Q/'src/ceta/kernel/cpu_execution.py'
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha == '4bffc411aaf0a85b2214fd75ecf154cb32f7673cf96d7518409586b3c7dbe5f2'
blocked = []
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.startfile', 'sqlite3.connect',
                 'socket.__new__', 'socket.connect', 'socket.bind'):
        blocked.append(event)
        raise RuntimeError('REVIEW_PURE_SCOPE_ONLY')
sys.addaudithook(audit)
sys.path.insert(0, str(Q/'src'))
import ceta.kernel.cpu_execution as module

class RejectSecondPublication(dict):
    def __setitem__(self, key, value):
        raise MemoryError('review-controlled second registration publication failure')

coordinator = object.__new__(module._CpuExecutionCoordinator)
coordinator.owners, coordinator.store = object(), object()
coordinator.kernel = SimpleNamespace(_owners=coordinator.owners, _store=coordinator.store)
coordinator.active = None
coordinator.mutating = 0
lease = object.__new__(module._RetainedCpuExecution)
lease._owner = coordinator
lease._recovery = object()
lease._called, lease._dispatching = True, False
lease._thread, lease._closed = threading.get_ident(), True
old_owners, old_stores = module._ACTIVE_OWNERS, module._ACTIVE_STORES
module._ACTIVE_OWNERS, module._ACTIVE_STORES = {}, RejectSecondPublication()
try:
    primary = None
    try:
        coordinator.claim_recovery_liveness(lease)
    except MemoryError as error:
        primary = error
    assert primary is not None
    orphan = module._ACTIVE_OWNERS.get(id(coordinator.owners))
    assert orphan is not None and orphan[3] is lease
    assert coordinator.active is None
    assert not module._ACTIVE_STORES
    selected_error = None
    try:
        coordinator.require_selected_coordinator()
    except module.ContractError as error:
        selected_error = str(error)
    assert selected_error and 'CPU_EXECUTION_OTHER_KERNEL_ACTIVE' in selected_error
    assert not blocked
    result = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
        actual_method='ceta.kernel.cpu_execution._CpuExecutionCoordinator.claim_recovery_liveness',
        source_path=str(source), source_sha256=source_sha,
        primary_type=type(primary).__name__, primary=str(primary),
        owner_registration_survives=True, store_registration_absent=True,
        coordinator_active_is_none=True, subsequent_selected_denial=selected_error,
        primary_has_custody_attachment=hasattr(primary, 'owned_cpu_execution'),
        native_operations=0, sqlite_connections=0, prohibited_events=blocked,
        source_or_candidate_mutations=False,
        limitations=['Synthetic correctly typed coordinator and lease objects.',
            'Real reviewed method executed; no claim of a native Windows recovery journey.'])
finally:
    module._ACTIVE_OWNERS, module._ACTIVE_STORES = old_owners, old_stores
path = R/'REGISTRATION-FAILURE-REPRODUCTION.json'
with path.open('x', encoding='utf8') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(dict(result=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    defect_reproduced=True)))

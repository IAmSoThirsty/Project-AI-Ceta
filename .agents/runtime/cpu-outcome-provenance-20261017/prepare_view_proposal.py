"""Build an unapplied, exact-base view delta and exercise its pure seam in memory."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import ctypes
import difflib
import hashlib
import json
import os
import sys
from unittest.mock import patch

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-outcome-provenance-20261017'
R = Path(__file__).resolve().parent
B = F / '.agents/cpu-capacity-connection-20261017/src/ceta/identity/native_owner_view.py'
PIN = 'd565621c02d97b4f7322f92c6fd9ae53f21772cc7c006bd689fd6ab134691672'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
assert sha(B) == PIN
before = B.read_text(encoding='utf8')
old_signature = 'def __init__(self, registry, clock_owner, store_binding, *, outcome_budget=None):'
assert before.count(old_signature) == 1
after = before.replace(old_signature,
    'def __init__(self, registry, clock_owner, store_binding, *, outcome_budget=None, cpu_outcome_observer=None):')
anchor = '        self._outcome_budget = outcome_budget\n'
assert after.count(anchor) == 1
after = after.replace(anchor, anchor + '''        self._cpu_outcome = None
        if cpu_outcome_observer is not None:
            from .native_cpu_outcome import NativeCpuOutcomeProvenance
            self._cpu_outcome = NativeCpuOutcomeProvenance(self, cpu_outcome_observer)

    @property
    def require_owned_cpu_outcome_provenance(self):
        return None if self._cpu_outcome is None else self._require_owned_cpu_outcome_provenance

    def _require_owned_cpu_outcome_provenance(self, request, permit, receipt, observation,
                                            proof, peer, context, retained):
        from .native_cpu_outcome import NativeCpuOutcomeProvenance
        producer = self._cpu_outcome
        require(type(producer) is NativeCpuOutcomeProvenance and producer._view is self,
                'CPU_OUTCOME_VIEW_PRODUCER_CHANGED')
        return producer.require_current(self, request, permit, receipt, observation,
                                        proof, peer, context, retained)
''')
proposed = R / 'native_owner_view.PROPOSED.py'
with proposed.open('x', encoding='utf8', newline='\n') as stream: stream.write(after)
delta = R / 'NativeOwnerView.PROPOSED.diff'
with delta.open('x', encoding='utf8', newline='\n') as stream:
    stream.write(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='capacity-cut-r1/src/ceta/identity/native_owner_view.py',
        tofile='PROPOSED/src/ceta/identity/native_owner_view.py')))
def methods(raw):
    cls = next(node for node in ast.parse(raw).body if isinstance(node, ast.ClassDef) and node.name == 'NativeOwnerView')
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
original, proposed_methods = methods(before), methods(after)
assert all(ast.dump(node) == ast.dump(proposed_methods[name]) for name, node in original.items() if name != '__init__')
events = []
def audit(event, args):
    if event in ('ctypes.dlopen', 'subprocess.Popen', 'os.system', 'sqlite3.connect',
                 'os.startfile', 'socket.connect', 'socket.bind'):
        events.append(event); raise AssertionError(event)
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        flags = args[2]
        if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            assert Path(os.fsdecode(args[0])).resolve().is_relative_to(R)
sys.addaudithook(audit)
sys.path[:0] = [str(Q / 'src')]
import ceta.identity.native_owner_view as view_module
from ceta.identity.native_cpu_outcome import NativeCpuOutcomeProvenance
from ceta.effects.native_observer import NativeCpuEffectObserver
from ceta.contracts.wire import ContractError
namespace = dict(vars(view_module))
names = ('__init__', 'require_owned_cpu_outcome_provenance', '_require_owned_cpu_outcome_provenance')
for name in names:
    tree = ast.Module(body=[proposed_methods[name]], type_ignores=[])
    exec(compile(tree, str(proposed), 'exec'), namespace)
View = view_module.NativeOwnerView
registry = object.__new__(view_module.WindowsPeerRegistry)
clock = object.__new__(view_module.NativeSessionClock)
binding = object.__new__(view_module.NativeStoreBinding)
observer = object.__new__(NativeCpuEffectObserver)
observer._clock = clock
observer._executable, observer._image, observer._commitment, observer._driver_sha = ('CONTROLLED', 'a'*64, 'b'*64, 'c'*64)
checks = []
with patch.object(View, '__init__', namespace['__init__']), \
     patch.object(View, 'require_owned_cpu_outcome_provenance', namespace['require_owned_cpu_outcome_provenance'], create=True), \
     patch.object(View, '_require_owned_cpu_outcome_provenance', namespace['_require_owned_cpu_outcome_provenance'], create=True):
    absent = View(registry, clock, binding)
    assert absent.require_owned_cpu_outcome_provenance is None
    checks.append('uncomposed_default_is_None')
    view = View(registry, clock, binding, cpu_outcome_observer=observer)
    method = view.require_owned_cpu_outcome_provenance
    assert method.__self__ is view and type(view._cpu_outcome) is NativeCpuOutcomeProvenance
    checks.append('composed_callback_is_bound_to_exact_view')
    args = tuple(object() for _ in range(8))
    with patch.object(NativeCpuOutcomeProvenance, 'require_current', autospec=True, return_value=None) as callback:
        assert method(*args) is None
        callback.assert_called_once_with(view._cpu_outcome, view, *args)
    checks.append('forwarder_passes_exact_original_arguments')
    view._cpu_outcome = object()
    try: method(*args)
    except ContractError: pass
    else: raise AssertionError('REPLACED_PRODUCER_ACCEPTED')
    checks.append('substituted_producer_is_denied')
assert not events and sha(B) == PIN
save(R / 'VIEW-PROPOSAL.json', dict(at=datetime.now(timezone.utc).isoformat(),
    author='/root/publication_recovery_review', status='PROPOSED_UNAPPLIED_CONTROLLED_SEAM_CHECKED',
    base=dict(path=str(B), sha256=PIN), proposed=dict(path=str(proposed), sha256=sha(proposed)),
    delta=dict(path=str(delta), sha256=sha(delta)), unchanged_other_methods=len(original)-1,
    controlled_checks=checks, forbidden_events=events, runner_sha256=sha(__file__),
    command=[sys.executable, '-B', '-X', 'utf8', *sys.argv], native_cases_executed=0,
    Source_publication=False, copied_source_LOC_credit=0))
print(json.dumps(dict(passed=True, checks=checks, receipt_sha256=sha(R / 'VIEW-PROPOSAL.json'))))

"""Read-only final checks and rejected-cut report. No profile mutation."""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import ctypes, hashlib, importlib.util, json, os, stat, subprocess, sys

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/ac2-20261014'
D = R / 'profile-tool-independent-review'
A = D / 'attempt-r2'
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert Path(sys.executable) == PY and not sys.flags.optimize
sys.dont_write_bytecode = True
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
utc = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    assert path.is_relative_to(D)
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write('\n'); output.flush(); os.fsync(output.fileno())
def ref(path): return {'repository_relative_path': path.relative_to(F).as_posix(), 'sha256': sha(path)}

tool_path = R / 'profile_qualification.py'
pin = '45c09e4cb0fe05d3993e8bb6f68b6414b6c0bd69e493736a0a36836aa681a3c9'
assert sha(tool_path) == pin
native_windll = ctypes.WinDLL
blocked = []
class Denied:
    def __init__(self, name): self.name = name
    def __call__(self, *args): blocked.append(self.name); raise AssertionError('PROFILE_MUTATION_FORBIDDEN')
class Guard:
    def __init__(self, dll): self.dll = dll
    def __getattr__(self, name):
        if name in ('CreateAppContainerProfile', 'DeleteAppContainerProfile'): return Denied(name)
        return getattr(self.dll, name)
def dll(name, *args, **kwargs): return Guard(native_windll(name, *args, **kwargs))

with patch.object(ctypes, 'WinDLL', dll):
    spec = importlib.util.spec_from_file_location('independent_final_profile_tool', tool_path)
    tool = importlib.util.module_from_spec(spec); sys.modules[spec.name] = tool; spec.loader.exec_module(tool)
    apis, closes = [], []
    original_init = tool.module._IsolationAPI.__init__
    def capture_api(instance):
        original_init(instance); apis.append(instance)
        original_close = instance.close
        def capture_close(handle):
            result = original_close(handle)
            closes.append({'handle': handle, 'native_CloseHandle_return_checked_by_library': True})
            return result
        instance.close = capture_close
    with patch.object(tool.module._IsolationAPI, '__init__', capture_api):
        inspection = tool.inspect()
    residual = [list(instance.pending_native_resources()) for instance in apis]
    assert not blocked and not any(residual)
    assert inspection['prior_folder']['HRESULT'] in (-2147024894, -2147024893)
    assert inspection['prior_folder']['path'] is None
    save(D / 'ACTUAL-READ-ONLY-INSPECTION.json', {'at': utc(), 'inspection': inspection,
        'captured_API_instances': len(apis), 'native_close_observations': closes,
        'pending_native_resources_after': residual, 'profile_mutation_attempts': blocked,
        'actual_Create_Delete_executed': False, 'worker_or_job_launch_executed': False,
        'scope': 'Exact caller token/SID derivation/folder query only; no whole-host census.'})

    # Compare against actual accepted ER1; no fixture or runtime file is written there.
    baseline = F / '.agents/runtime/er1-20261014/active-application/environment-after.json'
    acceptance_path = F / '.agents/runtime/er1-20261014/actual-acceptance.json'
    accepted, environment = read(acceptance_path), read(baseline)
    assert accepted['sequence'] == 13 and accepted['claims'] == {}
    assert set(accepted['actual_states'].values()) == {'SUCCEEDED'}
    root = Path(environment['source_root']); assert root == PY.parents[1]
    expected = {row['relative_path']: row for row in environment['members']}
    observations, directory_size_differences = {}, []
    for name, row in expected.items():
        path = root / name
        if row['kind'] == 'ordinary_file':
            facts = tool.observed(path)
            assert facts['sha256'] == row['sha256'] and facts['native_identity'] == row['native_identity'], name
            assert facts['native_identity']['bytes'] == row['bytes']
            observations[name] = facts
        else:
            info = tool.fs.lstat(tool.fs.safe_components(path))
            assert stat.S_ISDIR(info.st_mode) and not tool.fs.reparse(info)
            current, prior = tool.fs.file_identity(info), row['native_identity']
            assert {k:v for k,v in current.items() if k != 'bytes'} == {k:v for k,v in prior.items() if k != 'bytes'}, name
            if current['bytes'] != prior['bytes']:
                directory_size_differences.append({'relative_path': name,
                    'before_bytes': prior['bytes'], 'current_bytes': current['bytes']})
    actual_names = set()
    for directory, directories, files in os.walk(tool.fs.io_path(root), followlinks=False):
        normal = root / Path(directory).relative_to(Path(tool.fs.io_path(root)))
        for name in directories + files: actual_names.add((normal / name).relative_to(root).as_posix())
    assert actual_names == set(expected)
    current_root = tool.fs.file_identity(tool.fs.lstat(root))
    assert {k:v for k,v in current_root.items() if k != 'bytes'} == {
        k:v for k,v in environment['root_native_identity'].items() if k != 'bytes'}
    assert len(observations) == 3601
    save(D / 'ENVIRONMENT-CONSERVATION.json', {'at': utc(), 'accepted_after': ref(baseline),
        'accepted_lifecycle': ref(acceptance_path), 'ordinary_files': len(observations),
        'ordinary_bytes': sum(row['native_identity']['bytes'] for row in observations.values()),
        'ordinary_file_bytes_identities_and_membership_exact': True,
        'all_membership_exact': True, 'directory_nonsize_metadata_exact': True,
        'directory_size_differences': directory_size_differences, 'observations': observations})

    conservation = read(A / 'CONSERVATION.json')
    assert conservation['Source290_native_and_hash_exact'] and conservation['candidate294_native_and_hash_exact']
    current_source = tool.source_cut()
    assert current_source == conservation['Source290_after']
    current_candidate = {relative: tool.observed(tool.Q / relative)
        for relative in read(tool.Q / 'TRANSFER-MANIFEST.json')['payloads']}
    assert current_candidate == conservation['candidate294_after']
    for name, facts in conservation['inputs_after'].items(): assert tool.observed(F / name) == facts, name
    source_after = {'at': utc(), 'Source290': current_source, 'candidate294': current_candidate,
        'inputs_exact': True, 'Source_candidate_native_and_hash_conserved': True}
    save(D / 'FINAL-CONSERVATION.json', source_after)

    # Avoid platform-dependent separator assumptions in the first reader's booleans.
    cases = read(A / 'exception-windows-r1.json')['cases']
    case_confirmation = []
    for row in cases:
        matches = list(A.glob('controlled-' + row['label'] + '-*'))
        assert len(matches) == 1
        actual_files = [path.name for path in matches[0].rglob('*') if path.is_file()]
        assert 'RESULT.json' not in actual_files and 'PROFILE-RETAINED.json' not in actual_files
        assert 'SOURCE-AFTER.json' not in actual_files
        case_confirmation.append({'label': row['label'], 'actual_file_basenames': sorted(actual_files),
            'RESULT_PROFILE_RETAINED_SOURCE_AFTER_all_absent': True})
    save(D / 'EXCEPTION-FILE-CONFIRMATION.json', {'at': utc(), 'cases': case_confirmation,
        'reason': 'Platform-independent Path.name confirmation; initial reader used POSIX suffix checks on Windows paths.'})

    state_path, claims_path = R / 'ac2-20261014/state.json', R / 'ac2-20261014/claims.json'
    state, claims = read(state_path), read(claims_path)
    assert state['sequence'] == 9 and state['nodes']['review']['state'] == 'SUCCEEDED' and claims == {}
    git = lambda args: subprocess.run(['git', *args], cwd=F, capture_output=True, text=True, check=True).stdout.strip()
    git_facts = {'root': git(['rev-parse','--show-toplevel']), 'HEAD': git(['rev-parse','HEAD']),
                 'branch': git(['branch','--show-current']), 'tracked_status': git(['status','--short','--untracked-files=no'])}
    report = {
        'reviewer': '/root/wt1_reviewer', 'author': '/root', 'at': utc(),
        'decision': 'REJECTED_REPAIR_REQUIRED', 'exact_tool': ref(tool_path),
        'scope': 'Prepared operator-side host profile qualification tool only; no change to AC2 library review.',
        'write_scope': str(D), 'Source_changes': [], 'host_profile_mutations': [],
        'operator_approval_records_created': [], 'git': git_facts,
        'requirements_checked': ['explicit exact operator receipt gate', 'prior-profile refusal and create outcome',
            'native SID/pointer custody', 'post-create exception paths', 'fixed binary and helper binding',
            'fresh fixture ACL containment', 'captured process/handle retirement before Delete',
            'folder/residual reports', 'Source/candidate/E3 conservation'],
        'verified_findings': [
            {'id':'PROFILE-TOOL-F01', 'classification':'blocking current tool acceptance',
             'title':'Post-create exceptions escape resource custody and final reporting',
             'code_lines':[179,199,226,248], 'severity':'high operational risk',
             'proof':ref(A / 'exception-windows-r1.json'),
             'file_confirmation':ref(D / 'EXCEPTION-FILE-CONFIRMATION.json'),
             'facts':'Four controlled negative cases after simulated successful Create escape without RESULT, PROFILE-RETAINED or SOURCE-AFTER. SID conversion failure retains simulated pointer 12345 without release.',
             'limit':'Exact post-gate AST suffix only; native Create/Delete and genuine operator gate were not executed or represented as accepted.',
             'repair':'Cover the complete native-effect and cleanup interval with outer custody/final reporting. Register output pointers immediately, include creator API residuals, preserve primary exceptions, and independently attempt permitted SID release and residual reporting even when one evidence write fails. Never delete unknown/preexisting profiles.'},
            {'id':'PROFILE-TOOL-F02', 'classification':'blocking current tool acceptance',
             'title':'Copied worker can differ from the hash asserted in its binding',
             'code_lines':[110,113,127,130], 'severity':'high integrity risk',
             'proof':ref(A / 'binary-drift-r1.json'),
             'facts':'Exact prepare_probe executes successfully after a controlled differing second source read. Copied hash is 097a647accc5f9f625baa9659364efea9b3b08eb7ff03473ecd58433f7b12649; receipt claims 527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f. Actual original binary is unchanged.',
             'limit':'Controlled read drift, no binary execution, native probe or actual host race.',
             'repair':'Read and pin one exact byte payload/native identity, verify its expected hash, copy that payload, durably verify the copy, and bind subsequent fixture/launch checks to the fixed expected image hash.'},
            {'id':'PROFILE-TOOL-F03', 'classification':'blocking current tool acceptance',
             'title':'Runtime driver/support imports are not constrained to the reviewed dependency cut',
             'code_lines':[103,107,116,126,127], 'severity':'integrity gap',
             'proof':ref(D / 'profile_qualification.py'),
             'facts':'prepare_probe reads native_fixture_support.py with only a replacement-needle assertion, loads ac2_support.py without an expected hash, and records the driver hash after executing the imported driver. Frozen Q294 pins do not cover these runtime paths.',
             'limit':'Verified by complete code inspection. No changed untrusted helper was executed.',
             'repair':'Before any import or fixture preparation, verify exact reviewed driver/support hashes and native identities, and carry their bindings into the prepared driver and evidence. Reopen review if dependencies change.'}
        ],
        'verified_strengths':[
            {'fact':'Exact current candidate294 hashes/native identities validated before product imports; actual Source290 native/hash endpoints preserved.', 'evidence':ref(D / 'FINAL-CONSERVATION.json')},
            {'fact':'Four original negative methods passed unchanged at the TestCase AST level under an owned relocated harness.', 'evidence':ref(A / 'original4-r1.json')},
            {'fact':'Native inspect measured the exact current caller/name/SID and absent profile folder. Captured API residual lists are empty; profile mutation entrypoints were forbidden.', 'evidence':ref(D / 'ACTUAL-READ-ONLY-INSPECTION.json')},
            {'fact':'Fixture driver uses fresh UUID descendants, safe component checks before ACL operations, exact SID ACEs and protected sentinels; deletion requires a successful per-run creation record and retirement predicate.', 'evidence':ref(F / '.agents/runtime/ac1-20261014/native_fixture_support.py')}
        ],
        'tests': {'unique_original_methods':4, 'pass':4, 'fail':0, 'error':0, 'skip':0,
            'additional_negative_oracles':5, 'additional_oracles':'1 exact binary-copy drift and 4 controlled exceptional suffix cases',
            'root_original4_receipt_preserved':ref(R / 'profile-preparation-tests-r1.json')},
        'library_review_unchanged':{'sequence':9, 'review_state':'SUCCEEDED','claims':{},
            'state':ref(state_path),'claim_record':ref(claims_path),
            'positive_isolation_qualified':False,'Source_application':False},
        'conservation':{'Source290_candidate294':ref(D / 'FINAL-CONSERVATION.json'),
            'E3':ref(D / 'ENVIRONMENT-CONSERVATION.json')},
        'limitations': ['No host profile Create/Delete or ACL mutation executed.',
            'No positive isolated-worker run, genuine operator consent, CETA authority, or public real-effect milestone was qualified.',
            'Receipt fields cannot themselves prove a human uttered an approval; the coordinator must preserve actual user provenance.',
            'No actual concurrent profile replacement or Windows create/delete failure was tested.',
            'Equal endpoint hashes/native identities establish these observed cuts, not continuous custody.'],
        'hypotheses_unresolved': ['Concurrent same-name profile replacement between successful creation and name-based deletion is not an OS instance-identity fence; no such event was observed.'],
        'failed_attempts':[{'proof':ref(D / 'reader-failure-r1.json'),
            'disposition':'Fixed only reviewer AST end-line metadata in append-only r2; initial files retained.'}],
        'next_action':'Root repairs these exact tool/dependency boundaries in a separate scope; preserve this cut and failures, then request an independent review of the repaired cut before the precise owner approval request.',
        'review_scope_complete':True, 'tool_approved_for_host_profile_creation':False}
    save(D / 'REPORT.json', report)
    print(json.dumps({'decision':report['decision'], 'report_sha256':sha(D / 'REPORT.json'),
        'findings':3,'Source290':len(current_source),'candidate294':len(current_candidate),
        'E3_ordinary_files':len(observations),'actual_Create_Delete':False}), flush=True)

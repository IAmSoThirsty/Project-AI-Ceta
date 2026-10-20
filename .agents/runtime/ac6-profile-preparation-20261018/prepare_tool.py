"""Prepare AC6 files only. Never import or execute the qualification entrypoint."""
from pathlib import Path
from datetime import datetime, timezone
import ast, difflib, hashlib, json, os, sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
A = F / '.agents/runtime/ac5-profile-tool-20261015'
assert R == F / '.agents/runtime/ac6-profile-preparation-20261018'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name, value):
    raw = value.encode('utf-8') if isinstance(value, str) else (json.dumps(value, indent=2, allow_nan=False)+'\n').encode('utf-8')
    with (R/name).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
def replace(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)

assert sha(A/'profile_qualification.py') == '530238cbb5d5601802e96864a085a4d4becb0d0d045e3bf13286b5718b7d9a6e'
assert sha(A/'run_one_approved_attempt_v2.py') == '372a14a567ddecc4ccb67848669afe641d71ebc7b1d66aaad4dcaa0b5b709570'
published = F/'.agents/runtime/js8-20261015/amendment-report1/active-application/APPLIED.json'
assert sha(published) == 'b22b2f404a8373be3eb7bcd2ab9c974f5dba187aed2c787fb62f54fac7508a87'
source = json.loads(published.read_bytes())['source352']
assert len(source) == 352
for name, facts in source.items():
    assert sha(F/name) == facts['sha256'], name
assert sha(F/'src/ceta/supervisor/isolated_worker.py') == sha(F/'.agents/ac5-20261015/src/ceta/supervisor/isolated_worker.py')
build = F/'.agents/runtime/ac1-20261014/build-r2/build.json'
assert json.loads(build.read_bytes())['source']['sha256'] == sha(F/'native/windows_broker/isolated_worker.rs')
write('TASK-BINDING.json', {'at':datetime.now(timezone.utc).isoformat(), 'actor':'/root/native_denial_diagnosis',
    'coordinator':'/root', 'job':'Prepare current-source AC6 successor; no execution',
    'exclusive_write_scope':str(R), 'authority':'Explicit Root single-job assignment in current agent session',
    'reads':'Current project, existing same-project AC5/AC3/AC1 receipts and installed E3 runtime',
    'prohibited':['Source/candidate/ledger changes','profile create/delete','worker launch','ACL/token/firewall/loopback/account changes','elevation','Hello'],
    'reviewer':'Root or a separately assigned reviewer; author does not independently approve',
    'stop_conditions':['input drift','unexpected host operation','new approval needed for execution'],
    'acceptance':'Exact minimal delta, controlled checks, pinned proposal, explicit dormant state',
    'product_TAAR_transition':'Not applicable: operator-tool preparation, no product node claimed or completed'})
proposal = json.loads((A/'PROFILE-CREATION-PROPOSAL-AC5.json').read_bytes())
proposal.update({'schema':'ceta-ac6-profile-proposal-v1', 'status':'PREPARED_REQUIRES_DISTINCT_REVIEW_AND_NEW_EXPLICIT_HUMAN_APPROVAL',
    'at':datetime.now(timezone.utc).isoformat(), 'source_root':str(F), 'source_payloads':352,
    'source_publication':{'path':str(published),'sha256':sha(published)},
    'execution_source':'Canonical F/src, byte-identical accepted AC5 isolation implementation; no product edits',
    'candidate_manifest':None, 'candidate_review':None,
    'prior_tool':{'path':str(A/'profile_qualification.py'),'sha256':sha(A/'profile_qualification.py')},
    'prior_distinct_review':{'path':str(F/'.agents/runtime/ac5-profile-tool-review2-20261015/review.json'), 'sha256':sha(F/'.agents/runtime/ac5-profile-tool-review2-20261015/review.json')},
    'current_isolation_sha256':sha(F/'src/ceta/supervisor/isolated_worker.py'),
    'current_jobs_sha256':sha(F/'src/ceta/supervisor/windows_jobs.py'),
    'native_build_receipt':{'path':str(build),'sha256':sha(build)},
    'path_change':'Full UUID retained; owned attempt directory q-<uuid> replaces profile-qualification-<uuid>. Pre-profile projected and pre-launch actual native paths must be shorter than 258 characters.',
    'prior_denials':{'267':'Historical native cwd269/image296; length is a confound, sole causality unproved', '2':'Current native cwd235/image262; files existed, missing Windows object unproved'},
    'native_effects_if_later_approved':['One exact new AppContainer profile with zero capabilities','One bounded restricted worker and one owned ordinary control process','DACL and low/medium integrity labels only on newly created owned disposable fixture descendants','One owned bounded loopback test listener and restricted connection/listen/UDP denial probes','Delete only the exact new profile after recorded retirement; retain uncertainty'],
    'no_execution_release_conditions':['Distinct review approves exact tool, wrapper, proposal and controlled evidence','Root records Source352 acceptance and rechecks every hash/native identity and dependencies','No competing native qualification cohort','Fresh explicit actual user approval identifies the exact proposal/tool and all listed host effects','Fresh profile absence and exact user/SID checks succeed','No prior attempt marker or owned q-* attempt directory'],
    'post_cleanup_no_profile_regression':'Excluded from this single-attempt proposal; separate explicit bounded release required',
    'approval_record_created':False, 'profile_operations':[], 'worker_launches':[], 'Source_application':False,
    'documentation':'https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory'})
for key in ('candidate_manifest_sha256','candidate_review_sha256'):
    proposal.pop(key, None)
write('PROFILE-CREATION-PROPOSAL-AC6.json', proposal)
old = (A/'profile_qualification.py').read_text()
text = old.replace("ORIGINAL_R = F / '.agents/runtime/ac5-20261015'", "ORIGINAL_R = F / '.agents/runtime/ac5-profile-tool-20261015'")
text = text.replace("assert R == F / '.agents/runtime/ac5-profile-tool-20261015'", "assert R == F / '.agents/runtime/ac6-profile-preparation-20261018'")
text = replace(text, "Q = F / '.agents/ac5-20261015'", 'Q = F  # The execution view is the canonical published source, not a private candidate.')
text = text.replace('22263a72a8208e4024b94088ba95cf651846f542c44fa6fe44a68957eb29aa3e', sha(published))
text = text.replace('PROFILE-CREATION-PROPOSAL-AC5.json', 'PROFILE-CREATION-PROPOSAL-AC6.json')
text = text.replace('.agents/runtime/perf1-20261014/active-application/destination-full-r1.json', '.agents/runtime/js8-20261015/amendment-report1/active-application/APPLIED.json')
text = text.replace('428c4edff050dc130dfe64e15becff1d9167eb6697687e47c208657d7bbf30c4', sha(published))
text = text.replace("Q / 'TRANSFER-MANIFEST.json'", 'SOURCE_BASELINE')
text = text.replace('320b5dcc8bb807fad97b46a34faf8be25ed55423afa5d8e81d977947a02d4163', sha(R/'PROFILE-CREATION-PROPOSAL-AC6.json'))
text = text.replace("['payloads']", "['source352']").replace("len(FROZEN) == 295, 'CANDIDATE295_REQUIRED'", "len(FROZEN) == 352, 'SOURCE352_EXECUTION_VIEW_REQUIRED'")
text = text.replace("['after_hashes']", "['source352']").replace("len(pins) == 290, 'SOURCE290_REQUIRED'", "len(pins) == 352, 'SOURCE352_REQUIRED'")
text = replace(text, "return {relative: capture(F / relative, pin)[1] for relative, pin in pins.items()}", "return {relative: capture(F / relative, facts['sha256'], facts['native_identity'])[1] for relative, facts in pins.items()}")
text = text.replace('Source290_native_and_hash_conserved', 'Source352_native_and_hash_conserved').replace('candidate295_native_and_hash_conserved', 'execution_source352_native_and_hash_conserved')
text = replace(text, "('profile-qualification-' + uuid.uuid4().hex)", "('q-' + uuid.uuid4().hex)")
path_functions = r'''
def _native_path(path, *, directory):
    """Observe one owned ordinary path; the existing API retains handle cleanup."""
    path = fs.safe_components(Path(path))
    require(path.is_relative_to(R), 'OWNED_PROBE_PATH_REQUIRED')
    info = fs.lstat(path)
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and not fs.reparse(info), 'ORDINARY_PROBE_PATH_REQUIRED')
    api, primary = module._IsolationAPI(), None
    try:
        handle = api.CreateFileW(str(path), 0x80, 3, None, 3,
                                0x00200000 | (0x02000000 if directory else 0), None)
        require(handle not in (None, 0, module.INVALID_HANDLE), 'PROBE_PATH_HANDLE_UNAVAILABLE')
        api.queue_handle(handle)
        return api.native_volume_path(handle)
    except BaseException as error:
        primary = error
        raise
    finally:
        module._finish_cleanup(api, primary)

def check_launch_paths(directory, image=None):
    base = _native_path(directory, directory=True)
    predicted = image is None
    native_directory = base + '\\native-fixtures\\ac1-' + '0' * 32 if predicted else base
    native_image = native_directory + '\\assets\\isolated_worker.exe' if predicted else _native_path(image, directory=False)
    require(len(native_directory) < 258 and len(native_image) < 258, 'PROBE_NATIVE_PATH_TOO_LONG')
    facts = {'at': now(), 'native_directory': native_directory, 'native_image': native_image,
             'native_directory_length': len(native_directory), 'native_image_length': len(native_image),
             'predicted_fixture_suffix': predicted, 'limit_exclusive': 258,
             'qualification_claim': False, 'missing_profile_causality_claim': False}
    save(Path(directory) / ('PATH-LAYOUT.json' if predicted else 'LAUNCH-PATHS.json'), facts)
    return facts

'''
text = replace(text, 'def prepare_probe(directory, owned_identity=None):', path_functions+'def prepare_probe(directory, owned_identity=None):')
text = replace(text, "    driver_payload = body.encode('utf-8')", "    check_launch_paths(directory)\n    probe_needle = '    control, api = _ControlApi(), _IsolationAPI()\\n'\n    require(body.count(probe_needle) == 1, 'PROBE_PATH_GUARD_BINDING_CHANGED')\n    body = body.replace(probe_needle, '    check_launch_paths(fixture, image)\\n' + probe_needle)\n    driver_payload = body.encode('utf-8')")
text = replace(text, "    helper.__file__ = str(directory / 'native_fixture_support.py')", "    helper.__file__ = str(directory / 'native_fixture_support.py')\n    helper.check_launch_paths = check_launch_paths")
text = replace(text, "            'Verify copied fixture image equals IMAGE',", "            'Check projected native path lengths before profile creation; actual native paths before launch',\n            'Verify copied fixture image equals IMAGE',")
runtime = F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
runtime_cfg = runtime.parent.parent/'pyvenv.cfg'
text = replace(text, 'manifest_payload, _ = capture(SOURCE_BASELINE, MANIFEST)',
    "capture(PY, '"+sha(runtime)+"')\ncapture(PY.parent.parent / 'pyvenv.cfg', '"+sha(runtime_cfg)+"')\nmanifest_payload, _ = capture(SOURCE_BASELINE, MANIFEST)")
ast.parse(text)
write('profile_qualification.py', text)
wrapper_old = (A/'run_one_approved_attempt_v2.py').read_text()
wrapper = wrapper_old.replace('ac5-profile-tool-20261015','ac6-profile-preparation-20261018').replace('PROFILE-CREATION-PROPOSAL-AC5.json','PROFILE-CREATION-PROPOSAL-AC6.json')
wrapper = wrapper.replace('530238cbb5d5601802e96864a085a4d4becb0d0d045e3bf13286b5718b7d9a6e',sha(R/'profile_qualification.py')).replace('320b5dcc8bb807fad97b46a34faf8be25ed55423afa5d8e81d977947a02d4163',sha(R/'PROFILE-CREATION-PROPOSAL-AC6.json'))
wrapper = wrapper.replace("R.glob('profile-qualification-*')", "R.glob('q-*')").replace('ac5_single_attempt_preflight','ac6_single_attempt_preflight').replace('len(source) == 290 and len(candidate) == 295', 'len(source) == 352 and len(candidate) == 352').replace("'Source290': source, 'candidate295': candidate", "'Source352': source, 'execution_source352': candidate")
ast.parse(wrapper)
write('run_one_approved_attempt_v2.py',wrapper)
write('tool-delta.diff',''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='AC5/profile_qualification.py',tofile='AC6/profile_qualification.py')))
write('wrapper-delta.diff',''.join(difflib.unified_diff(wrapper_old.splitlines(True),wrapper.splitlines(True),fromfile='AC5/run_one_approved_attempt_v2.py',tofile='AC6/run_one_approved_attempt_v2.py')))
print(json.dumps({'prepared':str(R),'tool_sha256':sha(R/'profile_qualification.py'),'wrapper_sha256':sha(R/'run_one_approved_attempt_v2.py'),'proposal_sha256':sha(R/'PROFILE-CREATION-PROPOSAL-AC6.json'),'executed_qualification':False}))

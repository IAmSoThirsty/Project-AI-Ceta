"""Prepare an immutable AC7 successor. No native API or approval is invoked."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/ac7-token-contract-20261020'
OLD = F / '.agents/runtime/ac6-profile-preparation-20261018'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()


def save(path, value):
    with path.open('x', encoding='utf8', newline='\n') as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write('\n')


def write(path, text):
    with path.open('x', encoding='utf8', newline='\n') as output:
        output.write(text)


reader = F / '.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(reader) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec = importlib.util.spec_from_file_location('ac7_preparation_reader', reader)
fs = importlib.util.module_from_spec(spec); sys.modules[spec.name] = fs; spec.loader.exec_module(fs)


def capture(path, expected=None):
    fs.safe_components(path)
    before = fs.file_identity(fs.lstat(path))
    payload = fs.read_bytes(path)
    after = fs.file_identity(fs.lstat(path))
    assert before == after and len(payload) == before['bytes']
    digest = hashlib.sha256(payload).hexdigest()
    assert expected is None or digest == expected
    return dict(sha256=digest, native_identity=after)


applied = F / '.agents/runtime/js8-20261015/amendment-report1/active-application/APPLIED.json'
capture(applied, 'b22b2f404a8373be3eb7bcd2ab9c974f5dba187aed2c787fb62f54fac7508a87')
source = json.loads(applied.read_bytes())['source352']
assert len(source) == 352
for name, facts in source.items():
    assert capture(F / name, facts['sha256']) == dict(sha256=facts['sha256'], native_identity=facts['native_identity'])
candidate = {name: capture(Q / name) for name in source}
baseline = R / 'CANDIDATE-BASELINE-R2.json'
save(baseline, dict(schema='ceta-ac7-candidate-native-cut-v1', at=now(), root=str(Q),
    source_cut=dict(path=str(applied), sha256=sha(applied)), candidate352=candidate,
    source_publication=False, host_profile_operations=False))

build = R / 'build-r2/BUILD.json'
built = json.loads(build.read_bytes())
image = Path(built['native_image']['path'])
image_facts = capture(image, built['native_image']['sha256'])
assert built['pure_tests'] == 5 and built['source']['sha256'] == sha(Q / 'native/windows_broker/isolated_worker.rs')
oracle = Q / 'tools/isolated_worker_token_oracle.py'
oracle_facts = capture(oracle)
assert sha(OLD / 'profile_qualification.py') == 'a7a86f8164df9d1c2a4de37503bd5476cab28c35333630ba0b8e56a6bf3dc061'
proposal = json.loads((OLD / 'PROFILE-CREATION-PROPOSAL-AC6.json').read_bytes())
proposal.update(at=now(), schema='ceta-ac7-profile-proposal-v1',
    status='PREPARED_REQUIRES_DISTINCT_REVIEW_AND_NEW_EXPLICIT_HUMAN_APPROVAL',
    candidate_manifest=dict(path=str(baseline), sha256=sha(baseline)),
    native_image_sha256=image_facts['sha256'],
    native_build_receipt=dict(path=str(build), sha256=sha(build)),
    execution_source=str(Q / 'src'), source_publication_required_before_application_acceptance=True,
    change='Capture raw restriction BOOL, immediate error and independent restricting SID count in both processes; require typed agreement. Preserve every real denial probe and retirement guard.',
    token_predicates_changed=True,
    old_failed_predicate='AC6 measured IsTokenRestricted false without immediate error/count. Cause unresolved.',
    current_isolation_sha256=sha(Q / 'src/ceta/supervisor/isolated_worker.py'),
    current_jobs_sha256=sha(Q / 'src/ceta/supervisor/windows_jobs.py'),
    token_oracle=dict(path=str(oracle), **oracle_facts),
    prior_tool=dict(path=str(OLD / 'profile_qualification.py'), sha256=sha(OLD / 'profile_qualification.py')),
    prior_approved_attempt=dict(path=str(F / '.agents/runtime/ac6-readiness-20261020/EXECUTION-RESULT.json'),
        sha256=sha(F / '.agents/runtime/ac6-readiness-20261020/EXECUTION-RESULT.json')),
    prior_approval_used=True, approval_record_created=False,
    source_versions=dict(source352=sha(applied), ac7_candidate352=sha(baseline)),
    skills_used=['thirsty-work-orchestrator', 'unfinished-work-recovery', 'protocol-interoperability-auditor', 'rea'],
    governing_version='thirsty-constitution-v0.1')
proposal.pop('prior_distinct_review', None)
proposal.pop('prior_denials', None)
proposal['prior_native_path_failures_preserved_in_ac6_proposal'] = dict(
    path=str(OLD / 'PROFILE-CREATION-PROPOSAL-AC6.json'), sha256=sha(OLD / 'PROFILE-CREATION-PROPOSAL-AC6.json'))
proposal_path = R / 'PROFILE-CREATION-PROPOSAL-AC7.json'
save(proposal_path, proposal)

text = (OLD / 'profile_qualification.py').read_text(encoding='utf8')


def replace(old, new, count=1):
    global text
    assert text.count(old) == count, (old[:100], text.count(old))
    text = text.replace(old, new)


replace("R = Path(__file__).resolve().parent\nORIGINAL_R = F / '.agents/runtime/ac5-profile-tool-20261015'\nassert R == F / '.agents/runtime/ac6-profile-preparation-20261018'\nQ = F  # The execution view is the canonical published source, not a private candidate.",
    "R = F / '.agents/runtime/ac7-token-contract-20261020'\nQ = F / '.agents/ac7-token-contract-20261020'\nassert Path(__file__).resolve() == Q / 'tools/qualify_isolated_worker.py'\nCANDIDATE_BASELINE = R / 'CANDIDATE-BASELINE-R2.json'")
replace("MANIFEST = 'b22b2f404a8373be3eb7bcd2ab9c974f5dba187aed2c787fb62f54fac7508a87'", 'MANIFEST = ' + repr(sha(baseline)))
replace("IMAGE = '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'", 'IMAGE = ' + repr(image_facts['sha256']))
replace("PROPOSAL = R / 'PROFILE-CREATION-PROPOSAL-AC6.json'", "PROPOSAL = R / 'PROFILE-CREATION-PROPOSAL-AC7.json'")
start, end = text.index('DEPENDENCIES = '), text.index('\n\ndigest =')
dependencies = None
old_spec = __import__('ast').parse(text)
for node in old_spec.body:
    if isinstance(node, __import__('ast').Assign) and any(isinstance(t, __import__('ast').Name) and t.id == 'DEPENDENCIES' for t in node.targets):
        dependencies = __import__('ast').literal_eval(node.value)
assert type(dependencies) is dict
old_image = '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
dependencies.pop(old_image)
image_name = image.relative_to(F).as_posix()
dependencies[image_name] = image_facts
for name, facts in dependencies.items(): assert capture(F / name, facts['sha256']) == facts
text = text[:start] + 'DEPENDENCIES = ' + repr(dependencies) + text[end:]
replace("manifest_payload, _ = capture(SOURCE_BASELINE, MANIFEST)", 'manifest_payload, _ = capture(CANDIDATE_BASELINE, MANIFEST)')
replace("capture(PROPOSAL, 'aa849834a68cd670928ea8f17dc446a50354442b2dbd658ed8889c0cdc982f49')", 'capture(PROPOSAL, ' + repr(sha(proposal_path)) + ')')
replace("FROZEN = json.loads(manifest_payload.decode('utf-8-sig'))['source352']", "FROZEN = json.loads(manifest_payload.decode('utf-8-sig'))['candidate352']")
replace("require(len(FROZEN) == 352, 'SOURCE352_EXECUTION_VIEW_REQUIRED')", "require(len(FROZEN) == 352, 'CANDIDATE352_EXECUTION_VIEW_REQUIRED')")
replace("sys.path.insert(0, str(Q / 'src'))", """# A dormant import may not silently reuse a foreign project's CETA modules.
for loaded_name, loaded_module in tuple(sys.modules.items()):
    if loaded_name == 'ceta' or loaded_name.startswith('ceta.'):
        loaded_file = getattr(loaded_module, '__file__', None)
        require(type(loaded_file) is str and Path(loaded_file).resolve().is_relative_to(Q / 'src'),
                'FOREIGN_CETA_MODULE_REFUSED')
sys.path.insert(0, str(Q / 'src'))""")
replace('from ceta.supervisor.windows_jobs import WindowsOwnedProcess',
    'from ceta.supervisor.windows_jobs import WindowsOwnedProcess\n'
    + 'oracle_payload, _ = capture(' + repr(str(oracle)) + ', ' + repr(oracle_facts['sha256']) + ', ' + repr(oracle_facts['native_identity']) + ')\n'
    + "oracle = types.ModuleType('ac7_captured_token_oracle')\n"
    + 'oracle.__file__ = ' + repr(str(oracle)) + '\n'
    + "exec(compile(oracle_payload, oracle.__file__, 'exec'), oracle.__dict__)")
replace('    capture(SOURCE_BASELINE, MANIFEST)', '    capture(CANDIDATE_BASELINE, MANIFEST)')
replace("    image_name = '" + old_image + "'", '    image_name = ' + repr(image_name))
start, end = text.index('def assert_isolation(result):'), text.index('\n\ndef describe(error):')
text = text[:start] + 'def assert_isolation(result):\n    oracle.assert_isolation(result, SID)' + text[end:]
replace("'appcontainer_sid', 'integrity_rid', 'is_token_restricted', 'observed_monotonic_ns'}", "'appcontainer_sid', 'integrity_rid', 'is_token_restricted', 'observed_monotonic_ns',\n                'restriction_raw_result', 'restriction_last_error', 'restricted_sid_count', 'restriction_query_bytes'}")
replace("measured.get('schema') == 'ceta-rejected-isolation-token-v1'", "measured.get('schema') == 'ceta-rejected-isolation-token-v2'")
replace("'execution_source352_native_and_hash_conserved'", "'candidate352_native_and_hash_conserved'")
replace("def qualify(approval_path, approval_sha):\n    validate_operator_record(approval_path, approval_sha)\n    return _QualificationRun(R / ('q-' + uuid.uuid4().hex), approval_sha).execute()", """def qualify(approval_path, approval_sha):
    validate_operator_record(approval_path, approval_sha)
    # The entry point itself consumes the one attempt. Reusing the CLI or the
    # same approval after failure cannot launch a second qualification.
    marker = read(R / 'ONE-ATTEMPT-STARTED.json')
    require(marker['actual_approval_sha256'] == approval_sha and marker['tool_sha256'] == sha(Path(__file__)),
            'EXACT_REVIEWED_ATTEMPT_MARKER_REQUIRED')
    review_payload, _ = capture(Path(marker['review_path']), marker['review_sha256'])
    reviewed = json.loads(review_payload.decode('utf-8-sig'))
    require(reviewed['decision'] == 'approved' and reviewed['tool_sha256'] == sha(Path(__file__))
            and reviewed['proposal_sha256'] == sha(PROPOSAL)
            and reviewed['wrapper_sha256'] == sha(Q / 'tools/run_one_isolation_qualification.py')
            and type(reviewed['reviewer']) is str and reviewed['reviewer'] not in ('', '/root'),
            'DISTINCT_EXACT_REVIEW_REQUIRED')
    require(not list(R.glob('q-*')), 'PRIOR_QUALIFICATION_DIRECTORY_REFUSED')
    save(R / 'EXECUTION-CLAIM.json', {'at': now(), 'approval_sha256': approval_sha,
        'tool_sha256': sha(Path(__file__)), 'review_sha256': marker['review_sha256'], 'automatic_retry': False})
    return _QualificationRun(R / ('q-' + uuid.uuid4().hex), approval_sha).execute()""")
tool = Q / 'tools/qualify_isolated_worker.py'
write(tool, text)

wrapper = (OLD / 'run_one_approved_attempt_v2.py').read_text(encoding='utf8')
wrapper = wrapper.replace("F = Path('T:/00-Active/Project-AI-CETA'); R = Path(__file__).resolve().parent",
    "F = Path('T:/00-Active/Project-AI-CETA'); R = F / '.agents/runtime/ac7-token-contract-20261020'\nQ = F / '.agents/ac7-token-contract-20261020'")
wrapper = wrapper.replace("assert R == F / '.agents/runtime/ac6-profile-preparation-20261018'", "assert Path(__file__).resolve() == Q / 'tools/run_one_isolation_qualification.py'")
wrapper = wrapper.replace("tool = R / 'profile_qualification.py'", "tool = Q / 'tools/qualify_isolated_worker.py'")
wrapper = wrapper.replace('a7a86f8164df9d1c2a4de37503bd5476cab28c35333630ba0b8e56a6bf3dc061', sha(tool))
wrapper = wrapper.replace('PROFILE-CREATION-PROPOSAL-AC6.json', 'PROFILE-CREATION-PROPOSAL-AC7.json')
wrapper = wrapper.replace('aa849834a68cd670928ea8f17dc446a50354442b2dbd658ed8889c0cdc982f49', sha(proposal_path))
wrapper = wrapper.replace("assert not (R / 'ONE-ATTEMPT-STARTED.json').exists()", "assert not (R / 'EXECUTION-CLAIM.json').exists() and not (R / 'ONE-ATTEMPT-STARTED.json').exists()")
wrapper = wrapper.replace("reviewed['decision'] == 'approved' and reviewed['tool_sha256'] == sha(tool)",
    "reviewed['decision'] == 'approved' and reviewed['tool_sha256'] == sha(tool) and reviewed['proposal_sha256'] == sha(module.PROPOSAL) and reviewed['wrapper_sha256'] == sha(Path(__file__)) and type(reviewed['reviewer']) is str and reviewed['reviewer'] not in ('', '/root')")
wrapper = wrapper.replace("'review_sha256': review_sha, 'review_native_identity': review_identity,", "'review_path': str(review), 'review_sha256': review_sha, 'review_native_identity': review_identity,")
wrapper = wrapper.replace("'execution_source352': candidate", "'candidate352': candidate")
wrapper_path = Q / 'tools/run_one_isolation_qualification.py'
write(wrapper_path, wrapper)
save(R / 'TOOL-PREPARATION-R2.json', dict(at=now(), candidate352=sha(baseline),
    tool=dict(path=str(tool), sha256=sha(tool)), wrapper=dict(path=str(wrapper_path), sha256=sha(wrapper_path)),
    proposal=dict(path=str(proposal_path), sha256=sha(proposal_path)), oracle=dict(path=str(oracle), **oracle_facts),
    image=dict(path=str(image), **image_facts), host_profile_operations=[], worker_launches=[],
    actual_operator_approval=None, source_publication=False))
print(json.dumps(dict(prepared=True, tool_sha256=sha(tool), proposal_sha256=sha(proposal_path),
    host_profile_operations=False, worker_launches=False)), flush=True)

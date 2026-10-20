"""Read existing AC3 execution evidence; no profile/native launch/test execution."""
from pathlib import Path
import ast, hashlib, json, re, subprocess, sys

P = Path('T:/00-Active/Project-AI-CETA')
R = P / '.agents/runtime/ac3-20261014/profile-tool'
D = R / 'collaborative-review-20261015'
Q = P / '.agents/ac3-20261014'
A = R / 'profile-qualification-a82d795283474f5daa218f8c158d5047'
N = R / 'approved-no-profile-13b4cd2a9c00471f91340cb3a9f017e8'
FIX = A / 'native-fixtures/ac1-440c60f8ebcf48edb7c7f1105a1a69a4'
sys.path.insert(0, str(P / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q = Q; s.R = D
started = s.utc()
read = lambda path: json.loads(Path(path).read_text(encoding='utf-8-sig'))
def slim(path):
    observed = s.ordinary(path)
    return {'sha256':observed['sha256'], 'native_identity':observed['native_identity']}
def reference(path): return s.reference(Path(path))
def facts_tree(root):
    result = {}
    pending = [root]
    while pending:
        current = pending.pop()
        for path in current.iterdir():
            info = s.fs.lstat(path)
            assert not s.fs.reparse(info), ('Unexpected reparse member', str(path))
            if path.is_dir(): pending.append(path)
            elif path.is_file(): result[str(path.relative_to(P))] = s.ordinary(path)
            else: raise AssertionError(('Unexpected nonordinary member', str(path)))
    return result

assert s.sha(R/'profile_qualification.py') == '8d3ce66b6ac17d2774f4c11a8852b23b45e41218df887f6b18c99ac0add05414'
assert s.sha(R/'ACTUAL-OPERATOR-APPROVAL.json') == '3401d05d82ee4bcfe6bf62c21f2fb84324261bd78cbaf2761848d322e22ed4b5'
assert s.sha(Q/'TRANSFER-MANIFEST.json') == '274fbd34857409e54ef04991b4ba424332a58b87f553a2a1409bea64ff52c60b'
assert not (P/'.agents/cpb1-20261014').exists() and not (P/'.agents/runtime/cpb1-20261014').exists()
top_names = ('ACTUAL-OPERATOR-APPROVAL.json','APPROVED-PREFLIGHT.json','APPROVED-QUALIFICATION.json',
    'APPROVED-QUALIFICATION.stdout','APPROVED-QUALIFICATION.stderr','execute_approved_qualification.py',
    'profile_qualification.py','PROFILE-CREATION-PROPOSAL-AC3.json','ROOT-REVIEW.json',
    'PREPARED-TOOL.json','run_approved_no_profile_regression.py')
prior = {str((R/name).relative_to(P)):s.ordinary(R/name) for name in top_names}
prior.update(facts_tree(A)); prior.update(facts_tree(N))
approval = read(R/'ACTUAL-OPERATOR-APPROVAL.json')
proposal = read(R/'PROFILE-CREATION-PROPOSAL-AC3.json')
qualified = read(R/'APPROVED-QUALIFICATION.json')
pre = read(R/'APPROVED-PREFLIGHT.json')
before = read(A/'BEFORE.json')
create = read(A/'CREATE-RETURN.json')
created = read(A/'CREATED.json')
retirement = read(A/'RETIREMENT.json')
delete_intent = read(A/'DELETE-INTENT.json')
delete = read(A/'DELETE-RETURN.json')
post = read(A/'POST-DELETE-OBSERVATION.json')
actual = read(A/'RESULT.json')
native = read(FIX/'native-profile-r2.json')
regression = read(N/'RESULT.json')
regression_pre = read(N/'PREFLIGHT.json')
bindings = read(A/'PROBE-BINDING.json')
manifest = read(Q/'TRANSFER-MANIFEST.json')

assert approval['human_reply'] == approval['latest_plain_text_confirmation'] == 'Approve this exact AC3 attempt, own-profile cleanup, and bounded post-cleanup denial regression'
assert approval['repeated_confirmation_is_same_single_attempt'] is True
assert approval['additional_profile_creation_authorized'] is False
assert approval['prepared_script_sha256'] == qualified['tool_sha256'] == s.sha(R/'profile_qualification.py')
assert approval['proposal_sha256'] == s.sha(R/'PROFILE-CREATION-PROPOSAL-AC3.json')
assert qualified['approval_sha256'] == s.sha(R/'ACTUAL-OPERATOR-APPROVAL.json')
assert qualified['exit_status'] == 1 and qualified['automatic_retry'] is False
assert qualified['stdout_sha256'] == s.sha(R/'APPROVED-QUALIFICATION.stdout')
assert qualified['stderr_sha256'] == s.sha(R/'APPROVED-QUALIFICATION.stderr')
assert len(list(R.glob('profile-qualification-*'))) == len(list(R.glob('approved-no-profile-*'))) == 1
assert before['prior_folder']['path'] is None and before['prior_folder']['HRESULT'] in (-2147024894,-2147024893)
assert create['HRESULT'] == created['HRESULT'] == 0 and create['created_this_run']
assert created['actual_SID'] == approval['profile_sid'] == proposal['SID']
assert created['capabilities'] == [] and not create['unknown_output_pointer']
assert delete_intent['created_this_run_receipt_sha256'] == s.sha(A/'CREATED.json')
assert delete_intent['retirement_receipt_sha256'] == s.sha(A/'RETIREMENT.json')
assert delete['HRESULT'] == post['native_delete_HRESULT'] == 0
assert post['folder_observation']['path'] is None
assert post['folder_observation']['HRESULT'] == -2147024894
assert post['cleanup_status'] == actual['profile_cleanup_status'] == 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'
assert actual['primary_failure'] == {'type':'ContractError','text':'ISOLATION_TOKEN_NOT_QUALIFIED at $'}
assert not actual['positive_isolation_qualified'] and not actual['canonical_real_effect_accepted']
assert native['failure'] == actual['primary_failure']['text'] and native['raw_stdout'] == ''
assert 'facts' not in native and 'worker_exit_code' not in native
expected_lifetimes = {(29416,134365235213297489),(21816,134365235221305618)}
assert {(row['pid'],row['creation_time']) for row in retirement['custody']} == expected_lifetimes
assert all(all(row[k] is True for k in ('lifetime_closed','job_closed','process_closed','thread_closed')) for row in retirement['custody'])
assert len(retirement['pending_native_resources']) == 20 and not any(retirement['pending_native_resources'])
assert retirement['unknown_create_output_pointer'] is None and retirement['all_captured_resources_retired']
assert not any(actual['retirement']['post_delete_API_resources'])
assert actual['retirement']['all_captured_resources_retired_after_final_observation']
assert not actual['journal_errors']
assert native['cleanup'] == [{'kind':'trusted_medium_fixture','pid':29416,'creation_time':134365235213297489,
    'exit_code':125,'active_processes':0,'lifetime_closed':True}]

source_before = read(A/'SOURCE-BEFORE.json'); source_after = read(A/'SOURCE-AFTER.json')
candidate_before = read(A/'CANDIDATE-BEFORE.json'); candidate_after = read(A/'CANDIDATE-AFTER.json')
assert len(source_before) == 290 and source_before == source_after == pre['Source290']
assert len(candidate_before) == 294 and candidate_before == candidate_after == pre['candidate294']
assert source_before == regression['Source_before'] == regression['Source_after']
assert candidate_before == regression['candidate_before'] == regression['candidate_after']
assert all(slim(P/name) == row for name,row in source_before.items())
assert all(slim(Q/name) == row for name,row in candidate_before.items())
assert manifest['payloads'] == candidate_before

assert regression['tests_run'] == 1 and regression['failures'] == regression['errors'] == regression['skips'] == 0
assert regression['expected_ids'] == regression['executed_ids'] == regression['stopped_ids']
assert regression['exit_status'] == 0 and not regression['profile_Create_Delete_calls']
assert not any(regression['pending_native_resources']) and not regression['remaining_new_threads']
assert regression['all_recorded_lifetimes_closed']
assert regression['native_lifetimes'] == [{'pid':21952,'creation_time':134365236930495967,
    'lifetime_closed':True,'process_closed':True,'job_closed':True,'thread_closed':True}]
assert all(regression[name]['prior_folder']['path'] is None and regression[name]['prior_folder']['HRESULT'] == -2147024894
           for name in ('profile_absence_before','profile_absence_after'))
assert regression['raw_sha256'] == s.sha(N/'raw.txt')
assert actual['at'] < regression_pre['fresh_reserved_profile_absence']['observed_at'] < regression['started_at'] < regression['finished_at']
method_name = 'test_actual_nonpersistent_launch_denial_and_medium_control_retirement'
test_source = Q/'tests/contract/test_isolated_worker.py'
method = next(node for node in ast.walk(ast.parse(test_source.read_text()))
              if isinstance(node,ast.FunctionDef) and node.name == method_name)
ast_sha = hashlib.sha256(ast.dump(method,include_attributes=False).encode()).hexdigest()
assert ast_sha == regression_pre['original_test_method_AST_sha256']
regex = next(node.value for node in ast.walk(method) if isinstance(node,ast.Constant)
             and node.value == 'ISOLATION_RESTRICTED_CREATE_FAILED:2')
raw = (N/'raw.txt').read_text()
actual_error = re.search(r'ISOLATION_RESTRICTED_CREATE_FAILED:[0-9]+',raw).group()
assert actual_error == 'ISOLATION_RESTRICTED_CREATE_FAILED:267'
assert re.search(regex,actual_error) and not re.fullmatch(regex,actual_error)

tool_tree = ast.parse((R/'profile_qualification.py').read_text())
dependencies = next(ast.literal_eval(node.value) for node in tool_tree.body
    if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='DEPENDENCIES' for target in node.targets))
assert dependencies == bindings['captured_dependencies']
assert all(slim(P/name) == row for name,row in dependencies.items())
helper = P/'.agents/runtime/ac1-20261014/native_fixture_support.py'
driver = helper.read_text().replace('\r\n','\n')
needle = "    name = 'CETA.AC1.' + uuid.uuid4().hex\n"
assert driver.count(needle) == 1
driver = driver.replace(needle, '    name = ' + repr(proposal['name']) + '\n')
copy_needle = '    fs.write_new(image, fs.read_bytes(original))\n'
driver = driver.replace(copy_needle,copy_needle+'    assert sha(image) == '+repr(proposal['native_image_sha256'])+'\n')
driver = driver.replace('expected_image_sha256=sha(image)','expected_image_sha256='+repr(proposal['native_image_sha256']))
assert (A/'native_fixture_support.py').read_bytes() == driver.encode('utf-8')
assert slim(A/'native_fixture_support.py') == bindings['driver_copy']
assert slim(A/'ac3_support.py') == bindings['support_copy']
assert slim(A/'build-r2/isolated_worker.exe') == bindings['image_copy']
assert slim(FIX/'assets/isolated_worker.exe') == native['setup']['image'].__class__(
    (name,value) for name,value in native['setup']['image'].items() if name in ('sha256','native_identity'))
build_path = P/'.agents/runtime/ac1-20261014/build-r2/build.json'
build = read(build_path)
assert build['exit_status'] == 0
assert s.ordinary(Path(build['source']['path'])) == build['source']
assert s.ordinary(Path(build['native_image']['path'])) == build['native_image']
assert s.ordinary(Path(build['actual_rustc']['path'])) == build['actual_rustc']
assert s.ordinary(Path(build['resolved_rustup_command_image']['path'])) == build['resolved_rustup_command_image']
assert s.sha(Q/'native/windows_broker/isolated_worker.rs') == build['source']['sha256']
assert build['native_image']['sha256'] == proposal['native_image_sha256']

acl = [json.loads(line) for line in (FIX/'ACL-OPERATIONS.jsonl').read_text().splitlines()]
assert all(Path(row['path']).is_relative_to(FIX) and row['error']==0 for row in acl)
launcher_source = (Q/'src/ceta/supervisor/isolated_worker.py').read_text()
assert launcher_source.index('owned.launch_token_facts = api.token_facts') < launcher_source.index('api.ResumeThread(owned._thread)')
executor = (R/'execute_approved_qualification.py').read_text()
assert "assert not list(R.glob('profile-qualification-*'))" in executor
regression_executor = (R/'run_approved_no_profile_regression.py').read_text()
assert "assert not list(R.glob('approved-no-profile-*'))" in regression_executor
assert 'PROFILE_MUTATION_FORBIDDEN_IN_DENIAL_REGRESSION' in regression_executor
assert all(s.ordinary(P/name) == row for name,row in prior.items())
assert all(slim(P/name) == row for name,row in source_before.items())
assert all(slim(Q/name) == row for name,row in candidate_before.items())

report = dict(
    started_at=started,finished_at=s.utc(),reviewer=s.ACTOR,execution_author='/root',
    decision='accepted_as_failed_qualification_and_bounded_denial_cleanup_evidence',exit_status=0,
    positive_isolation_qualified=False,canonical_real_effect_accepted=False,
    actual_qualification_exit_status=1,existing_regression_exit_status=0,
    scope='Read-only Collaborative Review of the exact completed approved AC3 attempt and its existing original no-profile regression; no new native/profile/test execution.',
    approval=reference(R/'ACTUAL-OPERATOR-APPROVAL.json'),tool=reference(R/'profile_qualification.py'),
    approval_transport='Root-preserved actual human engineering reply; not a runtime identity credential or CETA authority grant.',
    permission_dedup=dict(attempts_observed=1,existing_regressions_observed=1,
        repeated_confirmation_same_attempt=True,wrapper_refuses_existing_attempt_directory=True,
        regression_wrapper_refuses_prior_run=True,additional_profile_creation_authorized=False,
        limit='Observed wrapper execution is single-attempt. This read-only review does not claim the data receipt is an unforgeable or independently consumed runtime credential, nor that the generic qualification CLI cryptographically enforces one use.'),
    verified_findings=[
        dict(id='AC3-EXEC-V01',finding='Exact tool and approval hashes bind the executed one-attempt command; recorded process exit1 is preserved.',evidence=[reference(R/'APPROVED-QUALIFICATION.json'),reference(R/'APPROVED-QUALIFICATION.stdout')]),
        dict(id='AC3-EXEC-V02',finding='Native profile Create returned0 with the exact requested SID; token qualification then denied. Raw child output contains no positive isolation facts.',evidence=[reference(A/'CREATE-RETURN.json'),reference(A/'CREATED.json'),reference(FIX/'native-profile-r2.json')]),
        dict(id='AC3-EXEC-V03',finding='Inspected launcher qualifies token before ResumeThread; failure is on that path. No independent native API trace of ResumeThread was recorded, so the boundary is code-correlated rather than a separate live trace.',evidence=[reference(Q/'src/ceta/supervisor/isolated_worker.py'),reference(FIX/'native-profile-r2.json')]),
        dict(id='AC3-EXEC-V04',finding='Both captured process/job/thread lifetimes closed;20 native API pending-resource lists empty, no unknown create pointer. Deletion was bound to exact created and retirement receipt hashes.',evidence=[reference(A/'RETIREMENT.json'),reference(A/'DELETE-INTENT.json')]),
        dict(id='AC3-EXEC-V05',finding='Own profile Delete returned0; subsequent folder query returned0x80070002/no path, then the later no-profile regression separately observed absence before and after. This is the recorded bounded absence observation, not proof of perfect registry/storage erasure or a new query at review time.',evidence=[reference(A/'DELETE-RETURN.json'),reference(A/'POST-DELETE-OBSERVATION.json'),reference(N/'RESULT.json')]),
        dict(id='AC3-EXEC-V06',finding='Original one-case regression has matching expected/executed/stopped IDs, zero failures/errors/skips, retired medium controlPID21952, no profile Create/Delete calls and no pending API resources/new threads.',evidence=[reference(N/'PREFLIGHT.json'),reference(N/'RESULT.json'),reference(N/'raw.txt')]),
        dict(id='AC3-EXEC-V07',finding='Source290 and AC3candidate294 recorded native identities/hashes match before/after, both execution records, and current independent native rehash.',evidence=[reference(A/'SOURCE-BEFORE.json'),reference(A/'SOURCE-AFTER.json'),reference(A/'CANDIDATE-BEFORE.json'),reference(A/'CANDIDATE-AFTER.json'),reference(N/'RESULT.json')]),
        dict(id='AC3-EXEC-V08',finding='Original Rust source/image/build receipt/toolchain images and copied worker bytes match their pins; transformed captured Python helper is exactly derivable from the declared profile/image transformations.',evidence=[reference(build_path),reference(A/'PROBE-BINDING.json')])
    ],
    qualification=dict(profile_create_hresult=0,profile_delete_hresult=0,
        failure=actual['primary_failure'],native_lifetimes=retirement['custody'],
        pending_API_owner_lists=20,pending_API_resources=0,
        last_recorded_profile_absence=regression['profile_absence_after']['observed_at'],
        worker_token_predicate_cause='UNESTABLISHED: aggregate token contract denied; raw measured failed-field values are absent.'),
    regression=dict(test_id=regression['expected_ids'][0],test_method_ast_sha256=ast_sha,
        tests_run=1,failures=0,errors=0,skips=0,actual_error=actual_error,
        original_regex=regex,prefix_matches_267=True,exact_error_2_verified=False,
        proof='Bounded restrictive launch denial, no positive facts and closed medium-control lifetime. Missing-profile causal explanation is unestablished.'),
    issues=[dict(id='AC3-EXEC-F01',classification='requires separate follow-up work; not blocking this correctly qualified evidence review',
        file=str(test_source),line=369,issue='Unanchored :2 assertion also accepts actual :267 and other longer decimal codes beginning2.',
        effect='The original passing test cannot support an exact error2 or a causal missing-profile claim.',
        next_executable_path='In a new reviewed test successor, explicitly separate generic bounded-denial/cleanup assertions from exact observed-code assertions and causal diagnosis; preserve historical raw evidence and require new authorization before another actual native launch.')],
    unresolved=[
        'Positive restrictive token/access/handle/network/isolation qualification is blocked by the observed token contract denial.',
        'Exact failing token field/root cause and error267 causality remain unestablished from captured raw evidence.',
        'No new profile/launch attempt or host query was executed by this reviewer; observed absence/retirement are tied to recorded execution times.',
        'No full product acceptance, CETA runtime approval/Hello or consequential CPU effect follows from these operator engineering records.'
    ],
    compiler=dict(build_receipt=reference(build_path),source=build['source'],image=build['native_image'],
        actual_rustc=build['actual_rustc'],rustup=build['resolved_rustup_command_image'],
        version_output=build['version_output'],new_build_executed=False),
    conservation=dict(Source290_exact=True,candidate294_exact=True,prior_execution_files_exact=len(prior),
        prior_files=prior,profile_or_worker_created_by_reviewer=False,Source_mutation=False,
        old_evidence_mutation=False,new_tests_run=0,CPB1_scopes_absent=True),
    command_argv=[str(s.PY),'-B','-X','utf8',str(Path(__file__))],
    method='Native ordinary-file reads, byte/hash/identity comparisons, JSON/AST/code-path inspection only. Existing tools/profile methods/build/test code are never executed by the reviewer.',
    lifecycle='Evidence-only Collaborative Review; no new TAAR product node or product status transition claimed.')
s.write_new(D/'REPORT.json',report)
s.write_new(D/'SOURCE-CANDIDATE-CONSERVATION.json',dict(recorded_at=s.utc(),Source290=source_before,
    candidate294=candidate_before,original_tool_evidence=prior,report=reference(D/'REPORT.json')))
files={path.relative_to(D).as_posix():s.ordinary(path) for path in D.iterdir() if path.is_file()}
s.write_new(D/'REVIEW-SEAL.json',dict(recorded_at=s.utc(),reviewer=s.ACTOR,files=files,
    decision=report['decision'],scope_complete=True,Source_mutation=False,profile_or_worker_execution=False))
print(json.dumps(dict(decision=report['decision'],exit_status=0,qualification_exit_status=1,
    existing_regression_passed=True,Source290_exact=True,candidate294_exact=True,
    reviewed_prior_files=len(prior),report_sha256=s.sha(D/'REPORT.json'),
    conservation_sha256=s.sha(D/'SOURCE-CANDIDATE-CONSERVATION.json'),seal_sha256=s.sha(D/'REVIEW-SEAL.json'))),flush=True)

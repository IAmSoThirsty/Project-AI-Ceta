"""Freeze the existing JS8 join and finite reviewed caller adaptation."""
from foundation_support import *
import ast
import difflib
import js8_support as j

J=F/'.agents/runtime/js7-20261015';P7=F/'.agents/js7-20261015'
P6=F/'.agents/fn6-20261015';R6=F/'.agents/runtime/fn6-20261015'
N=R/'native-readiness';G=R/'native-gate'
assert not (Q/'TRANSFER-MANIFEST.json').exists()
claim=read(R/RUN/'claims.json')['implement'];assert claim['executor_id']==AUTHOR and Path(claim['workspace'])==Q
parent=read(P7/'TRANSFER-MANIFEST.json');fn6=read(P6/'TRANSFER-MANIFEST.json')
assembly=read(R/'ASSEMBLY.json');v=read(R/'INPUTS.json')
payloads={name:ordinary(Q/name) for name in assembly['payloads']};assert len(payloads)==352
source={name:ordinary(F/name) for name in v['Source295']};assert source==v['Source295']
assert sha(F/'.agents/runtime/js7-20261015/amendment-fixture1/ACCEPTED-SOURCE-BASELINE.json')=='bd7af13da30e54aa916696cb9c4dbcd32539e2600e0fdc02f8af56f63d47fbbf'
for name,row in v['auxiliary_copies11'].items():assert ordinary(Q/name)==row
for name,row in v['auxiliary_source11'].items():assert ordinary(F/name)==row
assert len(v['auxiliary_copies11'])==11
subject=read(N/'SOURCE-SUBJECT.json')
assert payloads=={name:row['candidate'] for name,row in subject['payloads'].items()}
assert sha(N/'ROOT-NATIVE-FINDINGS.json')=='6a03fd6cf95d828cace235e8e0d0c18f53cbb9877fac5338410536b756982d36'
native=read(N/'ROOT-NATIVE-FINDINGS.json');assert native['decision']=='ORIGINAL_SEVEN_NATIVE_CASES_PASSED'
_,native_result=j.proof(native['result']);_,native_outer=j.proof(native['supervision'])
assert native_result['tests_run']==7 and all(type(native_result[k]) is int and native_result[k]==0 for k in ('failures','errors','skips','exit_status'))
assert native_result['expected_ids']==native_result['executed_ids']==native_result['stopped_ids']
assert native_result['native_resources']['owned_resources_closed'] is True and native_result['remaining_threads']==[]
assert native_outer['exit_status']==0 and native_outer['decision']=='qualification_passed'
stop_path=F/'.agents/runtime/js8-20261015-stop-review/review.json'
assert sha(stop_path)=='f693fd85bf46465d41bfa40ad073adc5cfb87eda896b663f2428fcca738bce0e'
stop=read(stop_path)
assert stop['decision']=='approved' and stop['exit_status']==0 and stop['whole_JS8_approved'] is False
assert all(payloads[name]['sha256']==pin for name,pin in stop['reviewed_payload_hashes'].items())
gate_review=F/'.agents/runtime/js8-native-gate-root-review-20261015/REVIEW.json'
assert sha(gate_review)=='31a1601ad7fab4cf31959b03fcf12e70608e053929d0e4d04c38d98a2952ce01'
assert sha(G/'native_case_gate.py')=='cdfa4d37444002338a2138b1cdd1da878ea50fa61d16f67044491815351fb6d4'
for name in j.SCRIPT_NAMES:ast.parse((R/name).read_bytes())
controls=read(R/'caller-controls-r1/RESULT.json')
assert controls['tests_run']==4 and controls['scripts']==j.scripts()
assert controls['expected_ids']==controls['executed_ids']==controls['stopped_ids']
assert all(type(controls[k]) is int and controls[k]==0 for k in ('failures','errors','skips','exit_status'))
observed=F/'.agents/runtime/js8-20261015-independent-review'
observer_results=[p for p in observed.glob('*.json') if 'REGISTRATION' in p.name]
repaired=[p for p in observer_results if read(p).get('tests_run')==2 and read(p).get('exit_status')==0]
assert repaired,'INDEPENDENT_REGISTRATION_CLOSURE_REQUIRED'
assert all(ordinary(Path(row['path']))==row for row in stop['reviewed_files'].values() for row in (row['reviewed'],))
cases=read(R/'APPROVED-CASESET.json');assert cases['expected_count']==len(cases['expected_ids'])==2334
discovery=read(R/'discovery-r2.json');assert discovery['tests_discovered']==2334 and discovery['exit_status']==0 and discovery['test_bodies_executed']==0
timing_before=ast.parse((R/'before-stop-timing/tests/contract/test_cpu_execution_timing_diagnostics.py').read_bytes())
old_names={n.name for n in ast.walk(timing_before) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
new_timing=[name for name in cases['expected_ids'] if name.startswith('test_cpu_execution_timing_diagnostics.') and name.rsplit('.',1)[1] not in old_names]
initializer=[name for name in cases['expected_ids'] if name.startswith('test_kernel_initializer_publication.')]
seven=native_result['expected_ids']
independent=parent['required_independent_ids']+new_timing+initializer+seven
assert len(parent['required_independent_ids'])==166 and len(new_timing)==4 and len(initializer)==3 and len(seven)==7
assert len(independent)==len(set(independent))==180 and set(independent)<=set(cases['expected_ids'])
selected=read(R/'STAGED-JOIN.json')['selected'];assert len(selected)==61
extended=[name for name in selected if name in source];created=[name for name in selected if name not in source]
assert len(extended)==4 and len(created)==57
for name in extended:assert ordinary(R/'before-images'/name)['sha256']==source[name]['sha256']
for name in created:
    try:fs.lstat(F/name)
    except FileNotFoundError:pass
    else:raise AssertionError('CREATE_TARGET_EXISTS:'+name)
fixture='tests/contract/test_launcher_custody_paths.py'
assert fixture not in selected and payloads[fixture]['sha256']==source[fixture]['sha256']=='35af2c33a76b8ac44e368c9df4a36842b0f5a04fff00bc8ccb553a9e68fd5dd1'
components={
 'accepted_JS7':dict(run_id='js7-20261015',author=parent['author'],manifest=reference(P7/'TRANSFER-MANIFEST.json'),
    review=reference(J/'independent-review/review.json')),
 'FN6_controlled':dict(run_id='fn6-20261015',author=fn6['author'],manifest=reference(P6/'TRANSFER-MANIFEST.json'),
    review=reference(R6/'independent-review/review.json'))}
for component in components.values():j.review(component['review'],component['run_id'],component['manifest']['sha256'],component['author'])
deps={}
def depend(path):
    path=Path(path);assert path.is_relative_to(F)
    deps[path.relative_to(F).as_posix()]=ordinary(path)
depend(F/'.agents/runtime/ac1-20261014/native_fixture_support.py')
depend(F/'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe')
build_path=F/'.agents/runtime/na2-20261014/build-r1/build.json';build=read(build_path)
depend(build_path);depend(build['native_executable']['path'])
assert ordinary(build['native_executable']['path'])==build['native_executable']
assert payloads['native/windows_broker/owner_approval.cpp']['sha256']==build['source']['sha256']
observer_build=F/'.agents/runtime/ob2-20261014/build-reuse/BUILD-REUSE.json';build=read(observer_build)
depend(observer_build);depend(build['native_image']['path'])
assert ordinary(build['native_image']['path'])==build['native_image']
assert payloads['native/windows_broker/effect_observer.rs']['sha256']==build['candidate_source']['sha256']
negative=F/'.agents/runtime/ob2-20261014/negative-reuse'
for path in sorted(negative.rglob('*')):
    info=fs.lstat(path);assert not fs.reparse(info)
    if path.is_file():depend(path)
environment={name:ordinary(Path(row['path'])) for name,row in v['E33601'].items()}
assert environment==v['E33601'] and len(environment)==3601
v.update(at=utc(),payloads352=payloads,components=components,fixture_dependencies=deps,
    Stop_component_review=reference(stop_path),native_seven_findings=reference(N/'ROOT-NATIVE-FINDINGS.json'),
    native_gate_review=reference(gate_review),native_gate_ready=reference(G/'READY-FOR-INTEGRATION.json'),
    expected_full_methods=2334,required_independent_ids=independent,product_copy_credit=0,
    native_full_executed=False,Source_publication=False,full_gate_pending=True)
write_new(R/'FINAL-INPUTS.json',v)
write_new(R/'DESTINATION-COHORT.json',dict(at=utc(),expected_ids=independent,expected_count=180,
    established166=parent['required_independent_ids'],Stop4=new_timing,initializer3=initializer,native7=seven,
    selection='Root RE-T32 refinement and WT finite selection; full2334 covers remaining inherited methods.',
    actual_destination_execution='NOT_RUN'))
diffs={}
(R/'helper-diffs').mkdir(exist_ok=False)
for name in j.SCRIPT_NAMES:
    original='js7_support.py' if name=='js8_support.py' else name
    before=J/original
    if not before.is_file():before=R6/original
    if before.is_file():
        path=R/'helper-diffs'/(name+'.diff')
        fs.write_new(path,''.join(difflib.unified_diff(before.read_text().splitlines(True),(R/name).read_text().splitlines(True),
            fromfile=str(before),tofile=str(R/name))).encode())
        diffs[name]=reference(path)
write_new(R/'PRIOR-FAILURES.json',dict(at=utc(),FN6_native_failure=subject['parent_manifest'],
    FN6_native_failed_result=reference(R6/'native-readiness/attempt-35f87ff04a88447aab3d4055d55b86a4/c/RESULT.json'),
    FN6_native_failed_findings=reference(R6/'native-readiness/ROOT-NATIVE-FINDINGS.json'),
    Stop_baseline=reference(R/'stop-baseline-r1/RESULT.json'),
    discovery_reader_failure=reference(R/'discovery-r1.json'),
    observer_failed_oracles=[reference(path) for path in observer_results if read(path).get('exit_status')!=0],
    observer_repaired_oracles=[reference(path) for path in repaired],
    parent_JS7_failures=parent['prior_failures'],full_no_profile_previous='Historical F4 deferred; no approval reused.',
    historical_unresolved='F4 interruptedr4/109 directory attribute changes and controlled pending pairs retained; no historical numeric PID/path cleanup.'))
def meaningful(raw):
    tree=ast.parse(raw);ignored=set()
    for node in ast.walk(tree):
        body=getattr(node,'body',None)
        if isinstance(body,list) and body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):
            ignored.update(range(body[0].lineno,body[0].end_lineno+1))
    return [line.strip() for number,line in enumerate(raw.decode().splitlines(),1) if number not in ignored and line.strip() and not line.lstrip().startswith('#')]
loc={}
for name in ('src/ceta/kernel/cpu_execution.py','tests/contract/test_cpu_execution_timing_diagnostics.py'):
    old=meaningful((R/'before-stop-timing'/name).read_bytes());new=meaningful((Q/name).read_bytes())
    added=removed=0
    for tag,a,b,c,d in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes():
        if tag in ('replace','insert'):added+=d-c
        if tag in ('replace','delete'):removed+=b-a
    loc[name]=dict(added=added,removed=removed)
write_new(R/'EXECUTABLE-DELTA.json',dict(at=utc(),new_Stop_product_diff=loc,
    all_FN6_JS7_payload_copies_credit=0,tools_are_engineering_code_not_product_Source=True,
    copied_test_oracles_credit=0,method_count_not_a_completion_percentage=True))
write_new(R/'SELF-REVIEW.json',dict(at=utc(),author=AUTHOR,source_files=352,application_paths=61,extends=4,creates=57,
    checked=['Exact Source295 accepted baseline and four originals/57 absence checks',
        'Forward launcher fixture35af preserved; all original1556 method ASTs/order',
        'Exact FN6 dependency closure plus HP Stop three-path review',
        'Root actual original7 native pass/closed custody on this frozen subject',
        'Native gate Root review and actual caller start/enter/finish/close wiring',
        'Physical closure is separate from intentionally uncertain product flags',
        'Unchanged OriginalReader/RS2 native publication and actual installed receipts',
        'Uniform GC/strict interpreter redirect/full2334/destination180/Source352 proof gates'],
    caller_controls=reference(R/'caller-controls-r1/RESULT.json'),observer_closure=[reference(path) for path in repaired],
    full_or_Source_execution='NOT_RUN',decision='READY_FOR_DISTINCT_JOINED_REVIEW'))
support=('bootstrap.py','prepare_tools.py','discover_only.py','freeze.py','qualify_callers.py',
    'APPROVED-CASESET.json','DESTINATION-COHORT.json','discovery-r1.json','discovery-r2.json',
    'SOURCE-BASELINE-BINDING.json','ASSEMBLY.json','STAGED-JOIN.json','CODE-SCOPE.json','TASK-BINDING.json',
    'STOP-TIMING-READY.json','STOP-TIMING-SCOPE-AMENDMENT.json','EXECUTABLE-DELTA.json','PRIOR-FAILURES.json','SELF-REVIEW.json',
    'controlled-r1/RESULT.json','controlled-r1/tests.txt','controlled-r1/CUSTODY.json',
    'caller-controls-r1/RESULT.json','caller-controls-r1/RAW.txt','native-readiness/PREPARED-INPUTS.json',
    'native-readiness/PREPARATION-READBACK.json','native-readiness/PREPARATION-SEAL.json','native-readiness/ROOT-NATIVE-FINDINGS.json')
limits=[
 'Source295 remains accepted authority; candidate352/61 paths are not published by this author.',
 'Copied/integrated FN6 and JS7 code receives zero new implementation credit; only the narrow Stop repair has new Source/test credit.',
 'Root original7 native pass uses controlled authority/capacity providers; genuine approval/runtime admission/isolation remain separately unqualified and closed.',
 'Full2334 and independent destination180 remain NOT_RUN. Original restricted no-profile method stays exact and requires a fresh Root engineering gate release for each full phase.',
 'No profile Create/Delete, Hello or host process adoption is authorized by this package.',
 'Controlled pending uncertainty and F4 historical custody/directory metadata issues remain disclosed; no full metadata-preservation claim.',
 'Actual Source publication/integration/baseline are Root-owned later transitions after distinct joined review and required full/delivery proof.']
rows={name:dict(candidate=row,before=source.get(name),parent_FN6=fn6['payloads'][name]['candidate'],
    classification='EXTEND' if name in extended else 'CREATE' if name in created else 'REUSE',
    origin='Root-approved Stop amendment' if name in stop['reviewed_payload_hashes'] else 'accepted Source295' if name not in selected else 'reviewed FN6',
    copied_product_LOC_credit=0,publication_authorized=False) for name,row in payloads.items()}
write_new(Q/'TRANSFER-MANIFEST.json',dict(schema_version=1,run_id=RUN,author=AUTHOR,recorded_at=utc(),
    scope='Exact existing real-effect library join over accepted Source295 plus bounded Stop/timing precedence repair.',
    source_root=str(F),candidate_root=str(Q),runtime_root=str(R),inputs=reference(R/'FINAL-INPUTS.json'),
    parent_manifest=reference(P6/'TRANSFER-MANIFEST.json'),accepted_source_baseline=v['source_baseline'],components=components,
    constructor_closure=parent['constructor_closure'],Source_before_map_sha256=digest(j.canonical(source).encode()),
    payloads=rows,expected_payload_hashes={name:row['sha256'] for name,row in payloads.items()},application_paths=selected,
    case_set=reference(R/'APPROVED-CASESET.json'),expected_test_count=2334,required_independent_ids=independent,
    test_inventory=dict(product_modules=88,full_methods=2334,original_methods=1556,added_methods=778,independent_methods=180),
    scripts=j.scripts(),git_dependency=reference(R/'GIT-SEARCH-DEPENDENCY.json'),
    auxiliaries={name:row['sha256'] for name,row in v['auxiliary_copies11'].items()},installed_tools=parent['installed_tools'],
    fixture_dependencies=deps,Stop_component_review=reference(stop_path),Stop_payload_hashes=stop['reviewed_payload_hashes'],
    native_gate=dict(script=reference(G/'native_case_gate.py'),review=reference(gate_review),ready=reference(G/'READY-FOR-INTEGRATION.json'),
        original_case_id='test_isolated_worker.NativeIsolatedWorkerTests.test_actual_nonpersistent_launch_denial_and_medium_control_retirement'),
    native_seven_qualification=reference(N/'ROOT-NATIVE-FINDINGS.json'),
    review_support={name:reference(R/name) for name in support},helper_diffs=diffs,
    prior_failures=reference(R/'PRIOR-FAILURES.json'),self_review=reference(R/'SELF-REVIEW.json'),LOC=loc,
    integration_copy_credit=0,limits=limits,Source_publication=False,full_gate_complete=False))
print(canonical(dict(manifest=reference(Q/'TRANSFER-MANIFEST.json'),payloads=352,application_paths=61,
    modules=88,full_methods=2334,independent_methods=180,caller_controls=4,native7='RootPASS',Source_publication=False)))

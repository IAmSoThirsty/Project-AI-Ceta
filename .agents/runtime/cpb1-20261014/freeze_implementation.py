"""Freeze one exact CPB1 author cut, with no Source publication."""
from pathlib import Path
import ast,collections,difflib,io,json,os,subprocess,sys,tokenize
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cpb1-20261014';R=P/'.agents/runtime/cpb1-20261014';RUN='cpb1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN=RUN
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());started=json.loads((R/'IMPLEMENTATION-STARTED.json').read_text())
final=json.loads((R/'connected-r2.json').read_text());baseline=json.loads((R/'return-occupancy-baseline.json').read_text())
closure=json.loads((R/'return-occupancy-closure.json').read_text())
assert final['tests_run']==163 and final['exit_status']==0 and final['failures']==final['errors']==final['skips']==[]
assert len(set(final['expected_ids']))==163 and final['expected_ids']==final['executed_ids']==final['stopped_ids']
assert len(baseline['failures'])==1 and baseline['exit_status']==1
assert closure['tests_run']==1 and closure['failures']==closure['errors']==closure['skips']==[] and closure['exit_status']==0
assert final['all_recorded_native_owners_closed'] and not final['remaining_threads'] and final['class15_CPU_writes']==[]
assert len(final['all_process_owners'])==8 and len(final['class9_fresh_owned_job_setup'])==8
clocks=collections.Counter(row['backend_type'] for row in final['all_clock_owners'])
assert clocks=={'_NativeClockAPI':13,'ControlledAPI':52,None:2}
assert all(row['state']=='CLOSED' for row in final['all_clock_owners'] if row['backend_type'] is not None)
assert all(row['no_native_allocation_before_constructor_failure'] for row in final['all_clock_owners'] if row['backend_type'] is None)
assert all(s.ordinary(P/name)==row for name,row in inputs['Source290'].items())
assert all(s.ordinary(Q/name)==row for name,row in started['staged_payloads'].items())
assert all(s.ordinary(Path(row['path']))==row for row in inputs['dependency_files'].values())
assert all(s.ordinary(Q/name)==row for name,row in final['candidate_before'].items())
assert s.ordinary(s.PY)==inputs['python_image']
for parent in inputs['parents']:
    for key in ('manifest','approved_review'):
        ref=parent[key];assert s.sha(P/ref['repository_relative_path'])==ref['sha256']
environment_before=json.loads((R/'environment-before.json').read_text())
environment_after=json.loads((R/'environment-after.json').read_text())
assert environment_before['members']==environment_after['members']
assert environment_after['ordinary_files']==3601 and environment_after['ordinary_bytes']==231026067
assert environment_before['exit_status']==environment_after['exit_status']==0
git=dict(HEAD=s.fs.text_git(P,'rev-parse','HEAD'),branch=s.fs.text_git(P,'branch','--show-current'),
    tracked_status=s.fs.text_git(P,'status','--porcelain=v1','-uno'))
assert all(git[key]==inputs[key] for key in git)
eligible=['src/ceta/effects/native_cpu_binding.py','tests/contract/test_native_cpu_binding.py','contracts/NATIVE_CPU_BINDING_V1.md']
assert all(not (P/name).exists() for name in eligible)
payloads={name:s.ordinary(Q/name) for name in started['staged_payloads']}
payloads.update({name:s.ordinary(Q/name) for name in eligible});assert len(payloads)==303

def meaningful(text):
    tree=ast.parse(text);doc=set()
    for node in ast.walk(tree):
        if isinstance(node,(ast.Module,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and node.body:
            first=node.body[0]
            if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and type(first.value.value) is str:
                doc.update(range(first.lineno,first.end_lineno+1))
    comments={token.start[0] for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type==tokenize.COMMENT and not text.splitlines()[token.start[0]-1][:token.start[1]].strip()}
    return sum(bool(line.strip()) and index not in doc and index not in comments for index,line in enumerate(text.splitlines(),1))
measures={}
for name in eligible:
    text=(Q/name).read_text();code=name.endswith('.py')
    measures[name]=dict(physical_lines=len(text.splitlines()),meaningful_executable_lines=meaningful(text) if code else 0,
        test_methods=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for n in ast.walk(ast.parse(text))) if code else 0,
        classification='CREATE',reuse_credit=0)
    before=R/'before-images'/name;before.parent.mkdir(parents=True,exist_ok=True)
    s.fs.write_new(before,b'')
    diff=''.join(difflib.unified_diff([],text.splitlines(keepends=True),fromfile='/dev/null',tofile=name))
    s.fs.write_new(R/(name.replace('/','__')+'.diff'),diff.encode('utf-8'))
assert measures[eligible[1]]['test_methods']==42
old_tree=ast.parse((R/'return-r1-before/test_native_cpu_binding.py').read_text())
new_tree=ast.parse((Q/eligible[1]).read_text())
methods=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
old_methods,new_methods=methods(old_tree),methods(new_tree)
assert len(old_methods)==40 and all(new_methods[name]==body for name,body in old_methods.items())
s.write_new(R/'MEASURES.json',dict(recorded_at=s.utc(),files=measures,
    new_meaningful_source_LOC=measures[eligible[0]]['meaningful_executable_lines'],
    new_meaningful_test_LOC=measures[eligible[1]]['meaningful_executable_lines'],
    documentation_lines=measures[eligible[2]]['physical_lines'],retained300_LOC_credit=0,
    exact_old40_test_ASTs=True,new_product_test_methods=42,
    extra_literal_return_probe_methods=1,extra_literal_probe_new_product_LOC_credit=0,
    method='Nonblank non-comment physical Python lines excluding complete module/class/function docstring spans; role/runtime/evidence helpers and reused dependencies excluded.'))
s.write_new(R/'CONSERVATION.json',dict(recorded_at=s.utc(),Source290=inputs['Source290'],
    Source290_current_native_bytes_exact=True,candidate_dependency300_exact=True,
    native_dependency_origins=inputs['dependency_files'],parents=inputs['parents'],git_current=git,
    E3_before=s.reference(R/'environment-before.json'),E3_after=s.reference(R/'environment-after.json'),
    E3_declared3601_native_bytes_exact=True,python_image=inputs['python_image'],
    limits='Matching bounded endpoint observations; no loaded-memory attestation or uninterrupted-custody assertion.',
    eligible_active_Source_paths_absent=eligible,Source_publication=False))
s.write_new(R/'SELF-REVIEW.json',dict(recorded_at=s.utc(),author=s.ACTOR,independent_review=False,
    personally_inspected=eligible,public_API=['NativeCpuBinding.capture','NativeCpuBinding.require_current',
        'NativeCpuBinding.driver_arguments','NativeCpuBinding.cancel','NativeCpuBinding.close'],
    native_domain='NC2 raw QPC sample bracket; original WT4 GetTickCount64 observation kept unchanged privately.',
    correction='Final high-resolution elapsed charge covers post-measurement serialization/validation before pure currentness and cancellation fence.',
    first_failure=s.reference(R/'return-occupancy-baseline.json'),unchanged_oracle=s.reference(R/'probe_return_occupancy.py'),
    closure=s.reference(R/'return-occupancy-closure.json'),final=s.reference(R/'connected-r2.json'),
    prior_passing_cut=s.reference(R/'connected-r1.json'),original_cut_before_images={name:s.ordinary(R/'return-r1-before'/name)
        for name in ('native_cpu_binding.py','test_native_cpu_binding.py','NATIVE_CPU_BINDING_V1.md')},
    ownership='One existing target/clock borrowed; private capture is metrology provenance, never authority/permit/native effect.',
    native_safety='Only canonical class9 setup for8 fresh owned medium worker jobs; global class15 guard recorded0 calls. Actual driver fence checks then vetoes before Set/version spend.',
    fixtures='36 controlled domain methods plus6 actual Windows observation methods. Native clock epoch1 remains a controlled input and gives no live authority.',
    conservation=s.reference(R/'CONSERVATION.json'),
    remaining=['Distinct review of exact frozen bytes and timing translation','Root-only integration of exactly3CREATE paths',
        'Canonical genuine owner/authority/admission and effect adapter composition','Qualified isolation/public runtime activation remains separately pending',
        'Actual host suspend/clock change and physical CPU effect intentionally not executed.'],Source_publication=False))
composition=collections.Counter(test.split('.')[0] for test in final['expected_ids'])
assert composition['test_native_cpu_binding']==42
classification={name:('CREATE' if name in eligible else 'REUSE_DEPENDENCY' if name in inputs['dependency_files'] else 'REUSE') for name in payloads}
s.write_new(Q/'TRANSFER-MANIFEST.json',dict(schema_version=1,job=RUN,author=s.ACTOR,frozen_at=s.utc(),
    source_root=str(P),candidate_root=str(Q),runtime_root=str(R),payload_count=303,
    eligible_application_paths=eligible,classification=classification,payloads=payloads,
    source_inputs=s.reference(R/'SOURCE-INPUTS.json'),parents=inputs['parents'],
    Source290=inputs['accepted_Source'],tests=s.reference(R/'connected-r2.json'),raw=final['raw'],
    retained_test40_ASTs_exact=True,new_test_methods=42,cohort_composition=dict(composition),
    extra_unchanged_oracle=s.reference(R/'probe_return_occupancy.py'),extra_oracle_closure=s.reference(R/'return-occupancy-closure.json'),
    prior_nonzero_attempt=s.reference(R/'return-occupancy-baseline.json'),measures=s.reference(R/'MEASURES.json'),
    conservation=s.reference(R/'CONSERVATION.json'),self_review=s.reference(R/'SELF-REVIEW.json'),
    authority_or_CPU_policy_created=False,Source_publication=False,independent_review_required=True))
s.write_new(R/'HANDOFF.json',dict(recorded_at=s.utc(),candidate=str(Q),runtime=str(R),
    manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),eligible_application_paths=eligible,
    executable_behavior='Same-owner native CPU policy capture/currentness/conservative raw-QPC versus original-driver timing arguments; no Set or authority.',
    exact_final_unique_methods=163,new_product_methods=42,retained_methods=121,
    extra_literal_probe_method=1,baseline_probe_exit_status=1,closure_probe_exit_status=0,
    final=s.reference(R/'connected-r2.json'),raw=final['raw'],
    native_census=dict(workers_closed=8,native_clock_owners_closed=13,controlled_clock_owners_closed=52,
        clock_constructor_failures_before_native_allocation=2,class9_fresh_owned_job_setups=8,class15_writes=0,remaining_threads=[]),
    API_source=eligible[0],measures=s.reference(R/'MEASURES.json'),conservation=s.reference(R/'CONSERVATION.json'),
    Source_published=False,independent_review=False,next='Distinct reviewer must claim actual review on exact frozen Q; mirror fixtures under reviewer output or obtain explicit fresh Q fixture extension.'))
commands=[dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(R/'run_tests.py'),'connected-r2','connected']),exit_status=0),
    dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(R/'probe_return_occupancy.py'),'return-occupancy-closure']),exit_status=0),
    dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(R/'verify_environment.py'),'environment-after']),exit_status=0)]
result=dict(manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),
    handoff=s.reference(R/'HANDOFF.json'),self_review=s.reference(R/'SELF-REVIEW.json'),
    tests_run=163,new_product_methods=42,retained_methods=121,extra_literal_probe_methods=1,
    first_nonzero_attempt=s.reference(R/'return-occupancy-baseline.json'),actual_nonzero_attempt_relabelled=False,
    final=s.reference(R/'connected-r2.json'),measures=s.reference(R/'MEASURES.json'),
    Source290_and_E33601=s.reference(R/'CONSERVATION.json'),class15_CPU_writes=0,
    native_process_owners_closed=8,native_clock_owners_closed=13,Source_published=False,independent_review=False)
response=s.complete('implement',result,commands,[('Final163 exact IDs pass without failures/errors/skips',True),
    ('Unchanged literal20ms/5ms return-occupancy oracle closes on final bytes',True),
    ('Native8workers/13clock owners retired;0CPUwrites/remainingthreads',True),
    ('Source290/E33601/native dependency pins retained;3CREATE eligibility only',True),
    ('Author proof remains distinct from independent review and authority/effect acceptance',True)])
print(json.dumps(dict(manifest=result['manifest'],implement=s.reference(R/'implement.json'),
    sequence=response['sequence'],states=response['states'])),flush=True)

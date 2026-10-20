"""Finish one bounded CPB1 independent review, preserving every old failure."""
from pathlib import Path
import ast, collections, hashlib, io, json, os, stat, subprocess, sys, tokenize
F=Path('T:/00-Active/Project-AI-CETA');Q=F/'.agents/cpb1-20261014';R=F/'.agents/runtime/cpb1-20261014';D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=D
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
prep=read(D/'PREPARATION.json');result=read(D/'connected-independent-r1.json');observed=read(D/'OBSERVED-EXECUTION.json');literal=read(D/'literal-return-r1.json')
assert result['exit_status']==literal['exit_status']==0 and result['tests_run']==163 and literal['tests_run']==1
assert result['failures']==result['errors']==result['skips']==literal['failures']==literal['errors']==literal['skips']==[]
assert result['expected_ids']==result['executed_ids']==result['stopped_ids']==prep['expected_ids']
assert len(set(result['expected_ids']))==163
assert result['all_recorded_native_owners_closed'] and not result['remaining_threads'] and not result['class15_CPU_writes']
assert observed['workers_closed'] and observed['clocks_closed'] and not observed['recorder_errors']
assert len(result['all_process_owners'])==8 and all(all(row[k] for k in ('lifetime_closed','process_closed','job_closed','thread_closed')) for row in result['all_process_owners'])
assert len(result['class9_fresh_owned_job_setup'])==8
worker_stream=[json.loads(line) for line in (D/'native-worker-identities.jsonl').read_text().splitlines()]
native_stream=[json.loads(line) for line in (D/'native-receipts.jsonl').read_text().splitlines()]
case_stream=[json.loads(line) for line in (D/'per-case-custody.jsonl').read_text().splitlines()]
clock_stream=[json.loads(line) for line in (D/'clock-owner-identities.jsonl').read_text().splitlines()]
assert worker_stream==observed['native_worker_identities'] and len(worker_stream)==8 and len(set((r['pid'],r['creation_time']) for r in worker_stream))==8
assert set((r['pid'],r['creation_time']) for r in worker_stream)==set((r['pid'],r['creation_time']) for r in result['all_process_owners'])
assert native_stream==result['native_receipts'] and len(native_stream)==6
assert len(clock_stream)==67 and sum(r['backend_type']=='_NativeClockAPI' for r in clock_stream)==13
assert len(case_stream)==163 and [row['test_id'] for row in case_stream]==result['expected_ids']
assert all(row['state']=='CLOSED' and not row['registration_owned'] and not row['sampler_alive'] and row['callbacks']==0 for row in case_stream[-1]['clocks'] if row['backend_type'] is not None)
def inventory(root):
    files={};dirs={};pending=[root]
    while pending:
        current=pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                p=current/entry.name;name=p.relative_to(root).as_posix();info=s.fs.lstat(p);assert not s.fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):dirs[name]=s.fs.file_identity(info);pending.append(p)
                else:assert stat.S_ISREG(info.st_mode);files[name]=s.ordinary(p)
    return dict(sorted(files.items())),dict(sorted(dirs.items()))
candidate,dirs=inventory(Q);assert candidate==prep['candidate326'] and dirs==prep['candidate_directories']
source={n:s.ordinary(F/n) for n in prep['Source290']};assert source==prep['Source290']
assert s.source_inventory()=={n:row for n,row in source.items() if n.split('/')[0] in ('src','tests','contracts')}
assert all(not (F/name).exists() for name in prep['eligible_paths'])
e3,e3dirs=inventory(s.PY.parents[1]);assert e3==prep['E3_members'] and e3dirs==prep['E3_directories'] and len(e3)==3601 and sum(row['bytes'] for row in e3.values())==231026067
author={n:s.ordinary(R/n) for n in prep['author_evidence']};assert author==prep['author_evidence']
for name,value in prep['pins'].items():assert s.sha((Q if name=='TRANSFER-MANIFEST.json' else R)/name)==value
assert s.fs.text_git(F,'rev-parse','HEAD')==prep['observed_HEAD'] and s.fs.text_git(F,'branch','--show-current')==prep['branch'] and s.fs.text_git(F,'status','--porcelain=v1','-uno')==prep['dirty_tracked']
ct4=read(F/'.agents/runtime/ct4-20261014/active-application/APPLIED.json')
metadata={row['relative_path']:s.ordinary(F/row['relative_path']) for row in ct4['completed']}
assert all(metadata[row['relative_path']]['sha256']==row['sha256'] for row in ct4['completed'])
fixture_files,fixture_dirs=inventory(D/'fixture-root')
actual_metadata=[read(Path(row['path'])) for name,row in fixture_files.items() if name.endswith('/primary.json')]
assert len(actual_metadata)==8 and set((row['pid'],row['creation']) for row in actual_metadata)==set((row['pid'],row['creation_time']) for row in worker_stream)
def meaningful(text):
    tree=ast.parse(text);doc=set()
    for node in ast.walk(tree):
        if isinstance(node,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and node.body:
            first=node.body[0]
            if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and type(first.value.value) is str:doc.update(range(first.lineno,first.end_lineno+1))
    comments={token.start[0] for token in tokenize.generate_tokens(io.StringIO(text).readline) if token.type==tokenize.COMMENT and not text.splitlines()[token.start[0]-1][:token.start[1]].strip()}
    return sum(bool(line.strip()) and i not in doc and i not in comments for i,line in enumerate(text.splitlines(),1))
production=Q/'src/ceta/effects/native_cpu_binding.py';tests=Q/'tests/contract/test_native_cpu_binding.py'
methods=lambda path:{n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
old=methods(R/'return-r1-before/test_native_cpu_binding.py');new=methods(tests)
assert len(old)==40 and len(new)==42 and all(new[n]==body for n,body in old.items())
assert meaningful(production.read_text())==296 and meaningful(tests.read_text())==375
assert len(list((Q/'src').rglob('*.py')))==78
baseline=read(R/'return-occupancy-baseline.json');assert baseline['exit_status']==1 and len(baseline['failures'])==1 and baseline['tests_run']==1
assert s.sha(R/'return-r1-before/native_cpu_binding.py')==baseline['source']['sha256']
assert read(R/'READBACK-HELPER-ERROR.json')['command_exit_status']==1
plan=F/'.agents/runtime/real-effect-20261014/plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'
assert s.sha(plan)=='d99cbc87dd5430b6287b3a77759fd75b8cdb0276a372c9a4cca8ba1bc047119c'
conservation=dict(at=s.utc(),Source290=source,candidate326=candidate,candidate_directories=dirs,author_evidence=author,E3_members=e3,E3_directories=e3dirs,CT4_metadata=metadata,
    own_fixture_files=fixture_files,own_fixture_directories=fixture_dirs,preexisting_fixture22_exact=True,all_source_and_candidate_native_bytes_exact=True,
    HEAD=prep['observed_HEAD'],branch=prep['branch'],dirty_tracked=prep['dirty_tracked'],Source_application=False)
s.write_new(D/'FINAL-CONSERVATION.json',conservation)
code_review=[
    dict(path='src/ceta/effects/native_cpu_binding.py',symbols=['__init__','_target_fields','_owned'],finding='Exact native clock type and owned target, observed Windows implementations/resolutions, captured handle/PID/creation/image/job identity and nonblocking binding/target lock ownership; no replacement owner or positive authority.'),
    dict(path='src/ceta/effects/native_cpu_binding.py',symbols=['_sample','_observation','_capture_wire','capture','_request'],finding='Detached original driver observation is retained privately. Public native-domain observation is separate, exact capture object/wire are rechecked, and strict OwnedCpuRequest is reconstructed before callbacks. Old/equal copied/cross-binding/mutated captures deny.'),
    dict(path='src/ceta/effects/native_cpu_binding.py',symbols=['_measure'],finding='Before/after NC2 samples enclose original driver query; driver timestamp must lie within its own bracket. Native lower/upper include uncertainty. Acquisition is max(high-resolution elapsed+two elapsed resolution units, full uncertain native span). Offset bounds are lower-(driver_end+driver_quantum) and upper-max(0,driver_start-driver_quantum). No absolute Python/raw-QPC epoch equality is assumed.'),
    dict(path='src/ceta/effects/native_cpu_binding.py',symbols=['_arguments'],finding='The current native/wall deadline remainder is the smaller bound minus acquisition, local post-measurement occupancy and endpoint charges. Driver deadline uses earlier driver start minus quantum. Age subtracts the original-driver/native lower timestamp offset upper bound and charge. Duration subtracts charge plus both driver quanta and cannot exceed bounded deadline remainder. Nonpositive or out-of-range allowances deny.'),
    dict(path='src/ceta/effects/native_cpu_binding.py',symbols=['capture','_arguments','_clock_fence','_pure_fence','_veto'],finding='Final QPC read follows serialization, request commitment and capture validation. Short clock-condition acquisition is nonblocking. Pure lifetime/policy/clock/session/generation/cancellation checks follow all fallible/native/time callbacks before local publication. Nested/reentrant/busy calls deny without releasing outer busy ownership.'),
    dict(path='src/ceta/effects/native_cpu_binding.py',symbols=['_tick','_clock_sample','cancel','close'],finding='Driver/elapsed rollback and native clock suspicion latch; unavailable never becomes measured zero. Binding stop/close only invalidate local state and do not close borrowed native owners. Original clock/control exceptions propagate without diagnostic cleanup replacing their primary.'),
    dict(path='src/ceta/supervisor/windows_jobs.py',symbols=['_cpu_expected','_cpu_set','apply_cpu_rate_limit'],finding='WT4 unchanged accepted dependency: original driver timestamps/age/duration/deadline/version/policy checks remain. Test dispatch callback rechecks same capture/request and then vetoes; version/native Set stays unspent. Prior WT4 authorship is disclosed, and its earlier distinct Root review supplies dependency acceptance.'),
    dict(path='src/ceta/identity/native_clock.py',symbols=['_derive_locked','_take_sample','_on_power','close'],finding='NC2 unchanged accepted dependency: actual QPC/boot/wall/interrupt/unbiased/resolution sampling and resume/gap/drift invalidation remain. Current bridge verifies ACTIVE/registration/session/epoch/resume under clock condition. Actual native registrations and threads were retired in this run.'),
    dict(path='tests/contract/test_native_cpu_binding.py',symbols=['NativeCpuBindingDomainTests','NativeCpuBindingWindowsTests'],finding='All 445 lines inspected: 36 explicitly controlled domain methods plus6 actual Windows observation methods. Existing40 test method ASTs retained, two timing-repair methods added. Same-capture final-fence hook checks then deliberately raises before Set; Stop case denies before Set. Controlled power callback is labeled and does not claim actual host resume.'),
    dict(path='contracts/NATIVE_CPU_BINDING_V1.md',symbols=[],finding='All87 lines inspected and match observation-only scope, distinct domains, conservative return-boundary budgets, borrowed custody, explicit library assumptions and separately pending effect/authority/runtime acceptance.')]
s.write_new(D/'CODE-REVIEW.json',dict(at=s.utc(),examined=code_review,approved_plan=s.reference(plan),new_defects=[],independence=prep['authored_scope']))
report=dict(at=s.utc(),executor_id='/root/wt1_reviewer',decision='approved',manifest_sha256=prep['manifest']['sha256'],approved_scope='Exact frozen CPB1 three-file native CPU/time observation bridge library delta; no Source integration or runtime effect acceptance.',
    authorship_disclosure=prep['authored_scope'],eligible_application_paths=prep['eligible_paths'],actual_parent_acceptances=prep['parent_acceptances'],
    verified=dict(payloads=303,ordinary_candidate_files=326,nonfixture_candidate_files=304,retained_fixture_metadata_files=22,modules=78,
        exact_original_connected_methods=163,new_methods=42,retained_methods=121,extra_literal_probe_methods=1,cohort=dict(collections.Counter(n.split('.')[0] for n in result['expected_ids'])),
        native_owned_worker_lifetimes=8,native_clock_owners_closed=13,controlled_clock_owners_closed=52,constructor_failures_before_native_allocation=2,per_test_native_receipts=6,
        class9_fresh_owned_job_containment_setups=8,class15_CPU_policy_writes=0,remaining_threads=[],Source_payloads_preserved=290,E3_members_preserved=3601,E3_bytes_preserved=231026067),
    LOC=dict(new_meaningful_source=296,new_meaningful_tests=375,new_product_methods=42,reuse_credit=0,Source_integration_credit=0),
    evidence={n:s.reference(D/n) for n in ('PREPARATION.json','EXECUTION-PREPARATION.json','connected-independent-r1.json','connected-independent-r1.txt','literal-return-r1.json','literal-return-r1.txt','OBSERVED-EXECUTION.json','native-worker-identities.jsonl','native-receipts.jsonl','clock-owner-identities.jsonl','per-case-custody.jsonl','CODE-REVIEW.json','FINAL-CONSERVATION.json')},
    preserved_failures=[dict(issue='Original author controlled20ms serialization occupancy escaped5ms duration.',classification='fixed in frozen cut; exact unchanged literal oracle independently passes1/1',original=s.reference(R/'return-occupancy-baseline.json'),old_source=s.reference(R/'return-r1-before/native_cpu_binding.py'),closure=s.reference(D/'literal-return-r1.json')),
        dict(issue='Original author readback expected snapshot membership to include22 disposable fixture metadata files excluded by installed TAAR.',classification='bookkeeping repair retained; exact304 nonfixture/326 ordinary sets independently verified',evidence=s.reference(R/'READBACK-HELPER-ERROR.json')),
        dict(issue='First reviewer preparation compared247 src/tests/contracts files to all290 accepted payloads.',classification='reviewer assertion corrected only; no claim or native test executed by failed attempt; all43 additional accepted inputs unchanged',evidence=s.reference(D/'PREPARATION-R1-ERROR.json'))],
    confirmed_new_defects=[],remaining=[
        dict(issue='Canonical owner/admission/effect-adapter composition and Root Source publication remain pending.',classification='requires separate implementation/integration work'),
        dict(issue='Actual physical CPU cap/restoration, independent effect observation, genuine approval/Hello and positive isolated-worker runtime acceptance were not executed by this observation-only review.',classification='separate explicit acceptance gates'),
        dict(issue='Actual host suspend/resume and wall-clock adjustment were not performed; clock trust remains bounded by accepted NC2 host assumptions.',classification='separate explicitly scheduled native acceptance'),
        dict(issue='Returned arguments are fresh at the inspected library boundary; future driver dispatch must recheck the same capture/request, canonical authority and retained driver CAS/time guards.',classification='required integration behavior; no future dispatch guarantee inferred')],
    Source_application=False,profile_mutation=False,restricted_launch=False,Hello=False,CPU_effect=False,production_activation=False,whole_product_completion=False)
s.write_new(D/'REPORT.json',report)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_persistence import sha256_json
life=R/'cpb1-20261014';claim=read(life/'claims.json')['review'];assert claim['executor_id']=='/root/wt1_reviewer' and Path(claim['workspace'])==Q
assert _changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')))==[]
receipt=dict(schema_version=1,run_id='cpb1-20261014',node_id='review',executor_id='/root/wt1_reviewer',started_at=claim['claimed_at'],finished_at=s.utc(),input_hash=claim['input_hash'],changed_files=[],
    result=dict(manifest_sha256=prep['manifest']['sha256'],report=s.reference(D/'REPORT.json'),code_review=s.reference(D/'CODE-REVIEW.json'),final_tests=s.reference(D/'connected-independent-r1.json'),literal_oracle=s.reference(D/'literal-return-r1.json'),conservation=s.reference(D/'FINAL-CONSERVATION.json'),Source_application=False,CPU_effect=False),
    commands=[dict(command=str(s.PY)+' -B -X utf8 '+str(D/'prepare_review_r2.py'),exit_status=0),dict(command=str(s.PY)+' -B -X utf8 '+str(D/'probe_return_occupancy.py')+' literal-return-r1',exit_status=0),dict(command=str(s.PY)+' -B -X utf8 '+str(D/'run_observed.py'),exit_status=0)],
    validations=[dict(name=n,passed=True) for n in ('exact_frozen_manifest303_payloads326ordinary22fixtures','actual_three_parent_review_normalized_bindings','independent_CPB1_delta_and_disclosed_WT4_authorship','complete_production_tests_contract_callsite_inspection','all42new121old163exact_ids_pass_no_skip','unchanged_original_serialization_tail_oracle_pass','conservative_distinct_clock_domain_bounds_and_private_capture','same_capture_driver_hook_veto_before_Set_and_version_spend','all8workers13native_clocks_retired_and_ID_streams_preserved','zero_class15_writes_only8owned_class9containment','Source290_E33601_author_evidence_native_bytes_exact','original_failure_and_two_reader_repairs_preserved','no_runtime_or_Source_acceptance_promoted')],exit_status=0,decision='approved')
validate_receipt(receipt,run_id='cpb1-20261014',node_id='review',executor_id='/root/wt1_reviewer',input_hash=claim['input_hash'],claimed_at=claim['claimed_at'],node=read(life/'graph.json')['graph']['nodes']['review'])
s.write_new(D/'review.json',receipt)
argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1','node','complete','cpb1-20261014','review',str(D/'review.json'),'--runtime-root',str(R)]
done=subprocess.run(argv,cwd=str(F),capture_output=True)
for suffix,raw in (('stdout',done.stdout),('stderr',done.stderr)):
    with (D/('complete-r1.'+suffix)).open('xb') as out:out.write(raw)
response=json.loads(done.stdout.decode('utf-8-sig'));assert done.returncode==0 and response['allowed'],response
stored=read(life/'receipts/review.json');state=read(life/'state.json');actual_result=read(life/'results/review.json');claims=read(life/'claims.json')
assert len(receipt)==13 and len(stored)==16 and set(stored)==set(receipt)|{'git_baseline','observed_git','receipt_hash'}
assert all(canon(stored[k])==canon(v) for k,v in receipt.items())
fingerprint=sha256_json({k:v for k,v in stored.items() if k!='receipt_hash'})
assert fingerprint==stored['receipt_hash']==state['nodes']['review']['receipt_hash']==actual_result['receipt_hash']
assert canon(actual_result['result'])==canon(receipt['result']) and state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={}
s.write_new(D/'ACTUAL-REVIEW-READBACK.json',dict(at=s.utc(),local_review=s.ordinary(D/'review.json'),persisted_review=s.ordinary(life/'receipts/review.json'),normalized_receipt_fingerprint=fingerprint,
    submitted_fields=13,persisted_fields=16,state=state,result=actual_result,claims=claims,completion_argv=argv,completion_exit_status=done.returncode,Source_application=False,CPU_effect=False))
print(canon(dict(decision='approved',actual_state='SUCCEEDED',sequence=9,claims={},review_sha256=s.sha(D/'review.json'),report_sha256=s.sha(D/'REPORT.json'),readback_sha256=s.sha(D/'ACTUAL-REVIEW-READBACK.json'))))

"""ET3 exact independent disposition and strict installed review completion."""
from review_support import *
import ast
setup=json.loads((D/'PREPARATION.json').read_text())
connected=json.loads((D/'connected-r1/RESULT.json').read_text())
native=json.loads((D/'native-r1/RESULT.json').read_text())
hostile=json.loads((D/'hostile-r1/RESULT.json').read_text())
author=json.loads((R/'connected-r1.json').read_text())
for proof,count in ((connected,406),(native,3),(hostile,4)):
    assert proof['tests_run']==count and proof['exit_status']==0
    assert not proof['failures'] and not proof['errors'] and not proof['skips']
    assert proof['expected_ids']==proof['executed_ids']
assert connected['expected_ids']==connected['stopped_ids']==author['expected_ids']
assert native['expected_ids']==native['stopped_ids']
assert len(set(connected['expected_ids']))==406
assert set(native['expected_ids']).issubset(connected['expected_ids'])
assert len(set(connected['expected_ids'])|set(hostile['expected_ids']))==410
for proof,label in ((connected,'connected-r1'),(native,'native-r1')):
    assert proof['all_observed_resources_closed'] and not proof['remaining_threads'] and not proof['forbidden_calls']
    assert len(proof['live_launch_events'])==len(proof['native_owners'])==6
    live={(row['pid'],row['creation_time']) for row in proof['live_launch_events']}
    assert len(live)==6 and live=={(row['pid'],row['creation_time']) for row in proof['native_owners']}
    assert all(row['pid']>0 and row['creation_time']>0 and row['poll'] is None and row['active_job_processes']==1 for row in proof['live_launch_events'])
    events=[json.loads(line) for line in (D/label/'lifetimes.jsonl').read_text().splitlines()]
    retired=[row for row in events if row['phase']=='BEFORE_CANONICAL_CLOSE']
    assert {(row['pid'],row['creation_time']) for row in retired}==live
    assert all(row['poll'] is not None and row['active_job_processes']==0 for row in retired)
    assert len(proof['canonical_fresh_owned_class9_setup'])==6
assert all(row['closed'] for row in connected['stores']) and len(connected['stores'])==419
assert len(connected['crash_observations'])==2 and {row['exit_code'] for row in connected['crash_observations']}=={71,72}
manifest_path=Q/'TRANSFER-MANIFEST.json';manifest=json.loads(manifest_path.read_text())
assert sha(manifest_path)=='b061311cf6f52c89b9af93845258ca061043ef6ef60d8530b9048983351e5c9a'
for ref in ('parent_manifest','parent_review','readiness_audit','qualification','qualification_raw','focused',
            'native_custody','self_review','implementation_measures','Source290','conservation','E3_after',
            'before_images','prior_failure','prior_failure_raw','before_test_adjustment'):
    item=manifest[ref];assert sha(F/item['repository_relative_path'])==item['sha256'],ref
seal=json.loads((R/'AUTHOR-SEAL.json').read_text())
assert sha(R/'AUTHOR-SEAL.json')=='8b674f699bef7dd15fe0f03277e6f1a82f71761d09f7d84b65bb8c1884f6947b'
for item in seal['members'].values():assert sha(F/item['repository_relative_path'])==item['sha256']
def inventory(root):
    result={}
    for base,dirs,files in os.walk(root,followlinks=False):
        for name in dirs:assert not fs.reparse(fs.lstat(Path(base)/name))
        for name in files:
            path=Path(base)/name;result[path.relative_to(root).as_posix()]=ordinary(path)
    return result
whole_Q=inventory(Q);assert whole_Q==setup['whole_original_Q']
assert {name:ordinary(Q/name) for name in setup['original_candidate']}==setup['original_candidate']
assert {name:ordinary(F/name) for name in setup['Source290']}==setup['Source290']
assert {name:ordinary(D/'replica'/name) for name in setup['replica']}==setup['replica']
assert {name:ordinary(F/'.agents/et2-20261014'/name) for name in setup['parent_payloads']}==setup['parent_payloads']
environment=inventory(Path(setup['E3_root']));assert environment==setup['E3']
assert len(environment)==3601 and sum(row['bytes'] for row in environment.values())==231026067
git=[fs.text_git(F,'rev-parse','--show-toplevel','--git-common-dir','HEAD'),fs.text_git(F,'status','--porcelain=v1','--untracked-files=no')]
assert git==setup['git']
before_failure=json.loads((R/'before-r1.json').read_text())
assert before_failure['tests_run']==11 and before_failure['errors']==7
readback_failure=json.loads((R/'READBACK-FAILURE-r1.json').read_text())
write(D/'CONSERVATION.json',{'at':utc(),'whole_original_Q':whole_Q,'candidate317_exact':True,
    'Source290':setup['Source290'],'E3_ordinary_files':environment,'E3_count':3601,'E3_bytes':231026067,
    'replica_input_bytes_exact':True,'parent_payloads_exact':True,'Git':git,
    'author_seal':ordinary(R/'AUTHOR-SEAL.json'),'author_before_failure':ordinary(R/'before-r1.json'),
    'author_readback_failure':ordinary(R/'READBACK-FAILURE-r1.json'),'Source_application':False})
code_path=Q/'src/ceta/kernel/effect_transactions.py'
lines=code_path.read_text().splitlines()
code_lines={}
for label,needle in [('captured_predicate','method = self.k._owned_cpu_outcome_current'),
    ('exact_native_decision','require(method(phase'),('fresh_child_reconciliation','require(observation.observer_identity.image_digest'),
    ('capacity','size <= row[\'reserved_bytes\']'),('same_transaction','self.k._store.commit((initial,)')]:
    code_lines[label]=[i+1 for i,line in enumerate(lines) if needle in line]
report={'at':utc(),'reviewer':ACTOR,'author':'/root','decision':'approved','exit_status':0,
    'manifest_sha256':sha(manifest_path),'candidate_root':str(Q),'source_root':str(F),
    'scope':'ET3 three-path fresh-child reconciliation successor over accepted ET2; no native authority/runtime activation',
    'source_locations':code_lines,'changed_production_method':'KernelEffectTransactions.record',
    'eligible_application_paths':manifest['eligible_application_paths'],
    'actual_author_delta':{'source_added_LOC':2,'source_removed_LOC':1,'test_LOC':126,'new_methods':12,
        'copied_source_LOC_credit':0,'reviewer_product_LOC_credit':0},
    'tests':{'connected_unique':406,'original_retained_ids':394,'new_ET3_methods':12,
        'separate_native_reexecutions':3,'extra_adversarial_unique':4,'total_method_executions':413,
        'distinct_executed_method_ids':410,'failures':0,'errors':0,'skips':0,
        'connected_raw_sha256':sha(D/'connected-r1/tests.txt'),'native_raw_sha256':sha(D/'native-r1/tests.txt'),
        'hostile_raw_sha256':sha(D/'hostile-r1/tests.txt')},
    'verified_findings':[
        'Only record changes in production; image continuity replaces whole-child-lifetime equality.314 parent payloads and every old test body remain exact.',
        'The same captured owner predicate and exact-None return remain required before/in/after the writer transaction. New lifetime/image data alone cannot satisfy proof provenance.',
        'Exact request/target/job/observer implementation binding, strictly increasing sequence/time, immutable original observation and one original receipt remain enforced.',
        'Fresh children settle uncertain/discrepant history; equal/old counters, changed implementation/image, foreign proof and terminal overwrite deny.',
        'All406 independent connected IDs equal author expected/executed IDs, with419 journals closed; actual before/after-COMMIT child exits71/72 reopen without dispatch.',
        'Independent3 native IPC methods capture6 current PID/creation lifetimes after canonical launch, actual live job1/pollNone, then exit/job0 and closed job/process/thread handles.',
        'Additional4 SQLite probes establish prior-proof denial, captured-method retention, one winning concurrent settlement and cumulative reserve exhaustion without refund.',
        'Cumulative fresh unavailable measurements10819/17482/24147/30814 bytes; next sequence5 denied at32768 reserve atomically, existing uncertainty/budget/reservation retained.',
        'All317 payloads and708 originalQ ordinary files, Source290, E33601/231026067 bytes, parent inputs and Git dirty state conserved.'],
    'failures_retained':{'author_baseline':{'path':str(R/'before-r1.json'),'tests':11,'errors':7,
        'classification':'Six fresh-lifetime rejection errors plus one controlled unhashable-proof expectation mismatch; current12 expressly labels TypeError from controlled registry.'},
        'readback_reader':{'path':str(R/'READBACK-FAILURE-r1.json'),
            'classification':'Author reader initially assumed bare result; installed node result is a three-key envelope. Author corrected reader; no transition repeat or source repair.'},
        'all_author_seal_member_hashes_verified':True},
    'trust_limits':['Positive producer/observer predicates are controlled domain fixtures, not native authentication.',
        'Same-host separate-process IPC tests prove their scoped CLOSED runtime behavior; no Hello/enrollment/profile/CPU effect was executed.',
        'Current observer-controller restart must restore canonical sequence continuity before use; this cut creates no restart owner.',
        'No production store isolation, physical evidence-capacity guarantee, native dispatch lease, Source publication or full-product acceptance is established.',
        'Replica executes exact317 bytes; module/DLL roots and native file identities differ explicitly from frozen Q.',
        'Native forbidden-function wrappers act in reviewer processes; child behavior is qualified through unchanged CLOSED callers and scoped assertions.'],
    'existing_issues':[{'classification':'requires_separate_followup_work','issue':'Root owns EN3 repair of the inherited pure-contract uuid import conflict; full joined leaf acceptance must use its accepted successor. No ET3 guard was widened.'},
        {'classification':'requires_separate_followup_work','issue':'Concrete native producer/observer ownership, physical capacity and restart continuity remain composition dependencies.'}],
    'authorship_disclosure':setup['authorship'],'Source_published':False,
    'evidence':{'preparation_sha256':sha(D/'PREPARATION.json'),'connected_sha256':sha(D/'connected-r1/RESULT.json'),
        'native_sha256':sha(D/'native-r1/RESULT.json'),'hostile_sha256':sha(D/'hostile-r1/RESULT.json'),
        'conservation_sha256':sha(D/'CONSERVATION.json')}}
write(D/'REPORT.json',report)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
from taar.orchestration_receipts import validate_receipt,load_receipt
claim=json.loads((R/RUN/'claims.json').read_text())['review'];assert claim['executor_id']==ACTOR
graph=json.loads((R/RUN/'graph.json').read_text())['graph']
changed=_changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')));assert changed==[]
command=lambda script,*args:{'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(D/script),*args]),'exit_status':0}
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':ACTOR,
    'started_at':claim['claimed_at'],'finished_at':utc(),'input_hash':claim['input_hash'],'changed_files':[],
    'result':{'manifest_sha256':sha(manifest_path),'report':{'repository_relative_path':(D/'REPORT.json').relative_to(F).as_posix(),'sha256':sha(D/'REPORT.json')},
        'independent_connected':406,'independent_native_reexecutions':3,'extra_hostile':4,
        'Source290_candidate317_conserved':True,'native_authority_qualified':False,'Source_application':False},
    'commands':[command('prepare_review.py'),command('run_cohort.py','connected'),command('run_cohort.py','native'),command('hostile_probes.py')],
    'validations':[{'name':name,'passed':True} for name in [
        'Exact406 IDs including394 retained and12new pass0fail_error_skip',
        'Native3 retains6 actual live-to-retired lifetimes; no profile or CPU policy effect',
        'Hostile4 verifies proof_custody_concurrency_and_finite_cumulative_accounting',
        'Only reviewed record method changes; prior test and owner/store interfaces exact',
        'Source290_Q317_wholeQ708_E33601_Git_prior_evidence_conserved',
        'Controlled positive provenance_and_remaining_public_runtime_dependencies_explicit']],
    'exit_status':0,'decision':'approved'}
kwargs={'run_id':RUN,'node_id':'review','executor_id':ACTOR,'input_hash':claim['input_hash'],
    'claimed_at':claim['claimed_at'],'node':graph['nodes']['review']}
validate_receipt(receipt,**kwargs);write(D/'review.json',receipt);validate_receipt(load_receipt(D/'review.json'),**kwargs)
invoke(['node','complete',RUN,'review',str(D/'review.json')],'review-complete')
print(json.dumps({'decision':'approved','review_sha256':sha(D/'review.json'),'report_sha256':sha(D/'REPORT.json'),
    'connected':406,'native':3,'extra_hostile':4}),flush=True)

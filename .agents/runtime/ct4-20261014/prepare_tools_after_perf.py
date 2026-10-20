"""Prepare truthful baseline/status candidates only after PERF Source acceptance."""
from pathlib import Path
import hashlib, json
R=Path(__file__).resolve().parent
F=R.parents[2]
OLD=F/'.agents/runtime/ct3-20261014'
PERF=F/'.agents/runtime/perf1-20261014'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
state=read(PERF/'perf1-20261014/state.json')
assert state['sequence']==13 and all(n['state']=='SUCCEEDED' for n in state['nodes'].values())
assert read(PERF/'perf1-20261014/claims.json')=={}
assert read(PERF/'actual-acceptance.json')['integrate_receipt_sha256']==sha(PERF/'integrate.json')
assert sha(OLD/'prepare_status.py')=='530de1db2fa933f20bc504c76eef160f0761e4bc14ed7611abcf6d54f262b70a'
script=(OLD/'prepare_status.py').read_text(encoding='utf-8')
script=script.replace('ct3-20261014','ct4-20261014')
for old,new in (('== 1416','== 1479'),("'passed': 1416","'passed': 1479"),
                ("'current_source_tests': 1416","'current_source_tests': 1479"),
                ('== 286','== 290'),("'source_payloads': 286","'source_payloads': 290"),
                ("'source_hashes': 286","'source_hashes': 290"),
                ('Source286 hashes','Source290 hashes'),('1416 contract tests,286 payload hashes','1479 contract tests,290 payload hashes'),
                ('1416_CURRENT_SOURCE','1479_CURRENT_SOURCE')):
    assert old in script,old
    script=script.replace(old,new)
script=script.replace("'rp1-20261014', 'rs-owner2-20261014', 'er1-20261014', 'hp10-20261014'", "'rp1-20261014', 'rs-owner2-20261014', 'er1-20261014', 'hp10-20261014', 'rb-task1-20261014', 'perf1-20261014'")
script=script.replace("base = F / '.agents/runtime/rs-owner2-20261014'", "base = F / '.agents/runtime/perf1-20261014'")
script=script.replace("'source_ledger': packages['rs-owner2-20261014']", "'source_ledger': packages['perf1-20261014']")
script=script.replace("'accepted_source_cut': packages['rs-owner2-20261014']", "'accepted_source_cut': packages['perf1-20261014']")
script=script.replace("'Source_ledger': packages['rs-owner2-20261014']", "'Source_ledger': packages['perf1-20261014']")
script=script.replace("'accepted_source_ledger': packages['rs-owner2-20261014']", "'accepted_source_ledger': packages['perf1-20261014']")
script=script.replace('AT_RS_OWNER2_ACCEPTED_SOURCE_CUT','AT_RB_PERF_ACCEPTED_SOURCE_CUT').replace('EXECUTED_RS_OWNER2_INTEGRATION','EXECUTED_RB_PERF_INTEGRATION')
script=script.replace('AT_RS_OWNER2_ACCEPTED_CUT','AT_RB_PERF_ACCEPTED_CUT')
script=script.replace('historical_fields_before_ct3_20261014','historical_fields_before_ct4_20261014')
script=script.replace('Prepare two truthful status candidates only after accepted reservation delivery.', 'Prepare reviewed baseline and continuity candidates after accepted RB and PERF delivery.')
script=script.replace("observed = now()", "observed = now()\nactual_head = subprocess.run(['git','rev-parse','HEAD'],cwd=F,capture_output=True,check=True,text=True).stdout.strip()\nactual_branch = subprocess.run(['git','branch','--show-current'],cwd=F,capture_output=True,check=True,text=True).stdout.strip()\nassert actual_head == '8ac404cdb2dd64c2dae974fbd25e13975b09295b' and actual_branch == 'build/standalone'\n")
start=script.index('facts = {');end=script.index('\nQ.mkdir()',start)
facts='''facts = copy.deepcopy(read(F / 'build/progress.json')['current_repository_execution_20261014'])
facts.update({'recorded_at': observed, 'Git_HEAD':actual_head,'branch':actual_branch,
    'accepted_source_integrations': ['APP3','BR1','WA1','HD2','GD3','RP1','RS-owner2','RB-task1','PERF1'],
    'source_payloads':290, 'product_modules':74, 'current_scoped_tests':suite_summary, 'accepted_package_ledgers':packages})
rs = F / '.agents/runtime/rs-owner2-20261014'
old_loc = facts['reservation_integrated_LOC']
facts['reservation_integrated_LOC'] = {'source_added':379,'source_removed':0,'tests_added':916,
    'method':old_loc['LOC_method'], 'historical_preapplication_count_proof':ref(rs/'root-integration/executable-source-and-test-delta.json'),
    'accepted_integration':packages['rs-owner2-20261014'], 'actual_completion_helper':ref(rs/'root-integration/complete_destination.py'),
    'Source_application':True}
for field, package, review_directory, independent_count in (
    ('budget_candidate','rb-task1-20261014','independent-root-review',276),
    ('performance_candidate','perf1-20261014','independent-review',384)):
    root=F/'.agents/runtime'/package
    facts[field]={'run_id':package,'state':'SOURCE_INTEGRATION_ACCEPTED','ledger':packages[package],
        'manifest':ref(F/'.agents'/package/'TRANSFER-MANIFEST.json'),
        'independent_candidate_review':ref(root/review_directory/'review.json'),
        'independent_destination_review':ref(root/'independent-destination/destination-review.json'),
        'independent_current_source_tests':independent_count,'Source_application':True,'whole_unit_completion':False}
facts['newly_integrated_LOC']={}
for name in ('rb-task1-20261014','perf1-20261014'):
    count_path=F/'.agents/runtime'/name/'root-integration/executable-source-and-test-delta.json'
    counts=read(count_path)
    facts['newly_integrated_LOC'][name]={'source_added':counts['source_added'],
        'source_removed':counts['source_removed'],'tests_added':counts['tests_added'],'method':counts['method'],
        'historical_preapplication_count_proof':ref(count_path),'accepted_integration':packages[name],
        'Source_application':True}
facts['remaining_product_requirements']=[item for item in facts['remaining_product_requirements']
    if item!='Integrate reviewed budget and performance candidates with full joined regressions']
plan=F/'.agents/runtime/real-effect-20261014'
assert sha(plan/'plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md')=='d99cbc87dd5430b6287b3a77759fd75b8cdb0276a372c9a4cca8ba1bc047119c'
assert read(plan/'independent-root-review/COLLABORATIVE-REVIEW.json')['decision']=='APPROVED_FOR_BOUNDED_ENGINEERING_IMPLEMENTATION'
wt=F/'.agents/runtime/wt1-20261014'
assert read(wt/'wt1-20261014/state.json')['nodes']['review']['state']=='FAILED'
assert read(wt/'wt1-20261014/claims.json')=={}
facts['next_major_acceptance_milestone']={'name':'Real-effect governance through the public runtime',
    'state':'ENGINEERING_IN_PROGRESS_ACCEPTANCE_NOT_RUN','plan':ref(plan/'plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'),
    'Collaborative_Review':ref(plan/'independent-root-review/COLLABORATIVE-REVIEW.json'),
    'tasks':32,'acceptance_cases':38,'activation_gates':6,'owner_approval_required_for_positive_runtime_journey':True,
    'rejected_dependency':{'run_id':'wt1-20261014','review':ref(wt/'independent-review/review.json'),
        'defect':'Final Stop inside clock fence still permits native class15 Set; unchanged failures preserved for WT2 repair.'},
    'dependency_jobs':['WT2 final Stop repair','AC1 restrictive native worker'], 'runtime_effect_acceptance':False}
baseline={'recorded_at':observed,'source_root':str(F),'display_identity':'Project-AI: CETA','Git_HEAD':facts['Git_HEAD'],'branch':facts['branch'],
    'code_scope':'Exact290 published payloads;74 current modules; all1479 current contract cases. Metadata is a subsequent separately reviewed two-path publication.',
    'source_hashes':suite['after_hashes'],'tests':suite_summary,'accepted_integrations':packages,
    'new_source_added':409,'new_source_removed':4,'new_test_added':556,'new_methods':63,
    'next_major_acceptance_milestone':facts['next_major_acceptance_milestone'],'whole_product_acceptance':False}
save(R/'ACCEPTED-SOURCE-BASELINE.json',baseline)
facts['accepted_source_baseline']=ref(R/'ACCEPTED-SOURCE-BASELINE.json')
'''
script=script[:start]+facts+script[end:]
script=script.replace("        candidate['next_action'] = 'Integrate reviewed task-budget and performance candidates; implement the next dependency-ready code package and native owner interfaces; continue authorized source/history consolidation with current evidence.'", "        candidate['next_action'] = 'Implement the reviewed real-effect plan: repaired Stop/dispatch primitive, actual isolated worker, genuine owner/time providers, canonical retained admission, independent observation and crash reconciliation. Continue existing product/source obligations with current evidence.'")
script=script.replace("        candidate['current_deliverable'] = 'Project-AI: CETA accepted resource reservation accounting on the current local Source;1479 contract tests,290 payload hashes,74 modules; task-budget and performance candidates await integration; installed and whole-product qualification remain open.'", "        candidate['current_deliverable'] = 'Project-AI: CETA accepted RB-task1 and PERF1 Source baseline:1479 contract cases,290 payloads,74 modules. The real-effect governance milestone is planned, reviewed and in engineering implementation.'")
anchor="    assert all(candidate[key] == value for key, value in prior.items() if key not in allowed)"
assert script.count(anchor)==1
script=script.replace(anchor,'''    candidate['accepted_source_baseline_20261014']=ref(R/'ACCEPTED-SOURCE-BASELINE.json')
    allowed.add('accepted_source_baseline_20261014')
    if relative=='build/progress.json':
        old_ref='handoff/source_reco3nciliation_20261006_07.md'
        repaired_ref='handoff/source_reconciliation_20261006_07.md'
        assert prior['work_packages'][1]['evidence_refs'][39]==old_ref
        assert (F/repaired_ref).is_file() and not (F/old_ref).exists()
        candidate['work_packages'][1]['evidence_refs'][39]=repaired_ref
        candidate['metadata_reference_repair_20261014']={'pointer':'/work_packages/1/evidence_refs/39',
            'before':old_ref,'after':repaired_ref,'origin':'UNESTABLISHED','preserved_current_before_image':str((R/'before'/relative).relative_to(F)).replace('\\\\','/'),
            'observed_drift':ref(F/'.agents/runtime/rb-task1-20261014/metadata-at-integration-preparation.json')}
        allowed.update({'work_packages','metadata_reference_repair_20261014'})
        repaired_compare=copy.deepcopy(candidate['work_packages']);repaired_compare[1]['evidence_refs'][39]=old_ref
        assert repaired_compare==prior['work_packages']
'''+anchor)
script=script.replace("'current_source_tests': 1479", "'current_source_tests': 1479, 'baseline_sha256':sha(R/'ACCEPTED-SOURCE-BASELINE.json')")
compile(script,str(R/'prepare_status.py'),'exec')
with (R/'prepare_status.py').open('x',encoding='utf-8',newline='\n') as stream:stream.write(script)
print(json.dumps({'prepared_status_script_sha256':sha(R/'prepare_status.py'),'actual_PERF_integrate_sha256':sha(PERF/'integrate.json')}))

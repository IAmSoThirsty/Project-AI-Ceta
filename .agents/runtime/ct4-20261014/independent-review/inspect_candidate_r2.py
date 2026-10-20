"""Independent CT4 exact JSON leaf, native identity and accepted Source review."""
from ct4_support import *
import ast, copy, difflib, re

M='2e8cdfd1bcd8e1b2c250c33f156df450c03bbc34f60efbdce90c9de3edf08efe'
H='d667f4edcfcba670af85ee06620ac3ee84c713d4f599e36d6cd36d215ca34664'
I='447f7a9149781e1b71aabf7f8bbeb3c54859fafd7f201292909746d117bdb3ed'
B='89f93db80a8fca90e7d5ac49d74aed06484d137e9689ef404e00a471e7f09e98'
strict=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
equal=lambda a,b:strict(a)==strict(b)

def leaf_changes(a,b,path=''):
    if type(a) is not type(b):return [{'pointer':path,'before':a,'after':b,'change':'TYPE_OR_VALUE'}]
    if isinstance(a,dict):
        out=[]
        for key in sorted(set(a)|set(b)):
            p=path+'/'+key.replace('~','~0').replace('/','~1')
            if key not in a:out.extend(new_leaves(b[key],p,'ADDED'))
            elif key not in b:out.extend(new_leaves(a[key],p,'REMOVED'))
            else:out.extend(leaf_changes(a[key],b[key],p))
        return out
    if isinstance(a,list):
        out=[]
        for index in range(max(len(a),len(b))):
            p=path+'/'+str(index)
            if index>=len(a):out.extend(new_leaves(b[index],p,'ADDED'))
            elif index>=len(b):out.extend(new_leaves(a[index],p,'REMOVED'))
            else:out.extend(leaf_changes(a[index],b[index],p))
        return out
    return [] if equal(a,b) else [{'pointer':path,'before':a,'after':b,'change':'VALUE'}]

def new_leaves(v,path,change):
    if isinstance(v,dict) and v:return [row for k,x in sorted(v.items()) for row in new_leaves(x,path+'/'+k.replace('~','~0').replace('/','~1'),change)]
    if isinstance(v,list) and v:return [row for i,x in enumerate(v) for row in new_leaves(x,path+'/'+str(i),change)]
    return [{'pointer':path,'value':v,'change':change}]

def bound(reference):
    rel=reference['repository_relative_path'];fs.relative_name(rel)
    path=fs.safe_components(F/rel);observed=ordinary(path)
    assert observed['sha256']==reference['sha256'],('REFERENCE_DRIFT',rel)
    return path,observed

def accepted(name):
    root=F/'.agents/runtime'/name;s=read(root/name/'state.json');c=read(root/name/'claims.json')
    assert s['sequence']==13 and c=={} and len(s['nodes'])==6 and all(n['state']=='SUCCEEDED' for n in s['nodes'].values())
    a=read(root/'actual-acceptance.json');assert a['integrate_receipt_sha256']==sha(root/'integrate.json')
    return {'run_id':name,'sequence':13,'claims':{},'accepted_at':s['nodes']['integrate']['completed_at'],
            'integrate_receipt':ref(root/'integrate.json'),'acceptance':ref(root/'actual-acceptance.json')}

def executable_lines(path):
    text=path.read_text(encoding='utf-8');tree=ast.parse(text);excluded=set()
    for node in ast.walk(tree):
        if isinstance(node,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and node.body:
            first=node.body[0]
            if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str):
                excluded.update(range(first.lineno,first.end_lineno+1))
    return [line for index,line in enumerate(text.splitlines(),1) if index not in excluded and line.strip() and not line.lstrip().startswith('#')]

def delta(before,after):
    left=[] if before is None else executable_lines(before);right=executable_lines(after)
    changes=list(difflib.ndiff(left,right))
    return {'added':sum(s.startswith('+ ') for s in changes),'removed':sum(s.startswith('- ') for s in changes)}

started=utc();assert sha(Q/'TRANSFER-MANIFEST.json')==M and sha(R/'implement.json')=='e732c54c4db4ecee9946d7abbc623454c88979f3d026366b98dcc3964739cff6'
assert sha(R/'apply_reviewed_status.py')==H and sha(R/'integrate_status.py')==I and sha(R/'ACCEPTED-SOURCE-BASELINE.json')==B
claim=read(R/RUN/'claims.json')['review'];assert claim['executor_id']==ACTOR and claim['workspace']==str(Q)
assert read(R/RUN/'state.json')['nodes']['review']['state']=='RUNNING'
m=read(Q/'TRANSFER-MANIFEST.json');allowed={'build/progress.json','handoff/continuity.json'}
assert m['author']=='/root' and m['source_root']==str(F) and m['candidate_root']==str(Q)
assert m['runtime_code_changes']==m['global_gate_or_requirement_changes']==0 and m['earlier_observations_preserved'] is True
assert set(m['application_paths'])==allowed and len(m['payloads'])==2 and {i['relative_path'] for i in m['payloads']}==allowed
assert {p.relative_to(Q).as_posix() for p in Q.rglob('*') if p.is_file()}==allowed|{'TRANSFER-MANIFEST.json'}
before={};after={};active_native={};candidate_native={'TRANSFER-MANIFEST.json':ordinary(Q/'TRANSFER-MANIFEST.json')};changes={}
for row in m['payloads']:
    rel=row['relative_path'];b=R/'before'/rel
    before[rel]=read(b);after[rel]=read(Q/rel)
    active_native[rel]=ordinary(F/rel);candidate_native[rel]=ordinary(Q/rel)
    assert active_native[rel]['sha256']==ordinary(b)['sha256']==row['active_before_sha256']
    assert candidate_native[rel]['sha256']==row['candidate_sha256']
    declared=dict(row['source_native_identity']);declared['mode']=stat.S_IMODE(declared['mode'])
    assert active_native[rel]['native_identity']==declared
    assert row['application_action']=='EXTEND_PRESERVE_BEFORE_IMAGE'
    assert all(equal(after[rel][key],value) for key,value in before[rel].items() if key not in row['allowed_changed_keys'])
    changes[rel]=leaf_changes(before[rel],after[rel])
    assert all(c['pointer'].split('/')[1] in row['allowed_changed_keys'] for c in changes[rel])
    assert set(after[rel])-set(before[rel])<=set(row['allowed_changed_keys'])
    hist=after[rel]['repository_execution_history_20261014']
    assert len(hist)==len(before[rel]['repository_execution_history_20261014'])+1
    assert equal(hist[:-1],before[rel]['repository_execution_history_20261014']) and equal(hist[-1]['previous_current_observation'],before[rel]['current_repository_execution_20261014'])
    assert after[rel]['accepted_source_baseline_20261014']==ref(R/'ACCEPTED-SOURCE-BASELINE.json')
old_ref='handoff/source_reco3nciliation_20261006_07.md';correct_ref='handoff/source_reconciliation_20261006_07.md'
work_changes=leaf_changes(before['build/progress.json']['work_packages'],after['build/progress.json']['work_packages'],'/work_packages')
assert work_changes==[{'pointer':'/work_packages/1/evidence_refs/39','before':old_ref,'after':correct_ref,'change':'VALUE'}]
assert old_ref.replace('3','',1)==correct_ref and len(old_ref)==len(correct_ref)+1
assert not (F/old_ref).exists();correct_native=ordinary(F/correct_ref)
repair=after['build/progress.json']['metadata_reference_repair_20261014']
assert repair['pointer']=='/work_packages/1/evidence_refs/39' and repair['before']==old_ref and repair['after']==correct_ref and repair['origin']=='UNESTABLISHED'
assert repair['preserved_current_before_image']=='.agents/runtime/ct4-20261014/before/build/progress.json'
bound(repair['observed_drift'])
continuity=after['handoff/continuity.json']
assert equal(continuity['historical_fields_before_ct3_20261014'],before['handoff/continuity.json']['historical_fields_before_ct3_20261014'])
for key,value in continuity['historical_fields_before_ct4_20261014'].items():assert equal(value,before['handoff/continuity.json'][key])
assert continuity['current_increment_tests']=='1479_CURRENT_SOURCE_CONTRACT_CASES_PASSED_ZERO_FAILURE_ERROR_SKIP_AT_RB_PERF_ACCEPTED_CUT;WHOLE_PRODUCT_ACCEPTANCE_OPEN'
facts=after['build/progress.json']['current_repository_execution_20261014'];assert equal(facts,continuity['current_repository_execution_20261014'])
assert facts['authoritative_repository']==str(F) and facts['display_identity']=='Project-AI: CETA' and facts['source_payloads']==290 and facts['product_modules']==74
head=subprocess.run(['git','rev-parse','HEAD'],cwd=F,capture_output=True,check=True,text=True).stdout.strip()
branch=subprocess.run(['git','branch','--show-current'],cwd=F,capture_output=True,check=True,text=True).stdout.strip()
assert head==facts['Git_HEAD']=='8ac404cdb2dd64c2dae974fbd25e13975b09295b' and branch==facts['branch']=='build/standalone'
assert datetime.fromisoformat(facts['recorded_at'])<=datetime.fromisoformat(claim['claimed_at'])
names={'wa1-20261014','hd2-20261014','gd3-20261014','rp1-20261014','rs-owner2-20261014','er1-20261014','hp10-20261014','rb-task1-20261014','perf1-20261014'}
assert set(facts['accepted_package_ledgers'])==names
ledgers={name:accepted(name) for name in sorted(names)}
assert equal(ledgers,facts['accepted_package_ledgers']) and m['accepted_source_ledger']==ledgers['perf1-20261014']
sp,_=bound(m['source_suite']);suite=read(sp);raw=sp.with_suffix('.txt').read_bytes()
assert suite['root']==str(F) and type(suite['tests_run']) is int and suite['tests_run']==1479
assert all(type(suite[k]) is int and suite[k]==0 for k in ('failures','errors','skips','exit_status'))
assert suite['expected_ids']==suite['executed_ids'] and len(set(suite['executed_ids']))==1479
assert hashlib.sha256(raw).hexdigest()==suite['output_sha256']
assert re.findall(r'^\S+ \((test_[^)]+)\)',raw.decode('utf-8-sig'),re.MULTILINE)==suite['executed_ids']
assert len(suite['imports'])==len({pin['module'] for pin in suite['imports']})==74
assert suite['native_census']['exit_status']==0 and suite['native_census']['result']['clear'] is True
assert suite['before_hashes']==suite['after_hashes']==suite['expected_payload_hashes'] and len(suite['after_hashes'])==290
source_native={rel:ordinary(F/rel) for rel in suite['after_hashes']};assert {k:v['sha256'] for k,v in source_native.items()}==suite['after_hashes']
for pin in suite['imports']:
    path=Path(pin['actual_path']);assert path.is_relative_to(F/'src/ceta') and ordinary(path)['sha256']==pin['sha256']==suite['after_hashes'][path.relative_to(F).as_posix()]
summary=facts['current_scoped_tests'];assert summary['sha256']==sha(sp) and summary['passed']==1479 and summary['complete_contract_suite'] is True and summary['whole_product_acceptance'] is False
assert all(type(summary[k]) is int and summary[k]==0 for k in ('failures','errors','skipped')) and equal(summary,continuity['latest_source_tests'])
dest,_=bound(summary['independent_destination_review']);assert read(dest)['decision']=='approved' and read(dest)['destination_suite_sha256']==sha(sp)
join,_=bound(summary['source_binding']);assert read(join)['after_hashes']==suite['after_hashes']
totals={'source_added':0,'source_removed':0,'tests_added':0};recomputed={}
for field,name,count in [('budget_candidate','rb-task1-20261014',276),('performance_candidate','perf1-20261014',384)]:
    fact=facts[field];assert fact['state']=='SOURCE_INTEGRATION_ACCEPTED' and fact['Source_application'] is True and fact['whole_unit_completion'] is False
    assert fact['ledger']==ledgers[name] and fact['independent_current_source_tests']==count
    cp,_=bound(fact['independent_candidate_review']);assert read(cp)['decision']=='approved'
    dp,_=bound(fact['independent_destination_review']);assert read(dp)['decision']=='approved'
    bound(fact['manifest'])
    fact_loc=facts['newly_integrated_LOC'][name];lp,_=bound(fact_loc['historical_preapplication_count_proof']);historic=read(lp)
    assert historic['Source_application'] is False and fact_loc['Source_application'] is True and fact_loc['accepted_integration']==ledgers[name]
    for key in totals:assert fact_loc[key]==historic[key];totals[key]+=fact_loc[key]
    root=F/'.agents/runtime'/name
    for rel in historic['paths']:
        before_path=None if rel.startswith('tests/') else root/'active-application/before'/(rel+'.source')
        recomputed[name+':'+rel]=delta(before_path,F/rel)
        assert recomputed[name+':'+rel]==historic['paths'][rel]
rs=facts['reservation_integrated_LOC'];rsh,_=bound(rs['historical_preapplication_count_proof']);historic_rs=read(rsh)
assert historic_rs['Source_application'] is False and rs['Source_application'] is True and rs['accepted_integration']==ledgers['rs-owner2-20261014']
assert (rs['source_added'],rs['source_removed'],rs['tests_added'])==(379,0,916)
assert all(historic_rs[k]==rs[k] for k in ('source_added','source_removed','tests_added'));bound(rs['actual_completion_helper'])
assert totals=={'source_added':409,'source_removed':4,'tests_added':556}
old_ids=read(F/'.agents/runtime/rs-owner2-20261014/active-application/destination-full-r1.json')['executed_ids']
new_ids=[i for i in suite['executed_ids'] if i not in set(old_ids)];assert len(new_ids)==63 and set(old_ids)<=set(suite['executed_ids'])
assert set(facts['remaining_product_requirements'])==set(before['build/progress.json']['current_repository_execution_20261014']['remaining_product_requirements'])-{'Integrate reviewed budget and performance candidates with full joined regressions'}
baseline=read(R/'ACCEPTED-SOURCE-BASELINE.json')
assert baseline['source_hashes']==suite['after_hashes'] and baseline['tests']==summary and baseline['accepted_integrations']==ledgers
assert baseline['Git_HEAD']==head and baseline['branch']==branch and baseline['recorded_at']==facts['recorded_at']
assert baseline['source_root']==str(F) and baseline['display_identity']==facts['display_identity'] and baseline['whole_product_acceptance'] is False
assert [baseline[k] for k in ('new_source_added','new_source_removed','new_test_added','new_methods')]==[409,4,556,63]
assert facts['accepted_source_baseline']==ref(R/'ACCEPTED-SOURCE-BASELINE.json')
nextmilestone=facts['next_major_acceptance_milestone'];assert equal(baseline['next_major_acceptance_milestone'],nextmilestone)
assert nextmilestone['state']=='ENGINEERING_IN_PROGRESS_ACCEPTANCE_NOT_RUN' and nextmilestone['runtime_effect_acceptance'] is False and nextmilestone['owner_approval_required_for_positive_runtime_journey'] is True
plan,_=bound(nextmilestone['plan']);plan_text=plan.read_text(encoding='utf-8')
tasks=re.findall(r'^\d+\. \*\*(RE-T\d+)\b',plan_text,re.MULTILINE);cases=re.findall(r'^\| (RE-\d+) \|',plan_text,re.MULTILINE)
assert len(tasks)==len(set(tasks))==nextmilestone['tasks']==32 and len(cases)==len(set(cases))==nextmilestone['acceptance_cases']==38
assert nextmilestone['activation_gates']==6;pr,_=bound(nextmilestone['Collaborative_Review']);assert read(pr)['decision']=='APPROVED_FOR_BOUNDED_ENGINEERING_IMPLEMENTATION'
wt=F/'.agents/runtime/wt1-20261014';assert read(wt/'wt1-20261014/state.json')['nodes']['review']['state']=='FAILED' and read(wt/'wt1-20261014/claims.json')=={}
wr,_=bound(nextmilestone['rejected_dependency']['review']);assert read(wr)['decision']=='rejected'
sys.path[:0]=[str(F/'tools')];import build_measurements
collected=build_measurements.collect(F);save(V/'actual-register-measurements-before.json',collected)
docs={key:read(F/rel) for key,rel in build_measurements.INPUTS.items()};old_docs=copy.deepcopy(docs);new_docs=copy.deepcopy(docs)
old_docs['progress']=before['build/progress.json'];new_docs['progress']=after['build/progress.json']
assert equal(build_measurements.measurements(old_docs),build_measurements.measurements(new_docs)) and collected['completion_inferred_from_applicability'] is False
globals_paths=['requirements/requirements.json','build/work_packages.json','build/gates.json','standards/lifecycle_coverage.json','acceptance/scenarios.json','policies/policy_registry.json','handoff/source_authority_register.json','PACKAGE_SUMMARY.json','architecture/components.json']
globals_native={rel:ordinary(F/rel) for rel in globals_paths}
assert all(ordinary(F/rel)==v for rel,v in source_native.items()) and all(ordinary(F/rel)==v for rel,v in active_native.items()) and all(ordinary(Q/rel)==v for rel,v in candidate_native.items())
proof={'executor':ACTOR,'started_at':started,'finished_at':utc(),'manifest':ref(Q/'TRANSFER-MANIFEST.json'),'source_suite':ref(sp),'baseline':ref(R/'ACCEPTED-SOURCE-BASELINE.json'),
    'claim':{k:claim[k] for k in ('executor_id','workspace','claimed_at','input_hash')},'source_native':source_native,'active_metadata_native':active_native,'candidate_native':candidate_native,
    'changed_json_leaf_counts':{k:len(v) for k,v in changes.items()},'changed_json_leaves':changes,'work_package_exact_leaf_repair':work_changes,'correct_evidence_file':{'relative_path':correct_ref,**correct_native},
    'actual_accepted_ledgers':ledgers,'globals_native':globals_native,'full_raw1479_ids_exact':True,'module_count':74,'new_method_ids':new_ids,'recomputed_LOC':recomputed,
    'previous_observations_and_CT3_history_preserved':True,'global_measurement_axes_preserved':True,'actual_collection':ref(V/'actual-register-measurements-before.json'),
    'next_milestone_tasks':tasks,'next_milestone_cases':cases,'next_milestone_acceptance':False,'Source_mutations':[],'candidate_mutations':[],'exit_status':0,
    'qualification':'Independent exact current Source/native/JSON/ledger/raw review. Root full1479 inspected, not repeated. Current input collect(F) executed. Only historical work package reference leaf is corrected; native publication and separate installed source completion remain pending.'}
save(V/'candidate-inspection.json',proof)
print(json.dumps({'inspection_sha256':sha(V/'candidate-inspection.json'),'leaf_counts':proof['changed_json_leaf_counts'],'source_payloads':290,'full_methods':1479,'exit_status':0}),flush=True)

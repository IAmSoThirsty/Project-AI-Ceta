"""Freeze and submit the distinct CT3 review after finite current proof."""
from ct3_support import *
import ast
M='2773d204475a35934f3f0b80ef110126761b66fb74e9a6065c51f40e4c19de7e'
H='e4fc059ba1b0d0e87f1d6a52f0b7e9148f8062cd832b2ca1f7f06caa1ef88a70'
I='90aba6ca15bcce97676bd29bb34026044ce63f0f9a328ca03d4f181cb2433f32'
assert sha(Q/'TRANSFER-MANIFEST.json')==M and sha(R/'apply_reviewed_status.py')==H and sha(R/'integrate_status.py')==I
inspection=read(V/'candidate-inspection.json');tests=read(V/'consumer-native-tests.json')
assert inspection['exit_status']==tests['exit_status']==0 and tests['tests_run']==8 and tests['expected_ids']==tests['executed_ids']
assert all(tests[key]==0 for key in ('failures','errors','skips'))
parent=F/'.agents/runtime/rs-owner2-20261014/root-integration/apply_reviewed_reservations.py'
assert sha(parent)=='af88b03f04593ae1a20d785bcc2fb0f8f604b68a5a36cce43b62d78cc4d848ed'
def tail(path):
 tree=ast.parse(path.read_text(encoding='utf-8'));main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 at=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Expr) and ast.unparse(n.value)=='native.fs.safe_components(OUT, allow_missing=True)')
 return main.body[at:]
old=tail(parent);new=tail(R/'apply_reviewed_status.py')
class DescribeCT3(ast.NodeTransformer):
 def visit_Constant(self,node):
  if isinstance(node.value,str):node.value=node.value.replace('FIVE_RESERVATION_PATHS_APPLIED_WITH_ACCEPTED_BASE_RETAINED_AWAITING_DESTINATION_VERIFICATION','TWO_STATUS_PATHS_APPLIED_WITH_ACCEPTED_SOURCE_RETAINED_AWAITING_DESTINATION_VERIFICATION').replace('exact five paths','exact two metadata paths').replace('actual_reservation_paths_applied','actual_status_paths_applied')
  return node
expected=[DescribeCT3().visit(n) for n in old]
assert len(new)==len(expected) and len(new)>6
assert all(ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False) for index,(a,b) in enumerate(zip(new,expected)) if index!=2)
assert ast.unparse(new[2]).startswith("save(OUT / 'JOINED-SOURCE.json',")
source_module=F/'tools/build_measurements.py';spec=importlib.util.spec_from_file_location('ct3_actual_register_collection',source_module);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
collected=module.collect(F);assert len(collected['verified_input_sha256'])==8
progress=read(F/'build/progress.json')
assert collected['implementation']['runtime_state']==progress['runtime_implementation'] and collected['full_product']==progress['goal_state']
assert collected['conformance_verification']['installed_state']==progress['installed_qualification']=='NOT_RUN'
assert collected['completion_inferred_from_applicability'] is False
save(V/'actual-register-measurements-before.json',collected)
mechanism={'executor':ACTOR,'decision':'approved','exit_status':0,'manifest_sha256':M,'publication_script_sha256':H,'integration_script_sha256':I,'native_primitive_sha256':'4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77','parent_publication_sha256':sha(parent),'preservation_staging_publication_backup_and_failure_AST_unchanged':True,'changed_join':'Metadata-specific source286 plus exact2 before/after hashes; only defined bound values','scope_guards':['Actual Root/F integrate claim and admitted distinct review/validate','Exact immutable manifest, reviewer/helper SHA, current Source286 and native before identities','Only two existing JSON paths, fsynced distinct stages/logical originals, ReplaceFileW flags0 with fresh backups','Full filesystem reconciliation of two paths after partial outcome; no automatic rollback or group atomicity claim'],'completion_checks':['Strict local/persisted review type/value equality and approved distinct actor','Exact integration helper/self SHA and publication approval pins','Both actual target SHA matches, two logical/native originals with exact IDs/bytes/mtime/full mode','Every old unapproved JSON field and previous observation retained','Actual eight-document collect(F) and runtime/installed/goal equality separate from three fixture unit tests','Exact full Source286 hashes retained; actual Source snapshot delta precisely two metadata paths','Strict installed integrate completion and actual all6 SUCCEEDED sequence13 claims{} readback'],'actual_before_collection':ref(V/'actual-register-measurements-before.json'),'native_execution':ref(V/'consumer-native-tests.json'),'qualification':'Static full publisher/completion inspection plus actual isolated native primitive cases; production F publisher/integration not executed by reviewer; concurrent arbitrary mutation is not claimed atomically frozen'}
save(V/'publication-helper-review.json',mechanism)
summary={'executor':ACTOR,'decision':'approved','exit_status':0,'observed_at':utc(),'manifest_sha256':M,'publication_script_sha256':H,'integration_script_sha256':I,'candidate_inspection':ref(V/'candidate-inspection.json'),'independent_tests':ref(V/'consumer-native-tests.json'),'tests_run':8,'fixture_consumer_tests':3,'actual_native_publication_cases':5,'actual_current_repository_document_collection':ref(V/'actual-register-measurements-before.json'),'changed_json_leaf_counts':inspection['changed_json_leaf_counts'],'source_tests_inspected':1416,'source_payloads_rehashed':286,'source_module_paths_pinned':74,'every_prior_observation_preserved':True,'all_global_and_requirement_work_package_axes_preserved':True,'source_root':str(F),'source_writes':[],'candidate_writes':[],'new_product_source_LOC':0,'pending_work':{'RB':'Author/review succeeded; Source integration pending','PERF':'Exact recorded 17:01:56.902851 UTC sequence8/reviewRUNNING observation preserved, Source integration pending','history':'W043/W044/W045 held; HP10 accepted operational tool; source/history consolidation still partial','installed_and_whole_product':'Open; global qualification/authority gates retained'},'prior_failures':[ref(V/'preparation-findings.json'),ref(V/'root-suite-readproof.json')],'review_limits':['1416 full Source methods are independently inspected Root execution, not a second reviewer full run','Eight current source documents collected before metadata application; reviewed completion helper collects actual updated documents after publication','Initial delivery-only validate_package NOT_STARTED invariant is not qualified against an implementation registry','Directory observation method differences and first missing author after-tree cause remain recorded in HP10 evidence','Two-path publication can be partial; exact originals and recovery state must be retained'],'release_scope':'Exact candidate, e4fc059 publisher and 90aba6 integration helper may proceed only through actual Root runtime gates and Source claim; no additional code, policy or capture approval'}
save(V/'REPORT.json',summary)
claim=read(R/RUN/'claims.json')['review'];assert claim['executor_id']==ACTOR and claim['workspace']==str(Q)
sys.path.insert(0,r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt,load_receipt
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
changed=_changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')));assert changed==[]
assert all(ordinary(F/rel)==value for rel,value in inspection['source286_native_observations'].items())
assert all(ordinary(F/rel)==value for rel,value in inspection['status_before_native'].items())
assert sha(Q/'TRANSFER-MANIFEST.json')==M and sha(R/'apply_reviewed_status.py')==H and sha(R/'integrate_status.py')==I
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':ACTOR,'started_at':claim['claimed_at'],'finished_at':utc(),'input_hash':claim['input_hash'],'changed_files':changed,'result':summary|{'manifest_sha256':M,'integration_script_sha256':I,'report':ref(V/'REPORT.json'),'publication_helper_review':ref(V/'publication-helper-review.json')},'commands':[{'command':str(PY)+' -B -X utf8 '+str(V/'inspect_candidate.py')+' '+M,'exit_status':0},{'command':str(PY)+' -B -X utf8 '+str(V/'run_narrow_tests.py'),'exit_status':0},{'command':str(PY)+' -B -X utf8 '+str(V/'finish_review.py')+' (native AST join, actual eight-document collection, immutable Source and strict receipt validation)','exit_status':0}],'validations':[{'name':name,'passed':True} for name in ('exact660_leaf_changes_prior_observations_and_global_axes','accepted_source1416_raw_unique_ids_and286_native_hashes','seven_accepted_ledgers_and_RB_PERF_exact_recorded_status','three_pure_consumer_unit_and_five_actual_native_cases','actual_eight_document_collection_separate_from_fixture_cases','exact_two_path_native_publisher_and_completion_helper','no_Source_candidate_or_environment_writes')],'exit_status':0,'decision':'approved'}
kwargs={'run_id':RUN,'node_id':'review','executor_id':ACTOR,'input_hash':claim['input_hash'],'claimed_at':claim['claimed_at'],'node':read(R/RUN/'graph.json')['graph']['nodes']['review']}
validate_receipt(receipt,**kwargs);save(V/'review.json',receipt);validate_receipt(load_receipt(V/'review.json'),**kwargs)
response=invoke('actual-review-complete',['node','complete',RUN,'review',str(V/'review.json')])
state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json');assert state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={}
stored=read(R/RUN/'receipts/review.json');assert json.dumps({k:stored[k] for k in receipt},sort_keys=True,allow_nan=False)==json.dumps(receipt,sort_keys=True,allow_nan=False)
save(V/'review-readback.json',{'observed_at':utc(),'actual_sequence':state['sequence'],'actual_review_state':state['nodes']['review']['state'],'actual_claims':claims,'persisted_review_decision':stored['decision'],'receipt':ref(V/'review.json'),'report':ref(V/'REPORT.json'),'helper_review':ref(V/'publication-helper-review.json'),'state_native':ordinary(R/RUN/'state.json'),'claims_native':ordinary(R/RUN/'claims.json')})
print(json.dumps({'decision':'approved','actual_sequence':9,'review':'SUCCEEDED','claims':{},'review_sha256':sha(V/'review.json'),'report_sha256':sha(V/'REPORT.json'),'helper_review_sha256':sha(V/'publication-helper-review.json'),'readback_sha256':sha(V/'review-readback.json')}),flush=True)

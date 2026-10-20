"""Read actual CT4 two-path publication and execute the exact nonmutating prefix."""
from ct4_support import *
import ast, re
M='2e8cdfd1bcd8e1b2c250c33f156df450c03bbc34f60efbdce90c9de3edf08efe'
H='d667f4edcfcba670af85ee06620ac3ee84c713d4f599e36d6cd36d215ca34664'
I='447f7a9149781e1b71aabf7f8bbeb3c54859fafd7f201292909746d117bdb3ed'
assert sha(Q/'TRANSFER-MANIFEST.json')==M and sha(R/'apply_reviewed_status.py')==H and sha(R/'integrate_status.py')==I
inspection=read(V/'candidate-inspection.json');manifest=read(Q/'TRANSFER-MANIFEST.json')
OUT=R/'active-application';journal=read(OUT/'APPLIED.json');state=read(R/RUN/'state.json')
assert journal['manifest_sha256']==M and len(journal['completed'])==len(journal['before_images'])==2
assert journal['review_sha256']==sha(V/'review.json') and journal['helper_review_sha256']==sha(V/'publication-helper-review.json')
assert state['nodes']['integrate']['state'] in {'RUNNING','SUCCEEDED'}
script=R/'integrate_status.py';tree=ast.parse(script.read_text(encoding='utf8'))
stop=next(i for i,node in enumerate(tree.body) if isinstance(node,ast.Assign) and ast.unparse(node.targets[0])=='sys.path[:0]')
assert all(not isinstance(node,ast.ImportFrom) or node.module not in {'taar.orchestration_runtime','taar.orchestration_receipts'} for node in tree.body[:stop])
prefix=ast.fix_missing_locations(ast.Module(body=tree.body[:stop],type_ignores=[]))
argv=list(sys.argv)
try:
    sys.argv=[str(script),'complete']
    exec(compile(prefix,str(script),'exec'),{'__file__':str(script),'__name__':'ct4_actual_readonly_completion_prefix'})
finally:sys.argv=argv
originals={}
for row in manifest['payloads']:
    rel=row['relative_path'];assert ordinary(F/rel)['sha256']==ordinary(Q/rel)['sha256']==row['candidate_sha256']
    backup=OUT/'native-backups'/(rel+'.original');logical=OUT/'before'/(rel+'.source')
    native=ordinary(backup);assert native==inspection['active_metadata_native'][rel]
    assert ordinary(logical)['sha256']==row['active_before_sha256']
    originals[rel]={'native_backup':ref(backup),'native_identity':native['native_identity'],'logical_before':ref(logical)}
assert all(ordinary(F/rel)==row for rel,row in inspection['source_native'].items())
assert all(ordinary(Q/rel)==row for rel,row in inspection['candidate_native'].items())
assert all(ordinary(F/rel)==row for rel,row in inspection['globals_native'].items())
sys.path.insert(0,str(F/'tools'));import build_measurements
collected=build_measurements.collect(F);previous=read(V/'actual-register-measurements-before.json')
for key,value in previous.items():
    if key not in {'verified_input_sha256','observed_at_utc'}:assert collected[key]==value,('MEASUREMENT_AXIS_CHANGED',key)
assert {rel for rel in previous['verified_input_sha256'] if previous['verified_input_sha256'][rel]!=collected['verified_input_sha256'][rel]}=={'build/progress.json'}
save(V/'actual-register-measurements-delivered.json',collected)
save(V/'delivered-source-review.json',{'executor':ACTOR,'reviewed_at':utc(),'decision':'approved','exit_status':0,'source_root':str(F),
    'manifest_sha256':M,'publisher_sha256':H,'integration_script_sha256':I,'actual_APPLIED':ref(OUT/'APPLIED.json'),
    'actual_nonmutating_completion_prefix_executed':True,'prefix_stops_before':'sys.path[:0] and subsequent consumer file outputs and actual TAAR snapshot/completion',
    'retained_source_payloads':290,'native_and_logical_originals':originals,'actual_current_collection':ref(V/'actual-register-measurements-delivered.json'),
    'global_product_axes_preserved':True,'old_observations_and_CT3_history_preserved':True,'one_work_package_reference_character_deleted':True,
    'candidate_and_Source290_native_conservation':True,'actual_review_sequence':9,'Root_integration_state_at_observation':state['nodes']['integrate']['state'],
    'Source_mutations':[],'actual_lifecycle_transitions':[],'qualification':'Actual delivered metadata targets/native originals and exact read-only completion prefix verified independently. Root consumer unit receipt, installed exact two-path delta and actual seq13 completion must still be read back before final seal.'})
print(json.dumps({'decision':'approved','delivered_review_sha256':sha(V/'delivered-source-review.json'),'actual_APPLIED_sha256':sha(OUT/'APPLIED.json'),'exact_prefix':'PASS'}),flush=True)

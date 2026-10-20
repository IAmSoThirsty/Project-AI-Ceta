"""Admit one three-path AC3 environment variant; no profile or launch retry."""
from ac3_support import *
read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
assert not Q.exists()
parent=F/'.agents/ac2-20261014';parent_runtime=F/'.agents/runtime/ac2-20261014'
manifest=read(parent/'TRANSFER-MANIFEST.json')
assert sha(parent/'TRANSFER-MANIFEST.json')=='41a2c6ab046279a581fe3ff99b126b84d7485d8369108f7abbf53634da254dda'
parent_facts={name:ordinary(parent/name) for name in manifest['payloads']}
assert parent_facts==manifest['payloads'] and len(parent_facts)==294
state=read(parent_runtime/'ac2-20261014/state.json');claims=read(parent_runtime/'ac2-20261014/claims.json')
assert state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={}
baseline=F/'.agents/runtime/ct4-20261014/ACCEPTED-SOURCE-BASELINE.json'
source={name:ordinary(F/name) for name in read(baseline)['source_hashes']}
assert len(source)==290 and {name:row['sha256'] for name,row in source.items()}==read(baseline)['source_hashes']
choices={name:(F/name,'Source290') for name in source}
for name in manifest['eligible_paths']:choices[name]=(parent/name,'accepted_AC2')
assert len(choices)==294
scope=['src/ceta/supervisor/isolated_worker.py','tests/contract/test_isolated_worker.py','contracts/ISOLATED_WORKER_V1.md']
Q.mkdir();invoke(['run','init','--root','T:\\','--scope',str(Q),'--run-id',RUN],'run-init')
claim('discover')
write_new(R/'SOURCE-INPUTS.json',{'recorded_at':utc(),'Source_payloads':source,'Source_baseline':reference(baseline),
    'AC2_manifest':reference(parent/'TRANSFER-MANIFEST.json'),'AC2_payloads':parent_facts,
    'AC2_state':ordinary(parent_runtime/'ac2-20261014/state.json'),'AC2_claims':ordinary(parent_runtime/'ac2-20261014/claims.json'),
    'historical_profile_attempt':reference(parent_runtime/'profile-tool-repair-r2/profile-qualification-7b716b95d15f440a90d6be98a666014c/RESULT.json'),
    'selected_dependencies':{name:{'owner':owner,'facts':ordinary(path)} for name,(path,owner) in choices.items()},
    'HEAD':fs.text_git(F,'rev-parse','HEAD'),'branch':fs.text_git(F,'branch','--show-current'),'Source_application':False})
complete('discover',{'source_inputs':reference(R/'SOURCE-INPUTS.json')},
    [{'command':'Read exact Source290, accepted AC2294 and the retained single authorized profile-attempt failure','exit_status':0}],
    [('source_parent_native_identities_and_actual_accepted_AC2_bound',True)])
claim('plan')
write_new(R/'TASK-BINDING.json',{'recorded_at':utc(),'author':ACTOR,'scope':scope,'task':'AC3 narrow Windows-observed LocalAppData environment variant and read-only error203 diagnosis',
    'source_count':290,'staged_payloads':294,'native_profile_Create_Delete_authority':False,'restricted_CreateProcess_retry_authority':False,
    'allowed_native_tests':'Read-only Windows known-folder/profile/ABI observations, real disposable resource cleanup, controlled negative calls before restricted creation. The previous actual restricted-launch case is retained but not executed without new authority.',
    'cause_status':'UNESTABLISHED; LOCALAPPDATA is a documentation-supported hypothesis, not a verified internal error203 cause.',
    'independent_reviewer':'/root','Source_application':False,'reused_LOC_credit':0})
complete('plan',{'binding':reference(R/'TASK-BINDING.json')},[{'command':'Bind exact three paths and no-profile/no-retry boundary','exit_status':0}],
    [('bounded_minimal_variant_and_reserved_positive_qualification_explicit',True)])
owned=claim('implement');assert owned['baseline_snapshot']=={}
for name,(path,owner) in choices.items():
    target=Q/name;target.parent.mkdir(parents=True,exist_ok=True);fs.write_new(target,fs.read_bytes(path))
for name in scope:
    target=R/'before-images'/name;target.parent.mkdir(parents=True,exist_ok=True);fs.write_new(target,fs.read_bytes(Q/name))
write_new(R/'IMPLEMENTATION-STARTED.json',{'recorded_at':utc(),'claim_input_hash':owned['input_hash'],'staged_payloads':294,'Source_application':False})
print(json.dumps({'implement':'RUNNING','staged':294,'Source':290,'scope':scope}),flush=True)

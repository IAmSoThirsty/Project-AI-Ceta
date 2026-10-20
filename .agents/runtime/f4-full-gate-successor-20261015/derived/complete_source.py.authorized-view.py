"""Accept only the independently checked delivered native-library foundation."""
from foundation_support import *

def main():
    manifest=read(Q/'TRANSFER-MANIFEST.json')
    approved=approved_review()
    assert approved['decision']=='approved' and approved['result']['manifest_sha256']==sha(Q/'TRANSFER-MANIFEST.json')
    assert approved['result']['reviewed_scripts']['complete_source.py']==sha(R/'complete_source.py')
    assert __successor_delivery_verified is True
    full_path=__successor_full_path;full=read(full_path)
    __require_successor_result(full)
    assert full['exit_status']==0 and full['failures']==full['errors']==full['skips']==0
    assert full['root']==str(F) and full['mode']=='destination' and full['all_product_module_count']==87
    assert full['mandatory_full_gate_complete'] is True and full['deferred_ids']==[]
    assert full['full_expected_ids']==full['expected_ids'] and full['all_owned_lifetimes_store_clock_bindings_closed'] and full['native_API_custody_accounted'] and full['all_controlled_allocations_released'] and full['all_native_approval_lifetimes_closed'] and not full['forbidden_calls']
    baseline=read(F/'.agents/runtime/perf1-20261014/active-application/destination-full-r1.json')['expected_ids']
    assert len(baseline)==1479 and set(baseline)<=set(full['expected_ids'])
    assert full['source_unchanged'] and full['all_native_throttle_lifetimes_closed'] and not full['remaining_new_threads']
    assert full['tests_run']==len(full['expected_ids'])==len(full['executed_ids'])==len(full['stopped_ids'])
    assert len(full['expected_ids'])==len(set(full['expected_ids'])) and full['expected_ids']==full['executed_ids']==full['stopped_ids']
    required=read(safe_proof(manifest['required_source_tests']))
    assert full['expected_ids']==required['required_ids']
    auxiliary=read(safe_proof(manifest['auxiliary_test_tools']))
    assert full['auxiliary_tools_before']==full['auxiliary_tools_after']=={name:row['source'] for name,row in auxiliary['members'].items()}
    for name,row in auxiliary['members'].items():
        assert ordinary(F/name)==row['source'] and ordinary(Q/name)==row['candidate']
    applied=read(R/'active-application/APPLIED.json')
    pins={name:row['candidate']['sha256'] for name,row in manifest['payloads'].items()}
    assert full['after_hashes']==full['before_hashes']==pins
    for name,value in applied['after'].items():assert ordinary(F/name)==value==full['after'][name]
    for name in manifest['application_paths']:
        before=manifest['payloads'][name]['before']
        if before is not None:
            require_native_original(R/'active-application/native-originals'/(name+'.original'),before)
    delivered_path=__successor_delivery_path;delivered=read(delivered_path)
    assert delivered['decision']=='approved' and delivered['executor_id'] not in {AUTHOR,INTEGRATOR}
    assert delivered['manifest_sha256']==sha(Q/'TRANSFER-MANIFEST.json') and delivered['source_full_result_sha256']==sha(full_path)
    assert delivered['applied_sha256']==sha(R/'active-application/APPLIED.json') and delivered['source_payload_hashes']==pins
    result={'accepted_at':utc(),'source_root':str(F),'accepted_profile':'native dependency libraries and typed contracts',
      'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'source_hashes':pins,'source_native_identities':applied['after'],
      'source_payloads':336,'product_modules':87,'full_contract_tests':full['tests_run'],
      'full_result':reference(full_path),'delivered_review':reference(delivered_path),
      'prior_accepted_baseline':reference(F/'.agents/runtime/ct4-20261014/ACCEPTED-SOURCE-BASELINE.json'),
      'new_assembly_source_LOC':0,'actual_first_source_integration_LOC':manifest['source_integration_LOC'],
      'activation_ready':False,'real_effect_runtime_accepted':False,
      'open_prerequisites':['positive worker isolation','genuine native owner enrollment and per-effect approval',
        'genuine native owner/session authority provider and retained admission composition','separate native observer','public runtime composition and real-effect acceptance']}
    result['successor_full_gate']=__successor_gate_bindings
    result['whole_fixture_preservation_accepted']=False
    result['metadata_issue_waived']=False
    write_new(__completion_runtime/'ACCEPTED-SOURCE-BASELINE.json',result)
    response=complete('integrate',{'accepted_baseline':reference(__completion_runtime/'ACCEPTED-SOURCE-BASELINE.json'),
        'payloads':336,'full_contract_tests':full['tests_run'],'real_effect_runtime_accepted':False},
      [{'command':__successor_actual_command,'exit_status':0}],
      [('all_336_actual_Source_hashes_and_native_identities_match',True),('independent_delivered_review_approved',True),
       ('all_original_1479_contract_cases_retained_and_complete_suite_passes',True),('only_49_reviewed_Source_paths_changed',True)])
    assert read(R/RUN/'claims.json')=={}
    state=read(R/RUN/'state.json');assert state['sequence']==13 and all(value['state']=='SUCCEEDED' for value in state['nodes'].values())
    write_new(__completion_runtime/'ACTUAL-ACCEPTANCE.json',{'recorded_at':utc(),'response':response,'state':state,
       'integrate_receipt':reference(R/RUN/'receipts/integrate.json'),'accepted_baseline':reference(__completion_runtime/'ACCEPTED-SOURCE-BASELINE.json')})
    print(json.dumps({'accepted':True,'payloads':336,'tests':full['tests_run'],'claims':{}}),flush=True)

if __name__=='__main__':main()

"""Read-only frozen BR3 integrity, no collection or canonical test execution."""
from pathlib import Path
import json
import run_broader as b
W=b.W;m=json.loads((W/'MANIFEST.json').read_bytes())
assert m['run_id']==b.RUN and m['author_controls']==55 and m['collected_tests']==510
for name,pin in m['work_hashes'].items():assert b.o.stable(W/name)['sha256']==pin,('work drift',name)
for name,pin in m['external_pins'].items():assert b.sha(Path(name))==pin,('support drift',name)
allowed={'MANIFEST.json','PREPARED-DRIVER.stdout','PREPARED-DRIVER.stderr','PREPARED-PROCESS.json',
    'AUTHOR-COMPLETION-RECEIPT.json','FREEZE-DRIVER.stdout','FREEZE-DRIVER.stderr','FREEZE-PROCESS.json'}
assert set(m['post_freeze_outputs'])==allowed
actual=b.o.snapshot(W)
assert set(actual)-allowed==set(m['work_observation']),'work entry set changed'
b.o.preservation(m['work_observation'],actual)
value=b.packet();binding=json.loads((W/'BINDING.json').read_bytes());fresh=b.source_observation(binding)
assert binding['control']==str(b.B/'control')
assert binding['graph_fingerprint']=='38a70f9069edec1aeb7daff0dbd491a474891ac5997d9a69a7ceda296aa4740e'
freeze=json.loads((W/'FREEZE-OBSERVATION.json').read_bytes())
assert freeze['source_before']==freeze['source_after']==fresh and len(binding['source_native'])==562
assert freeze['read_only_failed_JS9_preserved'] and len(binding['read_only_fixtures'])==1
collection=json.loads((W/'COLLECTION.json').read_bytes());ids=collection['test_ids']
previous=value['exact_cohort_predecessor'];assert b.sha(Path(previous['path']))==previous['sha256']
assert ids==json.loads(Path(previous['path']).read_bytes())['test_ids']
assert len(ids)==len(set(ids))==collection['tests_collected']==m['collected_tests']==510
assert collection['selected']==value['selected'] and len(collection['test_modules'])==26
assert collection['ordinary_imports'] and not collection['ROOT_override'] and not collection['module_overlay'] and not collection['test_bodies_executed']
assert collection['exact_ordered_BR1_ids_preserved']
for name,identity in collection['test_modules'].items():assert identity['origin']==str(b.F/'tests/contract'/(name+'.py'))
for identity in collection['dependencies'].values():
    if identity['file']:assert b.r.stable(Path(identity['origin']))[0]==identity['native']
for name,identity in collection['product_modules'].items():
    if identity['file']:assert b.r.stable(Path(identity['origin']))[0]==identity['native']
    else:
        assert name=='ceta.effects' and identity['namespace_path']==str(b.F/'src/ceta/effects')
        assert identity['loader']=='NamespaceLoader' and identity['namespace_init_absent'] is True
        path=Path(identity['namespace_path']);b.o.ancestors(b.F,path)
        assert b.o.native(b.o.plain(path))==identity['directory_native']
        try:b.o.physical(path/'__init__.py').lstat()
        except FileNotFoundError:pass
        else:raise AssertionError('namespace __init__.py unexpectedly appeared')
assert b.r.stable(Path(collection['sqlite_static_binary']['path']))[0]==collection['sqlite_static_binary']['native']
assert collection['sqlite_static_binary']['loaded_by_preparation'] is False
controls=json.loads((W/'CONTROLS-FINAL.json').read_bytes())
assert controls['tests']==55 and controls['failures']==controls['errors']==controls['skips']==0
assert controls['successful'] and controls['process_exit_status']==0
assert controls['selected']==controls['started']==controls['stopped'] and len(set(controls['selected']))==55
assert controls['source_before']==controls['source_after']
for name,pin in controls['source_after'].items():assert b.sha(W/name)==pin
assert not controls['canonical_test_bodies_executed'] and not controls['canonical_fixture_writes']
old_controls=json.loads((Path(value['rejected_broader_preparation']['root'])/'work/CONTROLS-FINAL.json').read_bytes())
assert old_controls['tests']==44
assert [name for name in controls['selected'] if name in old_controls['selected']]==old_controls['selected']
assert len([name for name in controls['selected'] if '.test_BR3_' in name])==11
prior=json.loads((W/'PRIOR-EVIDENCE.json').read_bytes())
assert prior['journal']['actual_exit_status']==0 and prior['journal']['tests']==33 and prior['journal']['all_actual_nodes_succeeded']
assert prior['timing']['run']=='ceta-tm23-r2' and prior['timing']['actual_case_executions']==1
assert prior['timing']['failed_predecessor_preserved'] and prior['timing']['predecessor_canonical_executions']==0
assert prior['timing']['diagnosis']['unchanged_bound_ns']==50000000
assert prior['failed_broader']['actual_exit_status']==1 and prior['failed_broader']['closed_as_failed']
assert prior['failed_broader']['whole_validation_passed'] is False and prior['failed_broader']['success_seal_absent']
assert prior['failed_broader']['original_failed_file_path']=='UNKNOWN_NOT_RECORDED'
rejected=prior['rejected_broader_preparation']
assert rejected['terminal_success'] is False and rejected['canonical_test_bodies_executed']==0
assert rejected['review']['decision']=='rejected' and rejected['all_actual_claims_closed']
assert rejected['whole_observation_rechecks_required_at_freeze_and_prepared_verification'] and rejected['nested_disposable_entries_are_data_not_runtime_support']
assert b.o.snapshot(Path(value['rejected_broader_preparation']['root'])/'work')==rejected['work_observation'],'retained BR2 complete work drift'
assert json.loads((W/'PIN-PRIOR-PROCESS.json').read_bytes())['exit_status']==1
assert json.loads((W/'PIN-PRIOR-R2-PROCESS.json').read_bytes())['exit_status']==0
for name,pin in prior['external_pins'].items():assert b.sha(Path(name))==pin
assert m['full_product_acceptance'] is False and m['canonical_tests_executed']==0
for name in m['python_sources']:compile((W/name).read_bytes(),str(W/name),'exec')
print('PREPARED PASS:55 disposable controls, all44 prior IDs plus11 hostile custody cases;exact ordered510 canonical IDs collected only;562 source/status/native/Git/index conserved;closed failed BR1 and read-only oldJS9 preserved;directional Win32 mode rule, complete traversal and explicit return-False body custody and all secondary faults;all acceptance remains open')

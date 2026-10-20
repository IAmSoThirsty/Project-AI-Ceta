"""Adapt exact accepted status helpers without substituting digits inside hashes."""
from pathlib import Path
import ast, hashlib, json

R=Path(__file__).resolve().parent
F=R.parents[2]
OLD=F/'.agents/runtime/ct3-20261014'
Q=F/'.agents/ct4-20261014'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
pins={'apply_reviewed_status.py':'e4fc059ba1b0d0e87f1d6a52f0b7e9148f8062cd832b2ca1f7f06caa1ef88a70',
      'integrate_status.py':'90aba6ca15bcce97676bd29bb34026044ce63f0f9a328ca03d4f181cb2433f32'}
manifest=Q/'TRANSFER-MANIFEST.json'
assert read(R/'ct4-20261014/state.json')['nodes']['implement']['state']=='SUCCEEDED'
assert read(R/'ct4-20261014/claims.json')=={}
prepared={}
for name,pin in pins.items():
    assert sha(OLD/name)==pin
    text=(OLD/name).read_text(encoding='utf-8').replace('ct3-20261014','ct4-20261014')
    text=text.replace('rs-owner2-20261014','perf1-20261014')
    text=text.replace('historical_fields_before_ct3_20261014','historical_fields_before_ct4_20261014')
    text=text.replace("assert review['decision'] == 'approved' and review['exit_status'] == 0",
                      "assert review['decision'] == 'approved' and type(review['exit_status']) is int and review['exit_status'] == 0")
    text=text.replace("assert helper['decision'] == 'approved' and helper['exit_status'] == 0",
                      "assert helper['decision'] == 'approved' and type(helper['exit_status']) is int and helper['exit_status'] == 0")
    if name=='apply_reviewed_status.py':
        old="'2773d204475a35934f3f0b80ef110126761b66fb74e9a6065c51f40e4c19de7e'"
        assert text.count(old)==1
        text=text.replace(old,repr(sha(manifest)))
    for old,new in (('== 1416','== 1479'),('== 286','== 290'),
                    ("'source_hashes_retained': 286","'source_hashes_retained': 290"),
                    ("'retained_source_payloads': 286","'retained_source_payloads': 290"),
                    ("'code_payloads_retained': 286","'code_payloads_retained': 290"),
                    ('previous1416_Source_run_retained','previous1479_Source_run_retained'),
                    ('metadata_consumer_tests_and_source286_conservation','metadata_consumer_tests_and_source290_conservation')):
        text=text.replace(old,new)
    if name=='integrate_status.py':
        anchor="    assert all(after[key] == value for key, value in before.items() if key not in item['allowed_changed_keys'])"
        assert text.count(anchor)==1
        text=text.replace(anchor,anchor+'''
    baseline_reference=after['accepted_source_baseline_20261014']
    assert baseline_reference['repository_relative_path']=='.agents/runtime/ct4-20261014/ACCEPTED-SOURCE-BASELINE.json'
    assert baseline_reference['sha256']==sha(R/'ACCEPTED-SOURCE-BASELINE.json')
    assert after['current_repository_execution_20261014']['budget_candidate']['Source_application'] is True
    assert after['current_repository_execution_20261014']['performance_candidate']['Source_application'] is True
    assert after['current_repository_execution_20261014']['next_major_acceptance_milestone']['runtime_effect_acceptance'] is False
    if relative=='build/progress.json':
        import copy
        assert before['work_packages'][1]['evidence_refs'][39]=='handoff/source_reco3nciliation_20261006_07.md'
        assert after['work_packages'][1]['evidence_refs'][39]=='handoff/source_reconciliation_20261006_07.md'
        reverted=copy.deepcopy(after['work_packages'])
        reverted[1]['evidence_refs'][39]=before['work_packages'][1]['evidence_refs'][39]
        assert reverted==before['work_packages']
''')
    ast.parse(text)
    with (R/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    prepared[name]=sha(R/name)
with (R/'publication-lineage.json').open('x',encoding='utf-8') as stream:
    json.dump({'parent_pins':pins,'prepared':prepared,'manifest_sha256':sha(manifest),
               'target_source_cases':1479,'target_source_payloads':290,
               'digit_substitution_inside_hashes':False,'Source_mutations':[]},stream,indent=2)
    stream.write('\n')
print(json.dumps(prepared),flush=True)

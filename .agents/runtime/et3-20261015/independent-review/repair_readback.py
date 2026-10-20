"""Preserve failed reviewer metadata oracle; use installed exact hash domain."""
from review_support import *
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
old=D/'readback_and_seal.py';text=old.read_text()
state=json.loads((R/RUN/'state.json').read_text());local=json.loads((D/'review.json').read_text())
assert state['nodes']['review']['state']=='SUCCEEDED' and state['sequence']==9
assert json.loads((R/RUN/'claims.json').read_text())=={}
assert state['nodes']['review']['artifact_hash'] != sha256_json(local['result'])
assert state['nodes']['review']['artifact_hash'] == sha256_json({'input_hash':local['input_hash'],'result':local['result']})
write(D/'REVIEW-READBACK-FAILURE-r1.json',{'recorded_at':utc(),
    'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(old)]),'exit_status':1,
    'script':ordinary(old),'traceback':'AssertionError at readback_and_seal.py line22: artifact_hash incorrectly compared with sha256_json(local[result]).',
    'classification':'Reviewer metadata/measurement error after successful actual review. Installed artifact domain includes input_hash plus result.',
    'actual_review_state':'SUCCEEDED','sequence':9,'claims':{},'actual_artifact_hash':state['nodes']['review']['artifact_hash'],
    'incorrect_expected_hash':sha256_json(local['result']),
    'correct_domain':'sha256_json({input_hash: local.input_hash, result: local.result})',
    'Source_code_failure':False,'transition_repeat':False})
needle="assert state['nodes']['review']['artifact_hash']==sha256_json(local['result'])"
assert text.count(needle)==1
text=text.replace(needle,"assert state['nodes']['review']['artifact_hash']==sha256_json({'input_hash':local['input_hash'],'result':local['result']})")
needle="'Source_published':False,'formal_product_completion':False})"
assert text.count(needle)==1
text=text.replace(needle,"'Source_published':False,'formal_product_completion':False,\n    'prior_reader_failure':ordinary(D/'REVIEW-READBACK-FAILURE-r1.json'),'no_transition_repeat':True})")
new=D/'readback_and_seal_r2.py';compile(text,str(new),'exec')
with new.open('x',encoding='utf8',newline='\n') as out:out.write(text)
print(json.dumps({'new_reader':str(new),'sha256':sha(new),'old_reader_preserved':True,
    'actual_review_already_succeeded':True,'transition_repeat':False}),flush=True)

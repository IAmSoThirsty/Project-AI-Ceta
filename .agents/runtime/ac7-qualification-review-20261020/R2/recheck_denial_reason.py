"""DATA_ONLY oracle check: unavailable process is distinct from access denied."""
from pathlib import Path
import ctypes
import hashlib
import importlib.util
import json
import sys
F=Path('T:/00-Active/Project-AI-CETA')
Q=F/'.agents/ac7-token-contract-20261020'
D=Path(__file__).resolve().parent
assert D==F/'.agents/runtime/ac7-qualification-review-20261020/R2'
def deny(*a,**k):raise AssertionError('NO_NATIVE_LOADING')
ctypes.WinDLL=deny
def audit(event,args):
    if event in {'ctypes.dlopen','ctypes.dlsym','subprocess.Popen','socket.__new__','sqlite3.connect'}:
        raise AssertionError('NO_NATIVE_OR_EXTERNAL_OPERATION')
sys.addaudithook(audit)
path=Q/'tests/contract/test_isolation_qualification_oracle.py'
spec=importlib.util.spec_from_file_location('denial_reason_data_only_fixture',path)
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
observations=[]
for reason in (None,0,5,87,True,False):
    result=fixture.probe()
    for row in result['facts']['process_rights'].values():
        if reason is not None:row['error']=reason
    caught=None
    try:fixture.oracle.assert_isolation(result,fixture.SID)
    except fixture.oracle.QualificationError as error:caught=error.code
    observations.append({'all_process_rights_granted':False,'controlled_error':reason,
                         'oracle_accepted':caught is None,'rejection_code':caught})
assert all(row['oracle_accepted'] == (type(row['controlled_error']) is int and row['controlled_error'] == 5) for row in observations)
record={'classification':'CONTROLLED_ORACLE_ACCEPTANCE_NOT_AN_ACTUAL_NATIVE_FAILURE',
 'oracle_sha256':hashlib.sha256((Q/'tools/isolated_worker_token_oracle.py').read_bytes()).hexdigest(),
 'cases':observations,'actual_process_operations':[],
 'source_provenance':'R4 oracle requires exact integer native error5 for each denied process right; trusted target identity and before/after liveness are supplied by the complete fixture.'}
with (D/'DENIAL-REASON-RESULT.json').open('x',encoding='utf8') as out:json.dump(record,out,indent=2)
print(json.dumps({'controlled_cases':len(observations),'only_integer_access_denied5_accepted':True,
 'result_sha256':hashlib.sha256((D/'DENIAL-REASON-RESULT.json').read_bytes()).hexdigest()}))

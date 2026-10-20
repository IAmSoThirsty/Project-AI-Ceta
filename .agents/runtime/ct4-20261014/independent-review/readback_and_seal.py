"""Confirm actual CT4 Source completion and seal only this reviewer scope."""
from ct4_support import *
import re
sys.path.insert(0,r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import sha256_json
inspection=read(V/'candidate-inspection.json');delivered=read(V/'delivered-source-review.json')
assert delivered['decision']=='approved' and delivered['exit_status']==0
s=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json')
assert s['sequence']==13 and claims=={} and len(s['nodes'])==6 and all(n['state']=='SUCCEEDED' for n in s['nodes'].values())
assert s['nodes']['review']['executor_id']==ACTOR and s['nodes']['integrate']['executor_id']=='/root'
acceptance=read(R/'actual-acceptance.json');integrate=read(R/'integrate.json');stored=read(R/RUN/'receipts/integrate.json')
assert acceptance['integrate_receipt_sha256']==sha(R/'integrate.json') and acceptance['metadata_paths']==2 and acceptance['retained_source_payloads']==290
assert len(integrate)==12 and set(stored)==set(integrate)|{'git_baseline','observed_git','receipt_hash'}
strict=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
assert strict({k:stored[k] for k in integrate})==strict(integrate)
normalized=dict(stored);normalized.pop('receipt_hash');fingerprint=sha256_json(normalized)
assert fingerprint==stored['receipt_hash']==s['nodes']['integrate']['receipt_hash']
assert integrate['changed_files']==sorted((F/rel).relative_to(Path('T:/')).as_posix() for rel in ('build/progress.json','handoff/continuity.json'))
dest=read(R/'destination-verification.json');assert dest['metadata_paths']==2 and dest['retained_source_payloads']==290 and dest['native_and_logical_originals']==2
assert dest['application_journal_sha256']==delivered['actual_APPLIED']['sha256']
assert dest['manifest_sha256']==delivered['manifest_sha256'] and dest['review_sha256']==sha(V/'review.json')
consumer=read(R/'active-application/metadata-consumer-tests.json')
assert consumer==dest['metadata_consumer_tests'] and consumer['tests_run']==3 and consumer['expected_ids']==consumer['executed_ids'] and len(set(consumer['executed_ids']))==3
assert all(type(consumer[k]) is int and consumer[k]==0 for k in ('failures','errors','skips','exit_status'))
raw=R/'active-application/metadata-consumer-tests.txt';assert sha(raw)==consumer['raw_sha256']
assert re.findall(r'^\S+ \(([^)]+)\)',raw.read_text(encoding='utf8'),re.MULTILINE)==consumer['executed_ids']
root_collection=read(R/'active-application/actual-register-measurements.json');own_collection=read(V/'actual-register-measurements-delivered.json')
assert all(root_collection[k]==v for k,v in own_collection.items() if k!='observed_at_utc')
assert all(ordinary(F/rel)==value for rel,value in inspection['source_native'].items())
assert all(ordinary(Q/rel)==value for rel,value in inspection['candidate_native'].items())
assert all(ordinary(F/rel)==value for rel,value in inspection['globals_native'].items())
for row in read(Q/'TRANSFER-MANIFEST.json')['payloads']:
    rel=row['relative_path'];assert sha(F/rel)==row['candidate_sha256']
    assert ordinary(R/'active-application/native-backups'/(rel+'.original'))==inspection['active_metadata_native'][rel]
environment=read(V/'environment-conservation.json');assert all(ordinary(E3/rel)==value for rel,value in environment['ordinary_native'].items())
save(V/'actual-destination-readback.json',{'executor':ACTOR,'observed_at':utc(),'actual_sequence':13,'actual_states':{k:v['state'] for k,v in s['nodes'].items()},
    'claims':claims,'actual_acceptance':ref(R/'actual-acceptance.json'),'actual_Source_integrate':ref(R/'integrate.json'),'normalized_integrate_fingerprint':fingerprint,
    'submitted_integrate_fields':12,'persisted_integrate_fields':15,'strict_projection_equal':True,'changed_files':integrate['changed_files'],
    'delivered_independent_review':ref(V/'delivered-source-review.json'),'destination_verification':ref(R/'destination-verification.json'),
    'root_actual_consumer_tests':ref(R/'active-application/metadata-consumer-tests.json'),'source_payloads':290,'modules':74,'root_full_contract_cases':1479,
    'current_E3_ordinary_files':3601,'current_E3_ordinary_bytes':sum(v['bytes'] for v in environment['ordinary_native'].values()),
    'actual_Source_metadata_paths':2,'runtime_code_changes':0,'Source_candidate_globals_E3_ordinary_conserved':True,'whole_product_acceptance':False,'runtime_effect_acceptance':False,
    'owned_native_processes_launched':0,'owned_lifecycle_claims_remaining':0,'exit_status':0})
files=[];reparse=[];stack=[V]
while stack:
    parent=stack.pop()
    with os.scandir(fs.io_path(parent)) as entries:
        for entry in entries:
            path=parent/entry.name;info=entry.stat(follow_symlinks=False)
            if fs.reparse(info):reparse.append({'path':path.relative_to(V).as_posix(),'native_identity':fs.file_identity(info)})
            elif stat.S_ISDIR(info.st_mode):stack.append(path)
            elif stat.S_ISREG(info.st_mode):files.append({'path':path.relative_to(V).as_posix(),**ordinary(path)})
            else:raise AssertionError(('UNEXPECTED_REVIEW_ENTRY',str(path)))
save(V/'REVIEW-SCOPE-SEAL.json',{'recorded_at':utc(),'reviewer':ACTOR,'scope':str(V),'scope_closed':True,'write_claims_remaining':0,
    'actual_review':ref(V/'review-readback.json'),'actual_Source_readback':ref(V/'actual-destination-readback.json'),'files':sorted(files,key=lambda r:r['path']),
    'ordinary_files':len(files),'reparse_not_followed':reparse,'owned_processes_running':0,'owned_threads_running':0,'qualification':'Only CT4 reviewer files sealed. Previous failed attempts and fixtures retained. Seal excludes its own bytes and enclosing capture output that is created after return; Root/candidate/Source/other review scopes remain outside ownership.'})
print(json.dumps({'sequence':13,'all6':'SUCCEEDED','claims':{},'readback_sha256':sha(V/'actual-destination-readback.json'),'seal_sha256':sha(V/'REVIEW-SCOPE-SEAL.json'),'files':len(files)}),flush=True)

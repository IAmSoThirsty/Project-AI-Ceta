"""Independent unchanged109 cases plus finite actual EN2/EN3 parser comparison."""
from review_support import *
import contextlib,ctypes,importlib,threading,unittest
from unittest.mock import patch
M=D/'replica';E=D/'qualification-r1';E.mkdir()
os.environ['TEMP']=os.environ['TMP']=str(E)
sys.path[:0]=[str(M/'src'),str(M/'tests/contract')]
names=('test_owner_enrollment','test_temporal','test_wire','test_all_records','test_source_coverage','test_owner_enrollment_guid')
modules=[importlib.import_module(name) for name in names]
from ceta.contracts import owner_enrollment as current
from ceta.contracts.wire import ContractError,canonical_bytes,strict_loads
parent_file=F/'.agents/en2-20261014/src/ceta/contracts/owner_enrollment.py'
spec=importlib.util.spec_from_file_location('ceta.contracts._independent_en2_parser_oracle',parent_file)
previous=importlib.util.module_from_spec(spec);sys.modules[spec.name]=previous;spec.loader.exec_module(previous)
facts=[]
canonical='12345678-1234-4234-8234-123456789abc'
variants={canonical,'00000000-0000-0000-0000-000000000000','ffffffff-ffff-ffff-ffff-ffffffffffff',
    canonical.upper(),canonical.replace('-',''),'{'+canonical+'}','urn:uuid:'+canonical,
    canonical+'\n',canonical+'\r',canonical+' ',canonical+'\0',' '+canonical}
for position in range(len(canonical)):
    for replacement in ('0','a','f','F','g','-','\0','\n','\uff10'):
        variants.add(canonical[:position]+replacement+canonical[position+1:])
variants=sorted(variants)
class IndependentGuidCompatibilityTests(unittest.TestCase):
    def test_every_single_position_guid_mutation_keeps_exact_parent_acceptance_and_error_code(self):
        rows=[]
        for guid in variants:
            path='\\\\?\\Volume{'+guid+'}\\.agents\\CETA\\private'
            def classify(api):
                try:
                    identity=api.NativeObjectIdentity(path,'directory','0'*16,'0'*32)
                    return ('ACCEPT',identity.as_dict())
                except ContractError as error:return ('DENY',error.code)
            old,new=classify(previous),classify(current)
            with self.subTest(guid=repr(guid)):self.assertEqual(new,old)
            rows.append({'input_sha256':digest(guid.encode()),'decision':new[0],
                'error_code':None if new[0]=='ACCEPT' else new[1]})
        facts.append({'test':self.id(),'cases':len(rows),'accepted':sum(row['decision']=='ACCEPT' for row in rows),
            'denied':sum(row['decision']=='DENY' for row in rows),'rows':rows})
    def test_all_version_variant_nibbles_and_invalid_boot_forms_match_actual_parent(self):
        request=modules[0].request();base=strict_loads(request.canonical_wire)
        guids={f'12345678-1234-{v}234-{variant}234-123456789abc' for v in '0123456789abcdef' for variant in '0123456789abcdef'}
        guids.update(variants)
        rows=[]
        for guid in sorted(guids):
            value=dict(base,deadline=dict(base['deadline'],boot_id='boot:'+guid+':session:'+request.clock_session_nonce))
            wire=canonical_bytes(value)
            def classify(api):
                try:return ('ACCEPT',api.decode_enrollment_request(wire).canonical_wire)
                except ContractError as error:return ('DENY',error.code)
            old,new=classify(previous),classify(current)
            with self.subTest(guid=repr(guid)):self.assertEqual(new,old)
            rows.append({'input_sha256':digest(guid.encode()),'decision':new[0],
                'error_code':None if new[0]=='ACCEPT' else new[1]})
        zero=next(row for row in rows if row['input_sha256']==digest(b'00000000-0000-0000-0000-000000000000'))
        self.assertEqual((zero['decision'],zero['error_code']),('DENY','ENROLLMENT_BOOT_WITNESS_INVALID'))
        facts.append({'test':self.id(),'cases':len(rows),'accepted':sum(row['decision']=='ACCEPT' for row in rows),
            'denied':sum(row['decision']=='DENY' for row in rows),'rows':rows,'version_variant_combinations':256})
base_suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
def ids(suite):
    if isinstance(suite,unittest.TestSuite):
        for test in suite:yield from ids(test)
    else:yield suite.id()
original_ids=list(ids(base_suite));author=json.loads((R/'targeted-r2.json').read_text())
assert original_ids==author['expected_ids'] and len(original_ids)==len(set(original_ids))==109
extra=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentGuidCompatibilityTests)
suite=unittest.TestSuite((base_suite,extra));expected=list(ids(suite));assert len(expected)==len(set(expected))==111
setup=json.loads((D/'PREPARATION.json').read_text())
def conserved():
    assert all(ordinary(Q/name)==row for name,row in setup['payloads'].items())
    assert all(ordinary(M/name)==row for name,row in setup['replica'].items())
    assert all(ordinary(F/name)==row for name,row in setup['Source290'].items())
conserved()
forbidden=[];real_dll=ctypes.WinDLL
class Forbidden:
    def __init__(self,name):self.name=name
    def __call__(self,*args,**kwargs):forbidden.append(self.name);raise AssertionError('NATIVE_PROFILE_PROCESS_OR_CPU_EFFECT_FORBIDDEN')
class DLL:
    def __init__(self,original):self.original=original
    def __getattr__(self,name):
        if name in ('CreateAppContainerProfile','DeleteAppContainerProfile','CreateProcessW','CreateProcessAsUserW',
                    'CreateProcessWithTokenW','CreateProcessWithLogonW','SetInformationJobObject'):
            return Forbidden(name)
        return getattr(self.original,name)
def guarded_dll(name,*args,**kwargs):return DLL(real_dll(name,*args,**kwargs))
def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.startfile'):
        forbidden.append(event);raise AssertionError('ACTUAL_PROCESS_OPERATION_FORBIDDEN')
sys.addaudithook(audit)
executed,stopped=[],[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
started=utc();threads=set(threading.enumerate())
write(E/'PREFLIGHT.json',{'at':started,'original109_ids':original_ids,'expected111_ids':expected,
    'current_parser':ordinary(M/'src/ceta/contracts/owner_enrollment.py'),'parent_data_oracle':ordinary(parent_file),
    'replica_bytes_exact':True,'native_operations_forbidden':True})
with patch.object(ctypes,'WinDLL',guarded_dll),(E/'tests.txt').open('x',encoding='utf8') as out:
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
        result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
conserved()
remaining=[{'name':t.name,'native_id':t.native_id} for t in set(threading.enumerate())-threads if t.is_alive()]
imports={name:str(Path(m.__file__).resolve()) for name,m in sys.modules.items()
    if (name=='ceta' or name.startswith('ceta.')) and getattr(m,'__file__',None)}
assert all(Path(path).is_relative_to(M/'src') or name=='ceta.contracts._independent_en2_parser_oracle' and Path(path)==parent_file for name,path in imports.items())
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and not remaining and not forbidden
write(E/'RESULT.json',{'started_at':started,'finished_at':utc(),'tests_run':result.testsRun,
    'original109_ids':original_ids,'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
    'failures':[{'id':t.id(),'traceback':tb} for t,tb in result.failures],
    'errors':[{'id':t.id(),'traceback':tb} for t,tb in result.errors],'skips':result.skipped,
    'differential_facts':facts,'source_imports':imports,'forbidden_calls':forbidden,'threads_remaining':remaining,
    'original_Source_Q_replica_exact':True,'raw_sha256':sha(E/'tests.txt'),
    'native_profile_process_authority_operations':[],'test_only_uuid_oracle_not_in_product_leaf':True,
    'exit_status':0 if passed else 1})
print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skips':len(result.skipped),'differential_cases':[fact['cases'] for fact in facts],'exit_status':0 if passed else 1}),flush=True)
sys.exit(0 if passed else 1)

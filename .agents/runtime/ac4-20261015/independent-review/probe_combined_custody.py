"""Actual owned token cleanup plus refusing primary hooks; no launch/profile."""
from pathlib import Path
import contextlib,ctypes as C,hashlib,importlib,json,sys,threading,unittest
F=Path('T:/00-Active/Project-AI-CETA');Q=F/'.agents/ac4-20261015';R=F/'.agents/runtime/ac4-20261015';D=Path(__file__).resolve().parent
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=D
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.supervisor import isolated_worker as module
assert Path(module.__file__).is_relative_to(Q/'src')
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text())
before={name:s.ordinary(Q/name) for name in manifest['payloads']}
source_before=json.loads((D/'cohort-r1/RESULT.json').read_text())['source_after']
observations=[];forbidden=[]
class CombinedCustody(unittest.TestCase):
    def probe(self,base):
        class RefusingPrimary(base):
            def __setattr__(self,name,value):raise RuntimeError('primary diagnostic setter refused')
            def __getattribute__(self,name):
                if name in ('__dict__','isolation_cleanup','owned_process','add_note'):
                    raise RuntimeError('primary diagnostic getter refused')
                return super().__getattribute__(name)
        primary=RefusingPrimary('exact native read primary');api=module._IsolationAPI()
        def deny(*args):forbidden.append('CreateProcessW');raise AssertionError('NO_WORKER_LAUNCH')
        api.CreateProcessW=deny
        for name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):
            def refuse(*args,_name=name):forbidden.append(_name);raise AssertionError('NO_PROFILE_OPERATION')
            setattr(api.userenv,name,refuse)
        real_read,real_cleanup=api.token_data,api.retry_cleanup
        def interrupted(token,kind):
            value=real_read(token,kind)
            if kind==29:raise primary
            return value
        def cleanup_failure(**kwargs):raise RuntimeError('injected cleanup failure before native close')
        caught=None;native_before=[];native_after=[];original_pending=[];raw={};recovered=False
        try:
            sid=api.derive('CETA.ProjectAICETA.AC4.ReviewerCombined')
            api.token_data=interrupted;api.retry_cleanup=cleanup_failure
            try:api.token_facts(api.GetCurrentProcess(),sid)
            except BaseException as error:caught=error
            raw=BaseException.__dict__['__dict__'].__get__(primary)
            original_pending=list(api.pending_native_resources())
            for row in api._pending_handles:
                flags=module.DWORD();C.set_last_error(0)
                ok=api.GetHandleInformation(row['handle'],C.byref(flags))
                native_before.append({'handle':row['handle'],'GetHandleInformation':bool(ok),'error':C.get_last_error()})
        finally:
            api.token_data=real_read;api.retry_cleanup=real_cleanup
            real_cleanup()
            for item in native_before:
                flags=module.DWORD();C.set_last_error(0)
                ok=api.GetHandleInformation(item['handle'],C.byref(flags))
                native_after.append({'handle':item['handle'],'GetHandleInformation':bool(ok),'error':C.get_last_error()})
            recovered=api.pending_native_resources()==()
            observations.append({'test_id':self.id(),'primary_type':base.__name__,'exact_primary_preserved':caught is primary,
                'primary_dictionary_keys':sorted(raw),'native_observation':raw.get('native_isolation_token_observation'),
                'caller_visible_cleanup_present':'isolation_cleanup' in raw,
                'native_pending_at_error':original_pending,'native_handles_before':native_before,
                'native_handles_after_explicit_reviewer_recovery':native_after,'all_owned_native_resources_retired':recovered,
                'profile_operations':[],'worker_launches':[]})
        self.assertIs(caught,primary)
        self.assertEqual(raw['native_isolation_token_observation']['stage'],'QUERY_APPCONTAINER')
        self.assertEqual(len(native_before),1);self.assertTrue(native_before[0]['GetHandleInformation'])
        self.assertTrue(recovered)
        self.assertEqual(native_after,[dict(native_after[0],GetHandleInformation=False,error=6)])
        self.assertIn('isolation_cleanup',raw,
            'Caller-visible primary retains native diagnostics but loses the pending native cleanup owner when setters refuse')
    def test_native_keyboard_interrupt_retains_cleanup_owner_despite_hooks(self):self.probe(KeyboardInterrupt)
    def test_native_system_exit_retains_cleanup_owner_despite_hooks(self):self.probe(SystemExit)
executed=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
old_threads=set(threading.enumerate());started=s.utc()
with (D/'combined-custody-r1.txt').open('x',encoding='utf-8',buffering=1) as out:
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
        result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(CombinedCustody))
after={name:s.ordinary(Q/name) for name in before};source_after={name:s.ordinary(F/name) for name in source_before}
assert before==after and source_before==source_after and not forbidden
remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-old_threads if t.is_alive()]
record={'started_at':started,'finished_at':s.utc(),'tests_run':result.testsRun,'executed_ids':executed,
    'failures':[{'id':t.id(),'traceback':tb} for t,tb in result.failures],
    'errors':[{'id':t.id(),'traceback':tb} for t,tb in result.errors],'skips':result.skipped,
    'observations':observations,'all_owned_native_resources_retired':all(o['all_owned_native_resources_retired'] for o in observations),
    'Source290_and_candidate295_bytes_native_identities_exact':True,'new_threads':remaining,'forbidden_calls':forbidden,
    'authorship_boundary':'Reviewer authored earlier AC2 cleanup foundation. AC4 diagnostic delta is Root authored; inherited combined custody finding requires Root disposition, not a claim of wholly independent AC2 review.',
    'probe':s.reference(Path(__file__)),'raw':s.reference(D/'combined-custody-r1.txt'),
    'exit_status':0 if result.wasSuccessful() and not remaining else 1}
s.write_new(D/'COMBINED-CUSTODY-PROBE.json',record)
print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'all_owned_native_resources_retired':record['all_owned_native_resources_retired'],'new_threads':remaining,'exit_status':record['exit_status']}))
sys.exit(record['exit_status'])

"""Original negative methods and bounded repair oracles; native profile mutation forbidden."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
import ast, contextlib, ctypes, hashlib, importlib.util, io, json, os, sys, types, unittest, uuid

F=Path('T:/00-Active/Project-AI-CETA')
R=Path(__file__).resolve().parent
D=R/'tests-r3'
assert R==F/'.agents/runtime/ac3-20261014/profile-tool'
assert Path(sys.executable)==F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
sys.dont_write_bytecode=True
D.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
utc=lambda:datetime.now(timezone.utc).isoformat()
blocked=[]
native_windll=ctypes.WinDLL
class Forbidden:
    def __init__(self,name):self.name=name
    def __call__(self,*args):blocked.append(self.name);raise AssertionError('ACTUAL_PROFILE_MUTATION_FORBIDDEN')
class DLL:
    def __init__(self,original):self.original=original
    def __getattr__(self,name):
        if name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):return Forbidden(name)
        return getattr(self.original,name)
def guarded_dll(name,*args,**kwargs):return DLL(native_windll(name,*args,**kwargs))

with patch.object(ctypes,'WinDLL',guarded_dll):
    spec=importlib.util.spec_from_file_location('author_profile_r2',R/'profile_qualification.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    before_source,before_candidate=module.source_cut(),module.candidate_cut()
    old_review=F/'.agents/runtime/ac2-20261014/profile-tool-independent-review'
    old_tests=F/'.agents/runtime/ac2-20261014/test_profile_preparation.py'
    before_paths={str(path.relative_to(F)):module.observed(path) for path in (
        F/'.agents/runtime/ac2-20261014/profile_qualification.py',old_tests,
        old_review/'REPORT.json',old_review/'SEAL.json',
        *(F/name for name in module.DEPENDENCIES))}
    with (D/'profile_qualification.py').open('xb') as output:output.write((R/'profile_qualification.py').read_bytes())
    old_tree=ast.parse(old_tests.read_text(encoding='utf-8'))
    old_class=next(node for node in old_tree.body if isinstance(node,ast.ClassDef) and node.name=='ProfilePreparationTests')
    scope={'__name__':'__main__','module':module,'R':D,'Path':Path,'patch':patch,
        'hashlib':hashlib,'json':json,'sys':sys,'unittest':unittest,'uuid':uuid}
    exec(compile(ast.Module(body=[old_class],type_ignores=[]),str(old_tests),'exec'),scope)

    binary=F/'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
    driver=F/'.agents/runtime/ac1-20261014/native_fixture_support.py'
    support=F/'.agents/runtime/ac3-20261014/ac3_support.py'
    original_read=module.fs.read_bytes
    stimulus=b'CONTROLLED_BINARY_DRIFT_NEGATIVE_ORACLE_NOT_EXECUTABLE\n'
    outcomes=[]

    def controlled_case(label, faults=(), *, sid_failure=False, mismatch=False,
            create_failure=False, lost_return=False, null_pointer=False,
            cleanup_failure=False, source_after_failure=False, closed_failure=False,
            profile_exists=False, post_delete_failure=False, all_late_writes_fail=False,
            stdout_failure=False, missing_retirement=False, partial_api=False):
        directory=D/('controlled-'+label+'-'+uuid.uuid4().hex)
        primary=RuntimeError('CONTROLLED_PRIMARY:'+label)
        diagnostic=OSError('CONTROLLED_DIAGNOSTIC:'+label)
        calls=[];original_save=module.save;source_calls=[]
        class Function:
            def __init__(self,name):self.name=name
            def __call__(self,*args):
                calls.append(self.name)
                if self.name=='simulated_Create':
                    if not null_pointer and not create_failure:
                        ctypes.cast(args[-1],ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.c_void_p(12345)
                    if lost_return:raise primary
                    return -2147024713 if create_failure else 0
                return 0
        class API:
            def __init__(self):
                if partial_api:raise primary
                self.pending_sids=[]
                self.userenv=types.SimpleNamespace(CreateAppContainerProfile=Function('simulated_Create'),
                    DeleteAppContainerProfile=Function('simulated_Delete'))
            def sid_text(self,pointer):
                if sid_failure:raise primary
                return 'S-1-15-2-1' if mismatch else module.SID
            def retry_cleanup(self,**kwargs):
                if self.pending_sids:
                    if cleanup_failure:raise diagnostic
                    calls.append('simulated_FreeSid');self.pending_sids.clear()
            def pending_native_resources(self):return tuple({'kind':'sid','address':x} for x in self.pending_sids)
        class Owner:
            def __init__(self):
                self._job,self._process,self._thread=101,102,None
                self.pid,self.creation_time,self._closed,self.exited=999999,123456,False,False
            @property
            def lifetime_closed(self):return self._closed
            def poll(self):return 125 if self.exited else None
            def terminate(self,code):calls.append('simulated_Terminate');self.exited=True
            def wait(self,seconds):self.exited=True;return True
            def active_process_count(self):return 0
            def close(self):
                if closed_failure:raise diagnostic
                self._closed=True;self._job=self._process=self._thread=None
                calls.append('simulated_CloseOwner')
        def probe(*args,**kwargs):
            module.WindowsOwnedProcess()
            if missing_retirement:raise primary
            receipt=directory/'CONTROLLED-NEGATIVE-PROBE.json'
            original_save(receipt,{'cleanup':[],'failure':'CONTROLLED_PROBE_DENIAL_NO_NATIVE_WORKER'})
            primary.native_probe_receipt=str(receipt)
            raise primary
        def prepared(path,**kwargs):
            assert path==directory and path.is_dir()
            return types.SimpleNamespace(run_native_probe=probe)
        def inspected():
            return {'prior_folder':{'HRESULT':0 if profile_exists else -2147024894,
                'path':'CONTROLLED_EXISTING_PROFILE_PATH' if profile_exists else None}}
        def source():
            source_calls.append(1)
            if source_after_failure and len(source_calls)>1:raise diagnostic
            return {'CONTROLLED_READ_ONLY_SOURCE_CUT':True}
        def save_control(path,value):
            if path.name in faults or all_late_writes_fail and path.name not in (
                    'BEFORE.json','SOURCE-BEFORE.json','CANDIDATE-BEFORE.json','CREATE-INTENT.json','CREATE-RETURN.json'):
                raise primary if path.name in ('CREATE-RETURN.json','CREATED.json') else diagnostic
            original_save(path,value)
        def folder(api,sid):
            if post_delete_failure:raise diagnostic
            return {'HRESULT':-2147024894,'path':None,'contents_read':False}
        class BrokenStream(io.StringIO):
            def write(self,text):raise diagnostic
        output=BrokenStream() if stdout_failure else io.StringIO()
        with patch.object(module.module,'_IsolationAPI',API),patch.object(module,'WindowsOwnedProcess',Owner), \
             patch.object(module,'prepare_probe',prepared),patch.object(module,'inspect',inspected), \
             patch.object(module,'source_cut',source),patch.object(module,'candidate_cut',lambda:{'CONTROLLED_CANDIDATE':True}), \
             patch.object(module,'save',save_control),patch.object(module,'folder',folder), \
             patch.object(module.module,'appcontainer_sid',lambda name:module.SID), \
             patch.object(module,'user_sid',lambda api:module.USER),contextlib.redirect_stdout(output),contextlib.redirect_stderr(io.StringIO()):
            run=module._QualificationRun(directory,'CONTROLLED_NOT_AN_OPERATOR_APPROVAL')
            code=run.execute()
        files={path.name for path in directory.iterdir() if path.is_file()}
        assert code==1 and not run.positive_isolation_qualified
        expected_primary=primary if (sid_failure or lost_return or faults and faults[0] in ('CREATE-RETURN.json','CREATED.json') or all_late_writes_fail or not (profile_exists or create_failure or mismatch or null_pointer)) else None
        if expected_primary is not None:assert run.primary_error is expected_primary,(label,run.primary_error)
        assert run.final_report['primary_failure']==module.describe(run.primary_error)
        assert run.created_this_run==('simulated_Create' in calls and not (lost_return or create_failure))
        if profile_exists:assert 'simulated_Create' not in calls
        if partial_api:assert 'simulated_Create' not in calls and not run.retired
        if missing_retirement:assert 'simulated_Delete' not in calls and not run.retired
        if label in ('create_return_write_fails','sid_text_fails','created_write_fails','retirement_write_fails',
                'cleanup_fails','create_return_lost','null_sid','wrong_sid','already_exists','owner_close_fails'):
            assert 'simulated_Delete' not in calls,label
        if not all_late_writes_fail:
            assert 'RESULT.json' in files or 'FINAL-FAILURE.json' in files,label
        if 'simulated_Delete' not in calls and not all_late_writes_fail:
            assert 'PROFILE-RETAINED-OR-UNKNOWN.json' in files,label
        if label=='sid_text_fails':assert 'simulated_FreeSid' in calls and run.retired
        if label=='cleanup_fails':assert not run.retired and run.retirement['pending_native_resources']
        if lost_return:assert run.unknown_output_pointer and not run.retired
        if source_after_failure:assert not run.source_conserved
        if post_delete_failure:
            assert calls.count('simulated_Delete')==1 and run.cleanup_status=='DELETE_OR_OBSERVATION_UNRESOLVED'
        row={'label':label,'non_native_calls':calls,'exit_status':code,
            'primary_object_identity_preserved':expected_primary is None or run.primary_error is expected_primary,
            'files':sorted(files),'final_report':run.final_report,
            'native_Create_Delete_executed':False,'operator_approval_created':False}
        outcomes.append(row)
        return run

    class RepairNegativeTests(unittest.TestCase):
        def test_exact_prepare_captures_one_payload_and_writes_actual_IMAGE(self):
            count=[];directory=D/('single-capture-'+uuid.uuid4().hex)
            def controlled_read(path):
                if Path(path)==binary:
                    count.append(1)
                    if len(count)>1:return stimulus
                return original_read(path)
            with patch.object(module.fs,'read_bytes',controlled_read):module.prepare_probe(directory)
            self.assertEqual(len(count),1)
            binding=module.read(directory/'PROBE-BINDING.json')
            self.assertEqual(module.sha(directory/'build-r2/isolated_worker.exe'),module.IMAGE)
            self.assertEqual(binding['image_copy']['sha256'],module.IMAGE)
            self.assertTrue(binding['imports_execute_captured_verified_bytes'])

        def test_bad_first_binary_payload_is_rejected_before_import_or_write(self):
            directory=D/('bad-binary-'+uuid.uuid4().hex)
            def same_size_drift(path):
                payload=original_read(path)
                return bytes([payload[0]^1])+payload[1:] if Path(path)==binary else payload
            with patch.object(module.fs,'read_bytes',same_size_drift), \
                 patch.object(module,'write_payload',side_effect=AssertionError('FORBIDDEN_WRITE')) as write:
                with self.assertRaisesRegex(AssertionError,'CAPTURED_PAYLOAD_HASH_MISMATCH'):module.prepare_probe(directory)
                write.assert_not_called()

        def test_both_runtime_helper_drifts_are_rejected_before_import(self):
            for target in (driver,support):
                with self.subTest(path=str(target)):
                    directory=D/('bad-helper-'+uuid.uuid4().hex)
                    def changed(path):
                        payload=original_read(path)
                        return bytes([payload[0]^1])+payload[1:] if Path(path)==target else payload
                    with patch.object(module.fs,'read_bytes',changed),patch.object(module,'write_payload') as write:
                        with self.assertRaisesRegex(AssertionError,'CAPTURED_PAYLOAD_HASH_MISMATCH'):module.prepare_probe(directory)
                        write.assert_not_called()

        def test_native_dependency_identity_mismatch_is_rejected_before_payload(self):
            pin=module.DEPENDENCIES[str(binary.relative_to(F)).replace('\\','/')]
            changed=dict(pin['native_identity'],inode=pin['native_identity']['inode']+1)
            with patch.object(module.fs,'read_bytes',side_effect=AssertionError('FORBIDDEN_PAYLOAD_READ')) as read:
                with self.assertRaisesRegex(AssertionError,'DEPENDENCY_NATIVE_IDENTITY_CHANGED'):module.capture(binary,module.IMAGE,changed)
                read.assert_not_called()

        def test_copy_verification_refuses_different_observed_copy(self):
            directory=D/('bad-copy-'+uuid.uuid4().hex)
            def changed(path):
                if Path(path)==directory/'build-r2/isolated_worker.exe':return stimulus
                return original_read(path)
            with patch.object(module.fs,'read_bytes',changed):
                with self.assertRaises(AssertionError):module.prepare_probe(directory)
            self.assertFalse((directory/'PROBE-BINDING.json').exists())
            self.assertEqual(module.sha(directory/'build-r2/isolated_worker.exe'),module.IMAGE)

        def test_create_return_write_failure_keeps_custody_and_reports_retention(self):controlled_case('create_return_write_fails',('CREATE-RETURN.json',))
        def test_sid_conversion_failure_frees_owned_output_without_masking_primary(self):controlled_case('sid_text_fails',sid_failure=True)
        def test_created_journal_failure_refuses_delete_and_reports_retention(self):controlled_case('created_write_fails',('CREATED.json',))
        def test_retirement_journal_failure_preserves_probe_primary_and_refuses_delete(self):controlled_case('retirement_write_fails',('RETIREMENT.json',))
        def test_late_journal_failures_still_retire_and_preserve_primary(self):controlled_case('all_late_writes_fail',all_late_writes_fail=True)
        def test_cleanup_refusal_retains_pending_pointer_without_masking_primary(self):controlled_case('cleanup_fails',sid_failure=True,cleanup_failure=True)
        def test_source_after_failure_does_not_skip_result_or_replace_primary(self):controlled_case('source_after_fails',source_after_failure=True)
        def test_result_write_failure_uses_independent_failure_receipt(self):controlled_case('result_write_fails',('RESULT.json',))
        def test_stdout_failure_preserves_probe_primary_and_disk_receipt(self):controlled_case('stdout_fails',stdout_failure=True)
        def test_create_response_loss_keeps_output_unknown_and_never_deletes(self):controlled_case('create_return_lost',lost_return=True)
        def test_success_without_sid_never_deletes(self):controlled_case('null_sid',null_pointer=True)
        def test_returned_other_sid_never_deletes(self):controlled_case('wrong_sid',mismatch=True)
        def test_already_exists_return_never_adopts_or_deletes(self):controlled_case('already_exists',create_failure=True)
        def test_prior_existing_profile_is_refused_before_create(self):controlled_case('preexisting_profile',profile_exists=True)
        def test_unretired_owned_process_refuses_delete(self):controlled_case('owner_close_fails',closed_failure=True)
        def test_post_delete_observation_failure_reports_unknown_without_replay(self):controlled_case('post_delete_observation_fails',post_delete_failure=True)
        def test_missing_helper_retirement_evidence_refuses_delete(self):controlled_case('missing_retirement',missing_retirement=True)
        def test_partial_api_constructor_is_captured_and_retains_unknown_resources(self):controlled_case('partial_api',partial_api=True)

        def test_folder_decode_and_free_errors_preserve_primary_and_pointer_custody(self):
            primary=ValueError('CONTROLLED_FOLDER_DECODE_PRIMARY')
            secondary=OSError('CONTROLLED_FOLDER_FREE_SECONDARY')
            class Function:
                def __init__(self,behavior):self.behavior=behavior
                def __call__(self,*args):return self.behavior(*args)
            def returned(sid,output):
                ctypes.cast(output,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.c_void_p(12345)
                return 0
            def failed_free(pointer):raise secondary
            api=types.SimpleNamespace(userenv=types.SimpleNamespace(GetAppContainerFolderPath=Function(returned)))
            ole=types.SimpleNamespace(CoTaskMemFree=Function(failed_free))
            with patch.object(module.C,'WinDLL',lambda *args,**kwargs:ole),patch.object(module.C,'wstring_at',side_effect=primary):
                with self.assertRaises(ValueError) as caught:module.folder(api,module.SID)
            self.assertIs(caught.exception,primary)
            self.assertIs(primary.profile_folder_cleanup_error,secondary)
            self.assertEqual(api._profile_folder_outputs,[{'kind':'folder_path','address':12345,'state':'RELEASE_UNCERTAIN'}])

        def test_token_data_and_cleanup_errors_preserve_primary(self):
            primary=ValueError('CONTROLLED_TOKEN_DATA_PRIMARY')
            secondary=OSError('CONTROLLED_TOKEN_CLEANUP_SECONDARY')
            class API:
                def __init__(self):self.queued=[]
                def GetCurrentProcess(self):return -1
                def OpenProcessToken(self,process,rights,output):
                    ctypes.cast(output,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.c_void_p(12345)
                    return True
                def queue_handle(self,handle):self.queued.append(handle)
                def token_data(self,*args):raise primary
                def retry_cleanup(self,**kwargs):raise secondary
            api=API()
            with self.assertRaises(ValueError) as caught:module.user_sid(api)
            self.assertIs(caught.exception,primary)
            self.assertIs(primary.profile_token_cleanup_error,secondary)
            self.assertEqual(set(api.queued),{12345})

        def test_occupied_evidence_directory_is_never_adopted(self):
            directory=D/('occupied-'+uuid.uuid4().hex);directory.mkdir()
            marker=directory/'UNKNOWN-ORIGINAL.txt';marker.write_bytes(b'PRESERVE_UNKNOWN_DIRECTORY\n')
            before=module.observed(marker)
            with contextlib.redirect_stdout(io.StringIO()):
                run=module._QualificationRun(directory,'CONTROLLED_NOT_AN_OPERATOR_APPROVAL')
                self.assertEqual(run.execute(),1)
            self.assertIsInstance(run.primary_error,FileExistsError)
            self.assertEqual(module.observed(marker),before)
            self.assertEqual({p.name for p in directory.iterdir()},{marker.name})

    suites=[unittest.defaultTestLoader.loadTestsFromTestCase(scope['ProfilePreparationTests']),
            unittest.defaultTestLoader.loadTestsFromTestCase(RepairNegativeTests)]
    expected=[test.id() for suite in suites for test in suite]
    assert len(expected)==len(set(expected))
    class Recorder(unittest.TextTestResult):
        def startTest(self,test):executed.append(test.id());super().startTest(test)
        def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
    executed,stopped=[],[]
    with (D/'negative-r1.txt').open('x',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=output,verbosity=2,resultclass=Recorder).run(unittest.TestSuite(suites))
    after_source,after_candidate=module.source_cut(),module.candidate_cut()
    after_paths={name:module.observed(F/name) for name in before_paths}
    assert before_source==after_source and before_candidate==after_candidate and before_paths==after_paths
    assert not blocked and executed==expected and stopped==expected
    module.save(D/'negative-r1.json',{'at':utc(),'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
        'tests_run':result.testsRun,'failures':[{'id':test.id(),'traceback':trace} for test,trace in result.failures],
        'errors':[{'id':test.id(),'traceback':trace} for test,trace in result.errors],'skips':result.skipped,
        'exit_status':0 if result.wasSuccessful() else 1,'raw_sha256':sha(D/'negative-r1.txt'),
        'actual_Create_Delete_executed':False,'actual_worker_or_job_created':False,
        'genuine_operator_approval_record_created':False,'blocked_actual_profile_attempts':blocked,
        'controlled_cases':outcomes,'Source290_native_and_hash_exact':True,'candidate294_native_and_hash_exact':True,
        'preserved_paths_before':before_paths,'preserved_paths_after':after_paths,
        'Source_after':after_source,'candidate_after':after_candidate,
        'limitation':'Control-flow/SID/output/resource cases are deliberately simulated negative probes; they are not native profile creation, isolation, cleanup or CETA authorization evidence.'})
    print(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'actual_Create_Delete_executed':False,'controlled_case_count':len(outcomes)}),flush=True)
    sys.exit(0 if result.wasSuccessful() else 1)

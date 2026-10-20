"""Actual safe CLI launchers under retained Windows job custody; no Qt execution."""
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
import base64,csv,importlib,importlib.metadata,io,json,msvcrt,os,struct,sys,time,unittest,uuid,zipfile
from er1_support import *
sys.path.insert(0,str(P/'src'))
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
jobs_source=ordinary(P/'src/ceta/supervisor/windows_jobs.py')
inventory=json.loads((R/'launcher-inventory-r2.json').read_text());generation=json.loads((R/'candidate-generation.json').read_text())
started=utc();candidate_before={str(path.relative_to(Q)):sha(path) for path in Q.rglob('*') if path.is_file()}
FIX=R/('native-staged-fixtures-'+uuid.uuid4().hex[:12]);fs.safe_components(FIX,allow_missing=True);FIX.mkdir()
commands=[];imports=[]

def run_owned(label,executable,arguments,expected_code):
    area=FIX/label;area.mkdir();temp=area/'temp';temp.mkdir()
    outputs=[];owned=None;record=None
    try:
        for name,mode in [('stdin.bin','xb+'),('stdout.bin','xb'),('stderr.bin','xb')]:
            stream=(area/name).open(mode);outputs.append(stream)
            os.set_handle_inheritable(msvcrt.get_osfhandle(stream.fileno()),True)
        env={name:value for name,value in os.environ.items() if name.upper() in {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','COMSPEC','PATH','PATHEXT'}}
        env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PIP_DISABLE_PIP_VERSION_CHECK='1',PIP_NO_INPUT='1',PIP_CONFIG_FILE=os.devnull,TEMP=str(temp),TMP=str(temp))
        image=ordinary(executable);begin=utc();tick=time.monotonic()
        owned=WindowsOwnedProcess.launch(str(executable),tuple(arguments),cwd=str(area),environment=env,
            standard_handles=tuple(msvcrt.get_osfhandle(stream.fileno()) for stream in outputs),expected_image_sha256=image['sha256'])
        pid=owned.pid;creation=owned.creation_time
        if not owned.wait(15):raise TimeoutError('Owned safe CLI exceeded15 seconds')
        exit_code=owned.poll();deadline=time.monotonic()+3
        while owned.active_process_count() and time.monotonic()<deadline:time.sleep(.01)
        empty=owned.active_process_count()==0
        if not empty:raise RuntimeError('Owned CLI descendant lifetime unresolved')
        owned.close();owned=None
        for stream in outputs:stream.close()
        out=(area/'stdout.bin').read_bytes();err=(area/'stderr.bin').read_bytes()
        record={'label':label,'command_argv':[str(executable),*arguments],'cwd':str(area),'started_at':begin,'finished_at':utc(),'elapsed_seconds':time.monotonic()-tick,
                'pid':pid,'creation_time_100ns':creation,'image':image,'expected_exit_status':expected_code,'actual_exit_status':exit_code,'observed_empty_job':empty,'owner_closed':True,
                'stdout':out.decode('utf-8',errors='replace'),'stderr':err.decode('utf-8',errors='replace'),'stdout_sha256':digest(out),'stderr_sha256':digest(err),
                'environment_control_keys':sorted(env),'environment_values_exposed':False,'custody_source':jobs_source,'fixture':str(area),'oracle_passed':exit_code==expected_code}
        write_new(area/'receipt.json',record);commands.append(record)
        if exit_code!=expected_code:raise AssertionError(f'{label}: expected exit{expected_code}, observed{exit_code}')
        return record
    except BaseException:
        if owned is not None:
            owned.terminate(125)
            if owned.wait(5) and owned.active_process_count()==0:owned.close();owned=None
            else:
                write_new(area/'unresolved-owner.json',{'pid':owned.pid,'creation_time':owned.creation_time,'state':'RETAINED_UNRESOLVED_NATIVE_OWNER','at':utc()})
                raise RuntimeError('Retained owned CLI requires coordinator custody')
        raise
    finally:
        if owned is None:
            for stream in outputs:
                if not stream.closed:stream.close()

class StagedLauncherTests(unittest.TestCase):
    def test_exact27_native_stubs_main_scripts_and_current_interpreter(self):
        for row in generation['launchers']:
            with self.subTest(filename=row['filename']):
                before=next(item for item in inventory['launchers'] if item['filename']==row['filename'])
                path=P/row['candidate']['repository_relative_path'];raw=fs.read_bytes(path)
                self.assertEqual(digest(raw),row['candidate']['sha256']);self.assertEqual(len(raw),row['candidate_bytes'])
                stub_size=before['stub_bytes'];self.assertEqual(digest(raw[:stub_size]),before['stub_sha256'])
                pe=struct.unpack_from('<I',raw,0x3c)[0];self.assertEqual(raw[pe:pe+4],b'PE\x00\x00')
                self.assertEqual(struct.unpack_from('<H',raw,pe+4)[0],0x8664)
                self.assertEqual(struct.unpack_from('<H',raw,pe+24+68)[0],3)
                self.assertEqual(raw[stub_size:raw.index(b'\n',stub_size)+1].decode().strip(),'#!'+str(PY))
                self.assertNotIn(b'CETA_Intelligence_Operating_System_Build_Package',raw)
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    self.assertEqual(archive.namelist(),['__main__.py']);self.assertIsNone(archive.testzip())
                    self.assertEqual(archive.read('__main__.py').decode(),before['original_main_script'])
                self.assertEqual(fs.read_bytes(P/row['before_image']['repository_relative_path']),fs.read_bytes(E3/row['source_relative_path']))
    def test_exact3_records_change_only_authorized_hash_size_raw_fields(self):
        total=0
        for row in generation['metadata']:
            old=fs.read_bytes(P/row['before_image']['repository_relative_path']);new=fs.read_bytes(P/row['candidate']['repository_relative_path'])
            self.assertEqual(digest(old),row['source_observation']['sha256']);self.assertEqual(digest(new),row['candidate']['sha256'])
            a=old.splitlines(keepends=True);b=new.splitlines(keepends=True);self.assertEqual(len(a),len(b))
            changed={item['line_number']:item for item in row['row_changes']};self.assertEqual(len(changed),row['changed_rows'])
            for number,(left,right) in enumerate(zip(a,b),1):
                if number not in changed:self.assertEqual(left,right);continue
                item=changed[number];self.assertEqual(digest(left),item['original_line_sha256']);self.assertEqual(digest(right),item['candidate_line_sha256'])
                old_row=next(csv.reader(io.StringIO(left.decode())));new_row=next(csv.reader(io.StringIO(right.decode())))
                self.assertEqual(old_row,item['original_row']);self.assertEqual(new_row,item['candidate_row']);self.assertEqual(old_row[0],new_row[0])
                self.assertEqual(left[-len(bytes.fromhex(item['original_line_ending_hex'])):],right[-len(bytes.fromhex(item['original_line_ending_hex'])):])
                old_body=left.rstrip(b'\r\n');new_body=right.rstrip(b'\r\n')
                old_fields=old_body.rsplit(b',',2);new_fields=new_body.rsplit(b',',2)
                self.assertEqual(old_fields[0],new_fields[0])
                self.assertEqual([value.startswith(b'\"') for value in old_fields[1:]],[value.startswith(b'\"') for value in new_fields[1:]])
                candidate=next(value for value in generation['launchers'] if value['filename']==item['filename'])
                expected_hash='sha256='+base64.urlsafe_b64encode(bytes.fromhex(candidate['candidate']['sha256'])).decode().rstrip('=')
                self.assertEqual(new_row[1],expected_hash);self.assertEqual(int(new_row[2]),candidate['candidate_bytes'])
            total+=len(changed)
        self.assertEqual(total,27)
    def test_all27_entry_points_resolve_to_current_callable_without_invocation(self):
        for row in inventory['launchers']:
            with self.subTest(filename=row['filename']):
                module_name,function=row['entry_point_value'].split(':',1);module=importlib.import_module(module_name);value=getattr(module,function)
                self.assertTrue(callable(value));origin=Path(module.__file__);self.assertTrue(origin.is_relative_to(E3/'Lib/site-packages'))
                imports.append({'filename':row['filename'],'module':module_name,'function':function,'module_observation':ordinary(origin),'callable':True,
                                'entrypoint_function_execution':'NOT_EXECUTED','Qt_tool_execution':'NOT_EXECUTED' if row['filename'].startswith('pyside6-') else 'SAFE_CLI_QUALIFIED_SEPARATELY'})
    def test_original_stale_pip_launcher_actual_failure_is_preserved(self):
        record=run_owned('old-pip-version',E3/'Scripts/pip.exe',['--version'],1)
        original=next(row for row in inventory['launchers'] if row['filename']=='pip.exe')
        self.assertEqual(record['actual_exit_status'],1)
        self.assertEqual(record['image']['sha256'],original['sha256'])
        self.assertFalse(Path(original['original_shebang'][2:]).exists())
        # Actual no-window fixture produced no diagnostic; retain that fact.
        record['old_interpreter_path_exists']=False
        record['old_shebang']=original['original_shebang']
        record['diagnostic_observation']='Empty captured streams under the native no-window/file-handle fixture; exact diagnostic-channel cause not asserted'
    def test_actual_three_staged_pip_aliases_use_current_package_and_python(self):
        for name in ('pip.exe','pip3.exe','pip3.12.exe'):
            with self.subTest(filename=name):
                record=run_owned('staged-'+name.replace('.','-'),Q/'launchers'/name,['--disable-pip-version-check','--version'],0)
                self.assertIn('pip25.0.1'.replace('pip','pip '),record['stdout']);self.assertIn('(python3.12)'.replace('python','python '),record['stdout'])
                self.assertIn(str(E3/'Lib/site-packages/pip'),record['stdout']);self.assertNotIn('CETA_Intelligence_Operating_System_Build_Package',record['stdout'])
    def test_actual_staged_schema_valid_and_invalid_disposable_instances(self):
        schema=FIX/'schema.json';valid=FIX/'valid.json';invalid=FIX/'invalid.json'
        for path,value in [(schema,{'type':'object','required':['count'],'properties':{'count':{'type':'integer','minimum':1}},'additionalProperties':False}),(valid,{'count':2}),(invalid,{'count':'bad'})]:write_new(path,value)
        positive=run_owned('schema-valid',Q/'launchers/jsonschema.exe',['--instance',str(valid),str(schema)],0)
        negative=run_owned('schema-invalid',Q/'launchers/jsonschema.exe',['--instance',str(invalid),str(schema)],1)
        self.assertNotIn('Fatal error in launcher',positive['stderr']+positive['stdout']);self.assertIn('is not of type',negative['stderr']+negative['stdout'])
    def test_actual_builder_refuses_existing_candidates_without_byte_changes(self):
        before={str(path.relative_to(Q)):sha(path) for path in Q.rglob('*') if path.is_file()}
        record=run_owned('existing-output-refusal',PY,['-B','-X','utf8',str(Q/'build_launchers.py')],1)
        self.assertIn('Existing candidate or before-image scope is preserved',record['stderr'])
        self.assertEqual(before,{str(path.relative_to(Q)):sha(path) for path in Q.rglob('*') if path.is_file()})

suite=unittest.TestLoader().loadTestsFromTestCase(StagedLauncherTests);expected=[test.id() for test in suite]
class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.executed=[]
    def startTest(self,test):self.executed.append(test.id());super().startTest(test)
with (R/'staged-tests-r2.txt').open('x',encoding='utf-8',buffering=1) as output:
    with redirect_stdout(output),redirect_stderr(output):result=unittest.TextTestRunner(stream=output,verbosity=2,resultclass=Result).run(suite)
candidate_after={str(path.relative_to(Q)):sha(path) for path in Q.rglob('*') if path.is_file()};assert candidate_after==candidate_before
passed=result.wasSuccessful() and not result.skipped and expected==result.executed
report={'started_at':started,'finished_at':utc(),'command_argv':[sys.executable,'-B','-X','utf8',str(Path(__file__))],'tests_run':result.testsRun,'expected_ids':expected,'executed_ids':result.executed,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
        'failure_details':[{'test_id':test.id(),'traceback':trace} for test,trace in result.failures+result.errors],'actual_cli_invocations':commands,'entrypoint_imports':imports,
        'candidate_before':candidate_before,'candidate_after':candidate_after,'native_fixture_root':str(FIX),'fixture_disposition':'All owned resources retained; all completed CLI processes observed exited with empty Windows jobs, owners closed','raw_sha256':sha(R/'staged-tests-r2.txt'),'exit_status':0 if passed else 1,
        'limits':['Native Windows job custody and own E3 direct interpreter; no arbitrary host-process termination','Only pip version/schema fixtures and existing-output denial executed; all23 Qt CLI/GUI/server/deploy functions NOT EXECUTED','Imports/static binding do not establish all Qt tool operation','Expected negative child exits retained explicitly and do not masquerade as successful executable invocations','No install/update/network, active E3/source/metadata/config or service/host mutation']}
write_new(R/'staged-tests-r2.json',report)
print(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'actual_cli_invocations':len(commands),'static_entrypoint_imports':len(imports),'receipt_sha256':sha(R/'staged-tests-r2.json'),'exit_status':report['exit_status']}))
raise SystemExit(report['exit_status'])

"""Explicit JS8 test-order amendment; frozen author and review evidence preserved."""
from pathlib import Path
import copy, hashlib, importlib.util, json, os, shutil, stat, sys
R=Path(__file__).resolve().parent
PARENT=R.parent
sys.path.insert(0,str(PARENT))
import js8_support as parent
sys.path.remove(str(PARENT))
s=parent.s; F=parent.F; PY=parent.PY; RUN=parent.RUN
Q=F/'.agents/js8-amendment-report1-20261017'
STRICT=parent.STRICT
SCRIPT_NAMES=('amendment_support.py','run_full.py','launch_full.py','publish_source.py','complete_source.py',
              'bounded_custody.py','gc_observer.py','tool_environment.py','fixture_runtime.py','resource_observer.py',
              'candidate_readiness.py','publication_preflight.py')
inputs=parent.inputs
review=parent.review
require_current_claim=parent.require_current_claim

def manifest_record():
    original,old_pin=parent.manifest_record()
    a=current_json(R/'AMENDMENT.json')
    assert a['original_manifest']==parent.exact_ref(parent.Q/'TRANSFER-MANIFEST.json')
    assert a['staging']==exact_ref(R/'STAGED.json')
    staged=current_json(R/'STAGED.json')
    expected=copy.deepcopy(original)
    name=staged['changed_path']
    assert name=='tests/contract/test_cpu_execution_timing_diagnostics.py'
    assert expected['expected_payload_hashes'][name]==staged['before_sha256']
    expected['expected_payload_hashes'][name]=staged['after_sha256']
    expected['Stop_payload_hashes'][name]=staged['after_sha256']
    expected['scripts']=a['reviewed_scripts']
    expected['native_gate']['script']=a['native_gate_script']
    expected['amendment_lineage']=a['staging']
    manifest_path=Q/'TRANSFER-MANIFEST.json'
    assert a['manifest']==exact_ref(manifest_path)
    value=pinned_json(manifest_path,a['manifest']['sha256'])
    assert canonical(value)==canonical(expected),'AMENDMENT_NOT_EXACT_ONE_TEST_DELTA'
    prior_path,prior=proof(a['prior_manifest'])
    assert prior_path==F/'.agents/js8-amendment-order1-20261017/TRANSFER-MANIFEST.json'
    assert a['prior_manifest']['sha256']=='6a99465610569df671fe736914ca2bd37f249e45794d3c6c4a7f5d044f32c31e'
    assert a['prior_amendment']=={'repository_relative_path':'.agents/runtime/js8-20261015/amendment-order1/AMENDMENT.json',
        'sha256':'3152785dde49c1cda26619b651ff89799ba03759c4594eb75004d110a75dadb4'}
    proof(a['prior_amendment'])
    assert prior['expected_payload_hashes']==value['expected_payload_hashes']
    assert prior['case_set']==value['case_set'] and prior['required_independent_ids']==value['required_independent_ids']
    assert a['author']=='/root/full_report_repair' and a['product_payload_changes']==0
    assert scripts()==a['reviewed_scripts']
    assert exact_ref(R/'native-gate/native_case_gate.py')==a['native_gate_script']
    return value,a['manifest']['sha256']

def require_release(path,pin,phase):
    assert phase in ('publication-preflight','publish','destination-full','complete')
    path=s.fs.safe_components(Path(path)); assert path.parent==R/'releases'
    release=pinned_json(path,pin);m,msha=manifest_record()
    assert type(release['schema_version']) is int and release['schema_version']==1
    assert release['executor']=='/root' and release['run_id']==RUN and release['phase']==phase
    assert release['amendment']==exact_ref(R/'AMENDMENT.json')
    assert release['manifest_sha256']==msha and release['reviewed_scripts']==m['scripts']==scripts()
    assert release['Source_publication'] is (phase=='publish') and release['automatic_retry'] is False
    assert release['all_conflicting_Source_pinned_runs_released'] is True
    # Reauthenticate every original author/component/reviewer receipt. This
    # reads the expired historical engineering release; it does not execute it.
    parent.require_release(PARENT/'releases/candidate-full.json',
        s.sha(PARENT/'releases/candidate-full.json'),'candidate-full')
    _,reviewed=proof(release['amendment_review'])
    assert reviewed['author']=='/root/full_report_repair' and reviewed['reviewer']=='/root/publication_recovery_review'
    assert reviewed['decision']=='approved' and type(reviewed['exit_status']) is int and reviewed['exit_status']==0
    assert reviewed['amendment']==release['amendment'] and reviewed['manifest_sha256']==msha
    assert reviewed['reviewed_scripts']==scripts() and reviewed['native_gate_script']==m['native_gate']['script']
    assert release['expected_ids_sha256']==m['case_set']['sha256']
    assert release['Source_before_map_sha256']==m['Source_before_map_sha256']
    if phase in ('candidate-full','destination-full'):
        native_path,_=proof(release['native_case_release']);assert native_path.parent==R/'releases'
    return release


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

def distinct_reviewer(value):
    assert type(value) is str and value and value==value.strip(),'REVIEWER_IDENTITY_REQUIRED'
    assert value not in (s.AUTHOR,'/root'),'DISTINCT_REVIEWER_REQUIRED'
    return value

def retain(primary,secondary,stage,stream=None):
    try:
        data=BaseException.__dict__['__dict__'].__get__(primary)
        prior=dict.get(data,'publication_evidence_failures',())
        if type(prior) is not tuple:prior=()
        trace=BaseException.__dict__['__traceback__'].__get__(secondary)
        dict.__setitem__(data,'publication_evidence_failures',prior+((stage,secondary,trace),))
        if stream is not None:
            prior=dict.get(data,'publication_io_owners',())
            if type(prior) is not tuple:prior=()
            dict.__setitem__(data,'publication_io_owners',prior+((stage,stream),))
    except BaseException:pass

def close(stream,primary,stage):
    try:stream.close()
    except BaseException as secondary:
        if primary is None:
            retain(secondary,secondary,stage,stream);raise
        retain(primary,secondary,stage,stream)

def read_bytes(path):
    stream=Path(path).open('rb');primary=None
    try:return stream.read()
    except BaseException as error:primary=error;raise
    finally:close(stream,primary,'read-close')

def write_bytes(path,raw):
    stream=Path(path).open('xb');primary=None
    try:
        count=stream.write(raw)
        assert type(count) is int and count==len(raw),'SHORT_WRITE'
        stream.flush();os.fsync(stream.fileno())
    except BaseException as error:primary=error;raise
    finally:close(stream,primary,'write-close')

def pinned_bytes(path,pin):
    before=s.ordinary(path);assert before['sha256']==pin,'PROOF_PIN_MISMATCH'
    raw=read_bytes(path)
    assert s.digest(raw)==pin and s.ordinary(path)==before,'PROOF_CHANGED_DURING_READ'
    return raw

def pinned_json(path,pin):return json.loads(pinned_bytes(path,pin).decode('utf-8-sig'))

def current_json(path):return pinned_json(path,s.ordinary(path)['sha256'])

def proof_bytes(reference):
    assert type(reference) is dict and set(reference)=={'repository_relative_path','sha256'}
    name=reference['repository_relative_path']
    assert type(name) is str and name==name.replace('\\','/') and name
    assert not Path(name).is_absolute() and not Path(name).drive
    assert all(part not in ('','.','..') for part in name.split('/'))
    path=F/s.fs.relative_name(name);s.fs.safe_components(path)
    assert path.is_relative_to(F)
    return path,pinned_bytes(path,reference['sha256'])

def proof(reference):
    path,raw=proof_bytes(reference)
    return path,json.loads(raw.decode('utf-8-sig'))

def exact_ref(path):return {'repository_relative_path':Path(path).relative_to(F).as_posix(),'sha256':s.ordinary(path)['sha256']}

def manifest():return manifest_record()[0]

def scripts():return {name:s.ordinary(R/name)['sha256'] for name in SCRIPT_NAMES}

def child_environment(temporary):
    path,value=proof(manifest()['git_dependency'])
    assert path==PARENT/'GIT-SEARCH-DEPENDENCY.json'
    assert s.ordinary(Path(value['git']['path']))==value['git']
    assert value['PATH']==str(Path(value['git']['path']).parent)+';'+value['system32']
    assert Path(shutil.which('git.exe',path=value['PATH']))==Path(value['git']['path'])
    assert Path(value['SystemRoot']).is_dir() and Path(value['system32']).is_dir()
    return {'SystemRoot':value['SystemRoot'],'PATH':value['PATH'],'TEMP':str(temporary),'TMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1'}

def inventory(root):
    out={};pending=[Path(root)]
    while pending:
        parent=pending.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                path=parent/entry.name;info=s.fs.lstat(path);assert not s.fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):pending.append(path)
                else:assert stat.S_ISREG(info.st_mode);out[path.relative_to(root).as_posix()]=s.ordinary(path)
    return out

def verify(*,source='before',environment=True):
    assert Path(sys.executable)==PY and not sys.flags.optimize and os.name=='nt'
    m=manifest();v=inputs();expected=m['expected_payload_hashes']
    for path,row in m['installed_tools'].items():assert s.ordinary(Path(path))==row
    assert len(expected)==352 and len(m['application_paths'])==61
    for name,pin in expected.items():assert s.ordinary(Q/name)['sha256']==pin,('candidate',name)
    for name,row in v['auxiliary_source11'].items():assert s.ordinary(F/name)==row
    for name,row in current_json(R/'STAGED.json')['auxiliary_copies11'].items():assert s.ordinary(Q/name)==row
    if source=='before':
        for name,row in v['Source295'].items():assert s.ordinary(F/name)==row,('Source295',name)
        for name in set(expected)-set(v['Source295']):
            try:s.fs.lstat(F/name)
            except FileNotFoundError:pass
            else:raise AssertionError('CREATE_TARGET_ALREADY_EXISTS:'+name)
    elif source=='after':
        for name,pin in expected.items():assert s.ordinary(F/name)['sha256']==pin,('Source352',name)
        for name,row in v['Source295'].items():
            if name not in m['application_paths']:assert s.ordinary(F/name)==row
    else:raise AssertionError('SOURCE_PHASE_INVALID')
    assert s.ordinary(PY)==v['python'] and s.ordinary(Path(sys._base_executable))==v['base_python']
    if environment:assert inventory(PY.parents[1])==v['E33601']
    assert s.fs.text_git(F,'rev-parse','HEAD')==v['Git']['HEAD']
    assert s.fs.text_git(F,'branch','--show-current')==v['Git']['branch']
    return v

def require_case_ids(actual):
    m=manifest();_,cases=proof(m['case_set']);required=cases['expected_ids']
    assert type(actual) is list and len(actual)==len(set(actual))==cases['expected_count']
    assert actual==required and not any('_FailedTest' in name for name in actual)
    parent=cases['parent1479_ids'];assert [n for n in actual if n in set(parent)]==parent
    parent=cases['parent1556_ids'];assert len(parent)==1556 and [n for n in actual if n in set(parent)]==parent
    for module,count in cases['added_module_counts'].items():
        assert sum(n.startswith(module+'.') for n in actual)==count
    return required

def ids(group):
    import unittest
    if isinstance(group,unittest.TestSuite):
        for item in group:yield from ids(item)
    else:yield group.id()

def require_validation(readiness_reference, *, source='before'):
    readiness=require_candidate_readiness(readiness_reference,source=source)
    local=current_json(PARENT/'validate.json');stored=current_json(PARENT/RUN/'receipts/validate.json')
    keys=STRICT-{'decision'}
    assert type(local) is dict and set(local)==keys
    assert type(stored) is dict and set(stored)==keys|{'git_baseline','observed_git','receipt_hash'}
    assert all(canonical(local[k])==canonical(stored[k]) for k in keys)
    assert local['run_id']==RUN and local['node_id']=='validate' and local['executor_id']=='/root'
    assert type(local['schema_version']) is int and local['schema_version']==1
    assert type(local['exit_status']) is int and local['exit_status']==0 and local['changed_files']==[]
    assert type(local['commands']) is list and all(type(row) is dict and set(row)=={'command','exit_status'} and
        type(row['command']) is str and row['command'] and type(row['exit_status']) is int and row['exit_status']==0 for row in local['commands'])
    assert type(local['validations']) is list and local['validations'] and all(type(row) is dict and set(row)=={'name','passed'} and
        type(row['name']) is str and row['name'] and row['passed'] is True for row in local['validations'])
    assert local['result']['manifest_sha256']==s.sha(Q/'TRANSFER-MANIFEST.json')
    assert local['result']['qualification_kind']=='SOURCE_PUBLICATION_PREFLIGHT'
    assert local['result']['candidate_full_status']=='FAILED' and local['result']['final_acceptance']=='PENDING'
    assert local['result']['source_publication_preflight']==readiness_reference
    assert local['result']['prior_failed_candidate']==readiness['prior_failed_candidate']
    assert readiness['claim_input_hash']==local['input_hash'] and readiness['claim_started_at']==local['started_at']
    assert all('launch_full.py' not in row['command'] and 'run_full.py' not in row['command'] for row in local['commands'])
    expected_command=s.subprocess.list2cmdline([str(PY),*readiness['argv'][1:]])
    assert any(row['command']==expected_command for row in local['commands'])
    assert local['result']['reviewed_scripts']==scripts()
    state=current_json(PARENT/RUN/'state.json');result=current_json(PARENT/RUN/'results/validate.json')
    assert type(result) is dict and set(result)=={'node_id','receipt_hash','result'} and result['node_id']=='validate'
    assert state['nodes']['validate']['state']=='SUCCEEDED'
    assert state['nodes']['validate']['claim'] is None and state['nodes']['validate']['executor_id']==local['executor_id']
    assert state['nodes']['validate']['receipt_hash']==result['receipt_hash']==stored['receipt_hash']
    assert canonical(result['result'])==canonical(stored['result'])
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt
    normalized=validate_receipt(local,run_id=RUN,node_id='validate',executor_id=local['executor_id'],input_hash=local['input_hash'],
        claimed_at=local['started_at'],node=current_json(PARENT/RUN/'graph.json')['graph']['nodes']['validate'])
    from taar.orchestration_persistence import sha256_json
    normalized.pop('receipt_hash');normalized.update(git_baseline=stored['git_baseline'],observed_git=stored['observed_git'])
    assert sha256_json(normalized)==stored['receipt_hash'],'COMPUTED_VALIDATION_FINGERPRINT_MISMATCH'
    assert state['nodes']['validate']['artifact_hash']==sha256_json({'input_hash':local['input_hash'],'result':local['result']})
    return local

def interpreter_observation(v):
    """Measure the same pinned executable designations already required by verify."""
    value=dict(sys_executable=sys.executable,sys_base_executable=sys._base_executable,
        python=s.ordinary(Path(sys.executable)),base_python=s.ordinary(Path(sys._base_executable)))
    assert value['sys_executable']==v['python']['path'] and value['sys_base_executable']==v['base_python']['path']
    assert value['python']==v['python'] and value['base_python']==v['base_python']
    return value

def require_interpreter_command(full,launch,phase):
    v=inputs()
    assert phase in ('candidate-full','destination-full')
    assert s.ordinary(Path(v['python']['path']))==v['python'],'LAUNCHER_NATIVE_PIN_MISMATCH'
    assert s.ordinary(Path(v['base_python']['path']))==v['base_python'],'BASE_NATIVE_PIN_MISMATCH'
    expected=dict(sys_executable=v['python']['path'],sys_base_executable=v['base_python']['path'],
        python=v['python'],base_python=v['base_python'])
    assert canonical(full['interpreter'])==canonical(launch['interpreter'])==canonical(expected),'INTERPRETER_OBSERVATION_MISMATCH'
    actual,command=full['argv'],launch['child_argv']
    assert type(actual) is type(command) is list and len(actual)==len(command)==10 and all(type(x) is str and x for x in actual+command)
    assert actual[0]==v['base_python']['path'] and command[0]==v['python']['path'],'INTERPRETER_ARGV0_MISMATCH'
    ref=full['release']
    assert type(ref) is dict and set(ref)=={'repository_relative_path','sha256'} and launch['release']==ref
    assert type(ref['repository_relative_path']) is str and '\\' not in ref['repository_relative_path']
    relative=s.fs.relative_name(ref['repository_relative_path']);release_path=F/relative
    assert release_path.parent==R/'releases' and type(ref['sha256']) is str and len(ref['sha256'])==64
    assert all(c in '0123456789abcdef' for c in ref['sha256'])
    _,binding=proof(ref)
    assert type(binding['schema_version']) is int and binding['schema_version']==1
    assert binding['executor']=='/root' and binding['run_id']==RUN and binding['phase']==phase
    assert binding['manifest_sha256']==full['manifest_sha256'] and binding['reviewed_scripts']==scripts()
    tail=['-B','-X','utf8',str(R/'run_full.py'),phase,'--release-path',str(release_path),'--release-sha256',ref['sha256']]
    assert actual[1:]==command[1:]==tail,'INTERPRETER_ARGUMENTS_MISMATCH'
    assert launch['record']['native_owner']['image_sha256']==v['python']['sha256'],'OWNED_LAUNCHER_IMAGE_MISMATCH'

def require_full(full,launch,phase,full_reference):
    m=manifest();required=require_case_ids(full['expected_ids'])
    assert full['phase']==phase and full['manifest_sha256']==s.sha(Q/'TRANSFER-MANIFEST.json')
    assert full['Source_publication'] is False and full['Source_accepted'] is False
    assert full['tests_run']==len(required) and type(full['tests_run']) is int
    assert all(type(full[k]) is int and full[k]==0 for k in ('failures','errors','skips','exit_status'))
    assert full['executed_ids']==full['stopped_ids']==required
    assert full['suite_aborted'] is False and full['gc_observation_failed'] is False
    assert full['remaining_threads']==[] and full['captured_journal_fixtures_closed'] is True
    assert full['before_hashes']==full['after_hashes']==full['expected_payload_hashes']==m['expected_payload_hashes']
    assert [row['test_id'] for row in full['uniform_pre_test_collection']]==required
    assert all(row['gc_enabled'] is True for row in full['uniform_pre_test_collection'])
    assert full['source_unchanged'] is True
    assert launch['exit_status']==0 and type(launch['exit_status']) is int and launch['primary_error'] is None
    assert launch['phase']==phase and launch['own_job_only'] is True
    require_interpreter_command(full,launch,phase)
    child=launch['record'];assert child['child_exit']==0 and child['primary_error'] is child['retirement_error'] is None
    assert type(child['child_exit']) is int
    assert child['child_result']==full_reference
    closed=child['native_owner_after']
    assert set(closed)=={'closed','process_closed','thread_closed','job_closed','startup_handles_closed'}
    assert all(value is True for value in closed.values())
    _,native=proof(full['native_case_proof'])
    assert native['passed'] is True and native['release_reader_closed'] is True
    assert native['original_case_id']==m['native_gate']['original_case_id']
    assert native['subject']['mode']==phase and native['subject']['source_root']==str(F if phase=='destination-full' else Q)
    _,root_release=proof(full['release'])
    assert native['release']==root_release['native_case_release']
    assert full['mandatory_full_gate_complete'] is True and full['deferred_ids']==[]
    _,physical=proof(full['physical_custody'])
    assert physical['owned_resources_closed'] is True and physical['remaining_resources']==[]
    _,owners=proof(full['native_owners_proof'])
    expected={'exact_process_job_handles_closed','clocks_retired','bindings_closed',
        'pending_API_custody_accounted','controlled_allocations_released','approval_lifetimes_closed',
        'observer_lifetimes_closed','observer_source_handles_closed','session_lifetimes_closed',
        'CPU_binding_lifetimes_closed','throttling_lifetimes_closed','admission_lifetimes_closed'}
    assert type(owners['obligations']) is dict and set(owners['obligations'])==expected
    assert owners['owned_resources_closed'] is True and all(value is True for value in owners['obligations'].values())
    assert canonical(native['subject'])==canonical(native_case_subject(phase,native['run_nonce']))

def native_case_subject(phase,nonce):
    """Measure the fixed input sets at every original-case gate fence."""
    assert phase in ('candidate-full','destination-full')
    assert type(nonce) is str and len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce)
    m=manifest();v=inputs();root=F if phase=='destination-full' else Q
    payloads={name:s.ordinary(root/name) for name in m['expected_payload_hashes']}
    assert {name:row['sha256'] for name,row in payloads.items()}==m['expected_payload_hashes']
    environment=inventory(PY.parents[1]);assert environment==v['E33601']
    environment['base_python']=s.ordinary(Path(v['base_python']['path']))
    assert environment['base_python']==v['base_python']
    tools={name:s.ordinary(R/name) for name in SCRIPT_NAMES}
    assert {name:row['sha256'] for name,row in tools.items()}==m['scripts']
    for name,row in m['fixture_dependencies'].items():
        tools['fixture/'+name]=s.ordinary(Path(row['path']))
        assert tools['fixture/'+name]==row
    gate_path,_=proof_bytes(m['native_gate']['script'])
    tools['native_gate']=s.ordinary(gate_path)
    helper=F/'.agents/runtime/ac1-20261014/native_fixture_support.py'
    image=F/'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
    return dict(run_id=RUN,run_nonce=nonce,mode=phase,
        original_case_id=m['native_gate']['original_case_id'],source_root=str(root),
        fixture_runtime=str(R/phase/'isolation-harness/.agents/runtime/ac1-20261014'),
        payload_map_sha256=s.digest(canonical(payloads).encode()),
        environment_sha256=s.digest(canonical(environment).encode()),
        tools_sha256=s.digest(canonical(tools).encode()),expected_ids_sha256=m['case_set']['sha256'],
        fixture_helper_sha256=s.ordinary(helper)['sha256'],native_image_sha256=s.ordinary(image)['sha256'])

def capture_native_case_gate(release,phase):
    reference=release['native_case_release'];path,raw=proof_bytes(reference)
    value=json.loads(raw.decode('utf8'));nonce=value['run_nonce']
    gate_path,_=proof_bytes(manifest()['native_gate']['script'])
    spec=importlib.util.spec_from_file_location('js8_frozen_native_case_gate',gate_path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module.NativeCaseGate.capture(path,reference['sha256'],
        expected_subject=native_case_subject(phase,nonce),snapshot=lambda:native_case_subject(phase,nonce),support=s,ports=sys.modules[__name__])


def require_candidate_readiness(reference, *, source='before'):
    from candidate_readiness import require_candidate_readiness as require
    return require(reference,source=source)

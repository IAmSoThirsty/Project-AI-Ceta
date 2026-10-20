"""Freeze the repaired engineering tool; no host profile operation or Source application."""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import ast, ctypes, hashlib, importlib.util, json, os, stat, subprocess, sys
F=Path('T:/00-Active/Project-AI-CETA')
R=Path(__file__).resolve().parent
assert R==F/'.agents/runtime/ac2-20261014/profile-tool-repair-r2'
assert Path(sys.executable)==F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
sys.dont_write_bytecode=True
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
utc=lambda:datetime.now(timezone.utc).isoformat()
def save(path,value):
    assert path.is_relative_to(R)
    with path.open('x',encoding='utf-8',newline='\n') as output:
        json.dump(value,output,indent=2,allow_nan=False);output.write('\n');output.flush();os.fsync(output.fileno())
def ref(path):return {'repository_relative_path':path.relative_to(F).as_posix(),'sha256':sha(path)}
native=ctypes.WinDLL
blocked=[]
class Forbidden:
    def __init__(self,name):self.name=name
    def __call__(self,*args):blocked.append(self.name);raise AssertionError('FORBIDDEN_ACTUAL_PROFILE_MUTATION')
class DLL:
    def __init__(self,dll):self.dll=dll
    def __getattr__(self,name):
        if name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):return Forbidden(name)
        return getattr(self.dll,name)
def guarded(name,*args,**kwargs):return DLL(native(name,*args,**kwargs))

with patch.object(ctypes,'WinDLL',guarded):
    spec=importlib.util.spec_from_file_location('frozen_author_profile_r2',R/'profile_qualification_r2.py')
    tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)
    test=read(R/'tests-r3/negative-r1.json')
    assert test['tests_run']==30 and not test['failures'] and not test['errors'] and not test['skips']
    assert test['expected_ids']==test['executed_ids']==test['stopped_ids']
    assert len(set(test['expected_ids']))==30 and not test['blocked_actual_profile_attempts']
    assert sha(R/'tests-r3/negative-r1.txt')==test['raw_sha256']
    actual_source,actual_candidate=tool.source_cut(),tool.candidate_cut()
    assert actual_source==test['Source_after'] and actual_candidate==test['candidate_after']
    for name,facts in test['preserved_paths_after'].items():assert tool.observed(F/name)==facts
    save(R/'SOURCE-CANDIDATE-READBACK.json',{'at':utc(),'Source290':actual_source,
        'candidate294':actual_candidate,'Source_native_and_hash_exact':True,
        'candidate_native_and_hash_exact':True,'preserved_paths':test['preserved_paths_after'],
        'Source_scope':'The 290 managed payload paths of the exact accepted PERF full receipt, not all repository files.'})
    original=R/'original-inputs';original.mkdir(exist_ok=False)
    archives={}
    paths=[F/'.agents/runtime/ac2-20261014/profile_qualification.py',
        F/'.agents/runtime/ac2-20261014/test_profile_preparation.py',*(F/name for name in tool.DEPENDENCIES)]
    for path in paths:
        payload,facts=tool.capture(path)
        target=original/path.name
        copy=tool.write_payload(target,payload,facts['sha256'])
        archives[path.relative_to(F).as_posix()]={'source':facts,'archive':ref(target),'archive_native':copy}
    save(R/'DEPENDENCY-MAP.json',{'at':utc(),'pinned_runtime_dependencies':tool.DEPENDENCIES,
        'archives':archives,'reader':ref(tool.reader),'manifest':ref(tool.Q/'TRANSFER-MANIFEST.json'),
        'proposal':ref(tool.PROPOSAL),'accepted_Source_baseline':ref(tool.SOURCE_BASELINE),
        'self':ref(R/'profile_qualification_r2.py'),'tests':ref(R/'test_profile_qualification_r2.py')})
    # A fresh actual inspect under capture retains cleanup evidence, not a host-effect claim.
    apis=[];original_init=tool.module._IsolationAPI.__init__
    def captured_init(instance):apis.append(instance);original_init(instance)
    with patch.object(tool.module._IsolationAPI,'__init__',captured_init):inspection=tool.inspect()
    pending=[list(api.pending_native_resources())+list(getattr(api,'_profile_folder_outputs',[])) for api in apis]
    assert not any(pending) and inspection['prior_folder']['HRESULT'] in (-2147024894,-2147024893) and inspection['prior_folder']['path'] is None
    save(R/'ACTUAL-INSPECTION.json',{'at':utc(),'facts':inspection,'API_instances':len(apis),
        'pending_resources_after':pending,'native_Create_Delete_executed':False,'worker_or_job_created':False})
    environment_path=F/'.agents/runtime/er1-20261014/active-application/environment-after.json'
    accepted_path=F/'.agents/runtime/er1-20261014/actual-acceptance.json'
    environment,accepted=read(environment_path),read(accepted_path)
    assert accepted['sequence']==13 and accepted['claims']=={} and set(accepted['actual_states'].values())=={'SUCCEEDED'}
    root=Path(environment['source_root']);expected={row['relative_path']:row for row in environment['members']}
    members={};directory_size_differences=[]
    for name,row in expected.items():
        if row['kind']=='ordinary_file':
            facts=tool.observed(root/name)
            assert facts['sha256']==row['sha256'] and facts['native_identity']==row['native_identity']
            members[name]=facts
        else:
            info=tool.fs.lstat(tool.fs.safe_components(root/name))
            assert stat.S_ISDIR(info.st_mode) and not tool.fs.reparse(info)
            current=tool.fs.file_identity(info);prior=row['native_identity']
            assert {k:v for k,v in current.items() if k!='bytes'}=={k:v for k,v in prior.items() if k!='bytes'}
            if current['bytes']!=prior['bytes']:directory_size_differences.append({'path':name,'before_bytes':prior['bytes'],'after_bytes':current['bytes']})
    names=set()
    for directory,directories,files in os.walk(tool.fs.io_path(root),followlinks=False):
        normal=root/Path(directory).relative_to(Path(tool.fs.io_path(root)))
        names.update((normal/name).relative_to(root).as_posix() for name in directories+files)
    assert names==set(expected) and len(members)==3601
    save(R/'ENVIRONMENT-CONSERVATION.json',{'at':utc(),'accepted_environment':ref(environment_path),
        'accepted_lifecycle':ref(accepted_path),'ordinary_files':len(members),
        'ordinary_bytes':sum(facts['native_identity']['bytes'] for facts in members.values()),
        'ordinary_native_hash_and_membership_exact':True,'all_membership_exact':True,
        'directory_nonsize_metadata_exact':True,'directory_size_differences':directory_size_differences,'members':members})
    previous=F/'.agents/runtime/ac2-20261014/profile-tool-independent-review'
    seal=read(previous/'SEAL.json')
    for name,facts in seal['files'].items():
        assert tool.observed(previous/name)==facts
    assert sha(previous/'REPORT.json')=='d1cb7a1740cae1d55c97e20aec6d599c80ff301960b27d763545d7fa4cdc36a0'
    assert sha(previous/'SEAL.json')=='eb7c7f0d4643644e3d4f26e7a94b4d6431e3203b11669035ebab78848397145d'
    original_tree=ast.parse((F/'.agents/runtime/ac2-20261014/test_profile_preparation.py').read_text())
    original_class=next(node for node in original_tree.body if isinstance(node,ast.ClassDef) and node.name=='ProfilePreparationTests')
    old_public=ast.parse((F/'.agents/runtime/ac2-20261014/profile_qualification.py').read_text())
    new_public=ast.parse((R/'profile_qualification_r2.py').read_text())
    old_args=next(node.args for node in old_public.body if isinstance(node,ast.FunctionDef) and node.name=='qualify')
    new_args=next(node.args for node in new_public.body if isinstance(node,ast.FunctionDef) and node.name=='qualify')
    assert ast.dump(old_args)==ast.dump(new_args)
    assert not blocked
    git=lambda args:subprocess.run(['git',*args],cwd=F,text=True,capture_output=True,check=True).stdout.strip()
    save(R/'SELF-REVIEW.json',{'at':utc(),'author':'/root/wt1_reviewer','independent_review':False,
        'scope':'Repaired operator-side qualification tool and its negative tests only',
        'tool':ref(R/'profile_qualification_r2.py'),'test_source':ref(R/'test_profile_qualification_r2.py'),
        'dependency_map':ref(R/'DEPENDENCY-MAP.json'),'tests':ref(R/'tests-r3/negative-r1.json'),
        'tests_passed':30,'original_methods':4,'new_repair_methods':26,'controlled_lifecycle_cases':18,
        'old_TestCase_AST_sha256':hashlib.sha256(ast.dump(original_class,include_attributes=False).encode()).hexdigest(),
        'repaired_findings':{'PROFILE-TOOL-F01':'Outer custody covers Create/output/SID/journal/retirement/final observations; independent diagnostics preserve primary error and retain unknown state.',
            'PROFILE-TOOL-F02':'Capture exactly one payload under qualified before/after native identity, hash exact payload, fsync and reverify copies; fixture and both launches require fixed IMAGE.',
            'PROFILE-TOOL-F03':'Pin original driver/support hash and native identity before read/import; execute captured verified bytes, bind all copied/transformed dependencies.'},
        'self_review_repairs_before_tests':['Retained token/folder primary exceptions when cleanup also fails.',
            'Capture API/owner objects before constructor calls for partial construction.',
            'Complete identity guards before resource census; include post-delete folder output residue in final retirement state.',
            'Own a fresh evidence directory before effects; refuse occupied directories and preserve their contents.'],
        'failed_attempts':[{'receipt':ref(R/'tests-r1/negative-r1.json'),'failures':3,
            'classification':'Reviewer/test stimulus issue, fixed now',
            'repair':'Changed drift stimulus to equal-size byte change so the expected hash guard is reached; no production guard weakened.',
            'original_test_source':ref(R/'test_profile_qualification_r2.before-same-size-stimulus.py')},
            {'receipt':ref(R/'tests-r2/negative-r1.json'),'failures':0,'tests':26,
             'next':'Four focused additional negative methods added; final 30 all passed.'}],
        'actual_inspection':ref(R/'ACTUAL-INSPECTION.json'),'Source_candidate_readback':ref(R/'SOURCE-CANDIDATE-READBACK.json'),
        'E3_conservation':ref(R/'ENVIRONMENT-CONSERVATION.json'),
        'old_review_seal_preserved':ref(previous/'SEAL.json'),
        'git':{'HEAD':git(['rev-parse','HEAD']),'branch':git(['branch','--show-current']),
               'status':git(['status','--short','--untracked-files=no'])},
        'qualify_public_signature_preserved':True,'actual_profile_Create_Delete_executed':False,
        'Source_application':False,'integrated_product_LOC_credit':0,'host_approval_record_created':False,
        'positive_isolation_qualified':False,'canonical_real_effect_accepted':False,
        'limitations':['Every profile/control-flow success or failure in negative tests is explicitly simulated; no native Create/Delete outcome is claimed.',
            'The coordinator must preserve the actual current user reply; typed receipt fields alone cannot prove a human utterance.',
            'No OS-atomic fence against an outside same-name profile replacement is claimed; no replacement was observed.',
            'Reopen if exact managed Source290, frozen candidate294, dependencies, interpreter, caller identity or tool cut changes.',
            'Owner-approved positive host qualification and independent review remain pending.'],
        'next':'Distinct Root review of this exact tool, tests, captured dependency transforms, and evidence before any host approval question.'})
    # Freeze every author-owned ordinary member. A separate Root review may add its own subtree.
    files={}
    for path in sorted(R.rglob('*')):
        info=tool.fs.lstat(tool.fs.safe_components(path));assert not tool.fs.reparse(info)
        if stat.S_ISREG(info.st_mode):files[path.relative_to(R).as_posix()]=tool.observed(path)
    save(R/'AUTHOR-SEAL.json',{'at':utc(),'author':'/root/wt1_reviewer','ordinary_files':len(files),
        'files':files,'tool':ref(R/'profile_qualification_r2.py'),'self_review':ref(R/'SELF-REVIEW.json'),
        'Source_changes':[],'actual_native_profile_effects':[],'authority_records_created':[],
        'TAAR_claim':'None requested or acquired for this separately scoped engineering-tool repair.',
        'author_write_scope_released':True,'frozen_members_read_only':True,
        'independent_reviewer_may_create_separately_owned_subtree':True})
    print(json.dumps({'tool':sha(R/'profile_qualification_r2.py'),'tests':sha(R/'test_profile_qualification_r2.py'),
        'self_review':sha(R/'SELF-REVIEW.json'),'seal':sha(R/'AUTHOR-SEAL.json'),
        'ordinary_files':len(files),'tests_passed':30,'actual_Create_Delete':False}),flush=True)

"""Deterministic provider faults and work-local traversal controls."""
from pathlib import Path
import copy,hashlib,json,os,stat,sys,unittest
from unittest.mock import patch
import directory_snapshot as d
W=Path(__file__).resolve().parent
FIXTURE_ROOT=W/'fixtures'
PROBE=json.loads((W/'DIRECTORY-HANDLE-PROBE.json').read_bytes())['directories'][0]
class Hostile(KeyboardInterrupt):
    def __setattr__(self,key,value):raise RuntimeError('hostile setter')
    @property
    def add_note(self):raise RuntimeError('hostile diagnostic getter')
def storage(error):return BaseException.__dict__['__dict__'].__get__(error)
class Provider:
    def __init__(self):
        self.raw=copy.deepcopy(PROBE['raw_path_before_open']);self.native=copy.deepcopy(PROBE['native_handle_before'])
        self.queries=self.paths=self.closes=self.enums=0;self.on_query=self.on_path=self.on_close=self.on_enum=None
    def open(self,path):return 123
    def path_stat(self,path):
        self.paths+=1;value=copy.deepcopy(self.raw)
        value['st_atime_ns']+=self.paths*100;value['st_atime']=value['st_atime_ns']/1e9
        if self.paths%2==0:value['st_size']=0
        if self.on_path:self.on_path(self.paths,value)
        return value
    def query(self,handle):
        self.queries+=1;value=copy.deepcopy(self.native);value['basic']['LastAccessTime']+=self.queries
        if self.on_query:self.on_query(self.queries,value)
        return value
    def close(self,handle):
        self.closes+=1
        if self.on_close:self.on_close()
    def children(self,path):
        self.enums+=1
        if self.on_enum:return self.on_enum(self.enums)
        return ['one','two']
class DirectoryMetadataTests(unittest.TestCase):
    def opened(self,provider=None):return d.Directory(W/'controlled-directory',provider or Provider())
    def test_consistent_provider_retains_access_and_path_size_provenance(self):
        p=Provider()
        with self.opened(p) as value:
            self.assertEqual(value.names('INITIAL'),value.names('FINAL'))
            self.assertEqual(value.record()['bytes'],p.native['standard']['EndOfFile'])
            recorded=value.provenance()
        self.assertEqual(p.closes,1)
        self.assertEqual({x['metadata']['st_size'] for x in recorded['raw_path_observations']},{0,p.raw['st_size']})
        self.assertGreater(len({x['metadata']['basic']['LastAccessTime'] for x in recorded['raw_handle_observations']}),1)
    def test_original_probe_remains_failed_and_separate_qualification_is_bound(self):
        process=json.loads((W/'DIRECTORY-HANDLE-PROBE-PROCESS.json').read_bytes())
        result=json.loads((W/'PROBE-SECURITY-QUALIFICATION.json').read_bytes())
        self.assertEqual(process['exit_status'],1);self.assertTrue(result['qualified_security_provider'])
        self.assertEqual(result['authority_policy_sha256'],d.POLICY_SHA)
    def test_raw_path_size_outside_zero_or_same_handle_EOF_refused(self):
        p=Provider();p.on_path=lambda count,value:value.__setitem__('st_size',17) if count==3 else None
        with self.assertRaisesRegex(AssertionError,'path-size'):
            with self.opened(p) as value:value.names('INITIAL')
        self.assertEqual(p.closes,1)
    def test_same_handle_whole_subtree_security_drift_refused(self):
        p=Provider();p.on_query=lambda count,value:value['basic'].__setitem__('ChangeTime',value['basic']['ChangeTime']+1) if count==4 else None
        with self.assertRaisesRegex(AssertionError,'handle security changed'):
            with self.opened(p) as value:value.names('INITIAL');value.names('FINAL')
    def test_duplicate_names_refused(self):
        p=Provider();p.on_enum=lambda count:['one','one']
        with self.assertRaisesRegex(AssertionError,'duplicate'):
            with self.opened(p) as value:value.names('INITIAL')
    def test_invalid_physical_names_refused(self):
        for name in ('.','..','a/b','a\\b'):
            p=Provider();p.on_enum=lambda count:[name]
            with self.subTest(name=name),self.assertRaisesRegex(AssertionError,'invalid'):
                with self.opened(p) as value:value.names('INITIAL')
    def test_setup_query_hostile_primary_and_close_secondary_preserved(self):
        p=Provider();primary=Hostile('query interrupted');secondary=OSError('close failed')
        p.on_query=lambda *a:(_ for _ in ()).throw(primary)
        p.on_close=lambda:(_ for _ in ()).throw(secondary)
        with self.assertRaises(Hostile) as caught:
            with self.opened(p):self.fail('setup must not publish')
        self.assertIs(caught.exception,primary);self.assertEqual(p.closes,1)
        data=storage(primary);self.assertIs(data['directory_snapshot_primary_exc_info'][1],primary)
        self.assertIs(data['directory_snapshot_secondary_exc_info'][0][1],secondary)
        self.assertEqual(data['directory_snapshot_handle'],123)
    def test_body_hostile_primary_and_close_secondary_preserved(self):
        p=Provider();primary=Hostile('body interrupted');secondary=OSError('close failed')
        p.on_close=lambda:(_ for _ in ()).throw(secondary)
        with self.assertRaises(Hostile) as caught:
            with self.opened(p):raise primary
        self.assertIs(caught.exception,primary);data=storage(primary)
        self.assertIs(data['directory_snapshot_primary_exc_info'][1],primary)
        self.assertIs(data['directory_snapshot_secondary_exc_info'][0][1],secondary)
        self.assertEqual(p.closes,1)
    def test_cleanup_only_hostile_primary_retains_handle_custody(self):
        p=Provider();primary=Hostile('cleanup interrupted');p.on_close=lambda:(_ for _ in ()).throw(primary)
        with self.assertRaises(Hostile) as caught:
            with self.opened(p):pass
        self.assertIs(caught.exception,primary);self.assertEqual(storage(primary)['directory_snapshot_handle'],123)
    def test_enumeration_hostile_error_identity_retained(self):
        p=Provider();primary=Hostile('enumeration interrupted');p.on_enum=lambda count:(_ for _ in ()).throw(primary)
        with self.assertRaises(Hostile) as caught:
            with self.opened(p) as value:value.names('INITIAL')
        self.assertIs(caught.exception,primary);self.assertEqual(p.closes,1)
    def test_os_scandir_body_and_close_faults_preserve_hostile_primary(self):
        primary=Hostile('iteration interrupted');secondary=OSError('enumerator close')
        class Stream:
            def __iter__(self):raise primary
            def close(self):raise secondary
        with patch.object(d.os,'scandir',return_value=Stream()),self.assertRaises(Hostile) as caught:
            d.WinProvider.children(object.__new__(d.WinProvider),W)
        self.assertIs(caught.exception,primary);self.assertIs(storage(primary)['directory_scandir_secondary_exc_info'][0][1],secondary)
    def test_public_interface_refuses_other_workspace_and_policy(self):
        for workspace,root,ignored in ((W,d.F,d.EXPECTED_IGNORED),(d.F,Path('T:/'),d.EXPECTED_IGNORED),(d.F,d.F,frozenset())):
            with self.subTest(workspace=str(workspace)),self.assertRaises(AssertionError):d.snapshot(workspace,root,ignored)
    def test_no_native_provider_is_constructed_at_import(self):
        self.assertEqual(d.LEGACY_SHA,hashlib.sha256(d.LEGACY.read_bytes()).hexdigest())
    def test_reusing_context_refused_without_opening_new_handle(self):
        p=Provider();value=self.opened(p)
        with value:pass
        with self.assertRaises(AssertionError):value.__enter__()
        self.assertEqual(p.closes,1)
def metadata_fault(kind,key):
    def test(self):
        p=Provider()
        def alter(count,value):
            if count==2:
                old=value[kind][key];value[kind][key]=('0'*32 if old!='0'*32 else '1'*32) if key=='FileId' else old+1
        p.on_query=alter
        with self.assertRaises(AssertionError):
            with self.opened(p) as value:value.names('INITIAL')
        self.assertEqual(p.closes,1)
    return test
for kind,keys in dict(basic=('CreationTime','LastWriteTime','ChangeTime','FileAttributes'),
    standard=('AllocationSize','EndOfFile','NumberOfLinks','DeletePending','Directory'),
    identity=('VolumeSerialNumber','FileId')).items():
    for key in keys:setattr(DirectoryMetadataTests,'test_native_drift_'+kind+'_'+key,metadata_fault(kind,key))
def path_fault(key):
    def test(self):
        p=Provider()
        def alter(count,value):
            if count==3:value[key]+=1
        p.on_path=alter
        with self.assertRaises(AssertionError):
            with self.opened(p) as value:value.names('INITIAL')
        self.assertEqual(p.closes,1)
    return test
for key in ('st_dev','st_ino','st_mode','st_file_attributes','st_reparse_tag','st_nlink','st_mtime_ns','st_birthtime_ns','st_ctime_ns','st_uid','st_gid'):
    setattr(DirectoryMetadataTests,'test_path_security_drift_'+key,path_fault(key))
class DiskProvider:
    """Recording provider for work-only traversal tests; no Win32 calls."""
    def __init__(self):self.handles={};self.frozen={};self.closes=0;self.on_children=None
    def path_stat(self,path):return d.raw(os.lstat(d.physical(path)))
    def open(self,path):
        handle=len(self.handles)+1;self.handles[handle]=path;value=self.path_stat(path)
        tick=lambda key:value[key]//100+116444736000000000
        self.frozen[handle]=dict(basic=dict(CreationTime=tick('st_birthtime_ns'),LastAccessTime=tick('st_atime_ns'),
            LastWriteTime=tick('st_mtime_ns'),ChangeTime=tick('st_mtime_ns'),FileAttributes=value['st_file_attributes']),
            standard=dict(AllocationSize=value['st_size'],EndOfFile=value['st_size'],NumberOfLinks=value['st_nlink'],DeletePending=0,Directory=1),
            identity=dict(VolumeSerialNumber=value['st_dev'],FileId=value['st_ino'].to_bytes(16,'little').hex()))
        return handle
    def query(self,handle):return copy.deepcopy(self.frozen[handle])
    def close(self,handle):self.closes+=1
    def children(self,path):
        names=sorted(item.name for item in os.scandir(d.physical(path)))
        return self.on_children(path,names) if self.on_children else names
class TraversalTests(unittest.TestCase):
    def fixture(self,name):
        base=FIXTURE_ROOT/name;base.mkdir(parents=True,exist_ok=False)
        (base/'ordinary.txt').write_bytes(b'ds1 immutable fixture\n');(base/'empty').mkdir()
        return base
    def test_work_tree_files_match_original_native_hash_shape(self):
        base=self.fixture('shape');provider=DiskProvider();observed=d._snapshot_tree(base,d.F,d.EXPECTED_IGNORED,provider)
        key=(base/'ordinary.txt').relative_to(d.F).as_posix()
        self.assertEqual(observed['files'][key],d.legacy.stable(base/'ordinary.txt'))
        self.assertEqual(d.file_map(observed),{key:hashlib.sha256(b'ds1 immutable fixture\n').hexdigest()})
        self.assertEqual(len(observed['directories']),2);self.assertEqual(provider.closes,2)
    def test_ignored_directories_and_named_regular_files_follow_original_policy(self):
        base=self.fixture('ignored');(base/'.git').mkdir();(base/'.git'/'excluded.txt').write_text('excluded')
        (base/'.pytest_cache').write_text('ordinary file must count')
        (base/'.project-ai'/'automation').mkdir(parents=True);(base/'.project-ai'/'automation'/'excluded.txt').write_text('excluded')
        value=d._snapshot_tree(base,d.F,d.EXPECTED_IGNORED,DiskProvider())
        names={Path(name).name for name in value['files']}
        self.assertEqual(names,{'ordinary.txt','.pytest_cache'})
    def test_membership_drift_at_final_subtree_boundary_refused(self):
        base=self.fixture('membership');p=DiskProvider();calls={}
        def children(path,names):
            calls[path]=calls.get(path,0)+1
            return sorted(names+['new-entry']) if path==base and calls[path]==2 else names
        p.on_children=children
        with self.assertRaisesRegex(AssertionError,'names changed'):d._snapshot_tree(base,d.F,d.EXPECTED_IGNORED,p)
    def test_case_alias_refused(self):
        base=self.fixture('case');p=DiskProvider()
        p.on_children=lambda path,names:sorted(names+['ORDINARY.TXT']) if path==base else names
        with self.assertRaisesRegex(AssertionError,'case alias'):d._snapshot_tree(base,d.F,d.EXPECTED_IGNORED,p)
    def test_original_regular_file_mode_drift_still_refused(self):
        base=self.fixture('file-mode');original=d.legacy.native;calls=[]
        def native(path):
            value=original(path);calls.append(path)
            if len(calls)==2:value=dict(value,mode=value['mode']^0o200)
            return value
        with patch.object(d.legacy,'native',side_effect=native),self.assertRaisesRegex(AssertionError,'file changed'):
            d.legacy.stable(base/'ordinary.txt')

class NestedCustodyTests(unittest.TestCase):
    def provider(self,handle,fault=None):
        p=Provider();p.open=lambda path:handle
        if fault is not None:p.on_close=lambda:(_ for _ in ()).throw(fault)
        return p
    def test_inner_close_failure_survives_successful_outer_unwind_and_exact_traceback(self):
        primary=Hostile('original body');secondary=OSError('inner close');outer=self.provider(101);inner=self.provider(202,secondary)
        original=None
        try:
            with d.Directory(W/'outer',outer):
                with d.Directory(W/'inner',inner):
                    try:raise primary
                    except BaseException:original=sys.exc_info();raise
        except BaseException as caught:self.assertIs(caught,primary)
        data=storage(primary);frames=data['directory_snapshot_custody']
        self.assertIs(data['directory_snapshot_primary_exc_info'][2],original[2])
        self.assertEqual([x['handle'] for x in frames],[202,101]);self.assertEqual([x['closed'] for x in frames],[False,True])
        self.assertIs(data['directory_snapshot_secondary_exc_info'][0][1],secondary)
        self.assertEqual(data['directory_snapshot_handle'],202);self.assertIs(data['directory_snapshot_observation'],frames[0]['observation'])
        self.assertEqual((inner.closes,outer.closes),(1,1))
    def test_three_level_secondary_order_and_every_handle_retained(self):
        primary=Hostile('body');faults=[OSError(str(n)) for n in range(3)]
        providers=[self.provider(101+n,faults[n]) for n in range(3)]
        with self.assertRaises(Hostile) as caught:
            with d.Directory(W/'outer',providers[0]):
                with d.Directory(W/'middle',providers[1]):
                    with d.Directory(W/'inner',providers[2]):raise primary
        self.assertIs(caught.exception,primary);data=storage(primary)
        self.assertEqual([x['handle'] for x in data['directory_snapshot_custody']],[103,102,101])
        self.assertEqual([x[1] for x in data['directory_snapshot_secondary_exc_info']],list(reversed(faults)))
        self.assertTrue(all(p.closes==1 for p in providers))
    def test_cleanup_only_inner_primary_survives_successful_outer_close(self):
        primary=Hostile('inner cleanup');outer=self.provider(101);inner=self.provider(202,primary)
        with self.assertRaises(Hostile) as caught:
            with d.Directory(W/'outer',outer):
                with d.Directory(W/'inner',inner):pass
        self.assertIs(caught.exception,primary);data=storage(primary)
        self.assertEqual([x['handle'] for x in data['directory_snapshot_custody']],[202,101])
        self.assertIs(data['directory_snapshot_secondary_exc_info'][0][1],primary)
    def test_inner_setup_query_fault_plus_close_fault_retained_through_outer(self):
        primary=Hostile('setup query');secondary=OSError('setup close');outer=self.provider(101);inner=self.provider(202,secondary)
        inner.on_query=lambda *a:(_ for _ in ()).throw(primary)
        with self.assertRaises(Hostile) as caught:
            with d.Directory(W/'outer',outer):
                with d.Directory(W/'inner',inner):self.fail('setup must fail')
        self.assertIs(caught.exception,primary);data=storage(primary)
        self.assertEqual([x['handle'] for x in data['directory_snapshot_custody']],[202,101])
        self.assertIs(data['directory_snapshot_secondary_exc_info'][0][1],secondary)
    def test_successful_inner_close_does_not_hide_failed_outer_custodian(self):
        primary=Hostile('body');secondary=OSError('outer close');outer=self.provider(101,secondary);inner=self.provider(202)
        with self.assertRaises(Hostile):
            with d.Directory(W/'outer',outer):
                with d.Directory(W/'inner',inner):raise primary
        frames=storage(primary)['directory_snapshot_custody']
        self.assertEqual([x['closed'] for x in frames],[True,False]);self.assertIs(frames[1]['secondary_exc_info'][0][1],secondary)
    def test_successful_handle_query_retained_when_following_path_stat_fails(self):
        p=self.provider(303);primary=Hostile('path read');secondary=OSError('close')
        p.on_path=lambda count,value:(_ for _ in ()).throw(primary) if count==3 else None
        p.on_close=lambda:(_ for _ in ()).throw(secondary);opened=d.Directory(W/'partial',p)
        with self.assertRaises(Hostile) as caught:
            with opened:opened.names('CONTROLLED')
        self.assertIs(caught.exception,primary);self.assertEqual(p.queries,len(opened.raw_handles));self.assertEqual(p.queries,2)
        self.assertEqual(opened.raw_handles[-1]['stage'],'CONTROLLED_BEFORE_ENUMERATION')
        self.assertIs(storage(primary)['directory_snapshot_secondary_exc_info'][0][1],secondary)
    def test_successful_raw_handle_and_path_retained_when_binding_fails(self):
        p=self.provider(303);p.on_path=lambda count,value:value.__setitem__('st_ino',17) if count==3 else None
        opened=d.Directory(W/'binding',p)
        with self.assertRaises(AssertionError):
            with opened:opened.names('CONTROLLED')
        self.assertEqual(len(opened.raw_handles),2);self.assertEqual(len(opened.raw_paths),3)
        self.assertEqual(opened.raw_paths[-1]['metadata']['st_ino'],17)
    def partial_native(self,failed_class):
        import ctypes as C
        from types import SimpleNamespace
        primary=Hostile('native class query');secondary=OSError('close');base=Provider()
        class P(d.WinProvider):
            def __init__(self):self.closes=0;self.api=SimpleNamespace(GetFileInformationByHandleEx=self.info)
            def path_stat(self,path):return copy.deepcopy(base.raw)
            def open(self,path):return 404
            def close(self,handle):self.closes+=1;raise secondary
            def info(self,handle,number,pointer,size):
                if number==failed_class:raise primary
                kind,key={0:(d.Basic,'basic'),1:(d.Standard,'standard'),18:(d.Identity,'identity')}[number]
                value=kind()
                for name,typ in kind._fields_:
                    raw=base.native[key][name]
                    if name=='FileId':getattr(value,name)[:]=bytes.fromhex(raw)
                    else:setattr(value,name,raw)
                C.memmove(pointer,C.byref(value),size);return 1
        p=P();opened=d.Directory(W/'native-partial',p)
        with self.assertRaises(Hostile) as caught:
            with opened:self.fail('query must fail')
        self.assertIs(caught.exception,primary);self.assertEqual(p.closes,1)
        row=opened.raw_handles[-1];self.assertFalse(row['complete']);self.assertEqual(row['failed_class'],failed_class)
        self.assertEqual(row['completed_classes'],(0,) if failed_class==1 else (0,1))
        self.assertEqual(set(row['metadata']),{'basic'} if failed_class==1 else {'basic','standard'})
        data=storage(primary);self.assertIs(data['directory_handle_query_failures'][-1]['exc_info'][1],primary)
        self.assertIs(data['directory_snapshot_secondary_exc_info'][0][1],secondary)
    def test_successful_Basic_retained_when_Standard_query_fails(self):self.partial_native(1)
    def test_successful_Basic_Standard_retained_when_Id_query_fails(self):self.partial_native(18)

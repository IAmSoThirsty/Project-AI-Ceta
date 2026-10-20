"""Bind exact relocated launchers to current installed metadata without mutation."""
from pathlib import Path
import ast,base64,csv,importlib.metadata as metadata,io,json,os,struct,sys,zipfile
from er1_support import *
started=utc();assert Path.cwd()==P.parent
current=json.loads((R/RUN/'claims.json').read_text())['discover'];assert current['executor_id']==ACTOR
observed=snapshot_tree();assert observed['ordinary_files']>0 and observed['reparse_not_followed']==0
if (R/'E3-before.json').exists():
    before=json.loads((R/'E3-before.json').read_text())
    assert observed['members']==before['members'] and observed['root_native_identity']==before['root_native_identity']
    write_new(R/'E3-discovery-r2.json',observed)
else:
    before=observed;write_new(R/'E3-before.json',before)
from pip._vendor.distlib.scripts import ScriptMaker
from pip._internal.operations.install.wheel import get_console_script_specs
import pip._vendor.distlib.scripts as distlib_scripts
import pip._internal.operations.install.wheel as wheel
maker=ScriptMaker(None,str(Q/'launchers'))
stub=maker._get_launcher('t');stub_size=len(stub);stub_hash=digest(stub)
assert stub.startswith(b'MZ') and stub_hash=='81a618f21cb87db9076134e70388b6e9cb7c2106739011b6a51772d22cae06b7'
distributions=list(metadata.distributions());entries=[]
for distribution in distributions:
    for entry in distribution.entry_points:
        if entry.group in {'console_scripts','gui_scripts'}:entries.append((distribution,entry))
pip_dist=metadata.distribution('pip');pip_console={entry.name:entry.value for entry in pip_dist.entry_points if entry.group=='console_scripts'}
pip_specs=get_console_script_specs(pip_console);pip_aliases={name.strip():value.strip() for name,value in (spec.split('=',1) for spec in pip_specs)}
assert pip_aliases['pip3.12']==pip_console['pip'] and 'ENSUREPIP_OPTIONS' not in os.environ
old_python=str(P.parent/'CETA_Intelligence_Operating_System_Build_Package'/PY.relative_to(P))
launchers=[];other=[];metadata_observations={}
for member in before['members']:
    if member['kind']!='ordinary_file' or not member['relative_path'].startswith('Scripts/'):continue
    path=E3/member['relative_path'];name=path.name;data=fs.read_bytes(path)
    if path.suffix.lower()!='.exe' or name in {'python.exe','pythonw.exe'}:
        other.append({**member,'classification':'CURRENT_INTERPRETER' if name in {'python.exe','pythonw.exe'} else 'ACTIVATION_OR_OTHER_SCRIPT_PRESERVED','former_root_literal_present':b'CETA_Intelligence_Operating_System_Build_Package' in data});continue
    assert data[:stub_size]==stub and data[stub_size:stub_size+2]==b'#!'
    end=data.index(b'\n',stub_size)+1;shebang=data[stub_size:end].decode().strip()
    assert shebang=='#!'+old_python
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.namelist()==['__main__.py'];payload=archive.read('__main__.py');assert not archive.testzip()
    imports=[node for node in ast.parse(payload.decode()).body if isinstance(node,ast.ImportFrom)]
    assert len(imports)==1 and len(imports[0].names)==1
    old_module=imports[0].module;old_function=imports[0].names[0].name
    matches=[(distribution,entry) for distribution,entry in entries if entry.name==path.stem]
    binding_kind='DIRECT_INSTALLED_ENTRY_POINT'
    if not matches:
        assert path.stem=='pip3.12' and path.stem in pip_aliases
        matches=[(pip_dist,entry) for entry in pip_dist.entry_points if entry.group=='console_scripts' and entry.name=='pip']
        binding_kind='INSTALLED_PIP_VERSION_ALIAS_GENERATOR'
    assert len(matches)==1
    distribution,entry=matches[0];assert entry.group=='console_scripts'
    value=entry.value;assert value==old_module+':'+old_function
    spec_name=path.stem+' = '+value
    generated_main=maker._get_script_text(__import__('pip._vendor.distlib.util',fromlist=['get_export_entry']).get_export_entry(spec_name)).encode('utf-8')
    assert generated_main==payload
    info_path=Path(distribution._path);assert info_path.is_relative_to(E3/'Lib/site-packages')
    metadata_files=[]
    for leaf in ('METADATA','entry_points.txt','RECORD','WHEEL','INSTALLER'):
        item=info_path/leaf
        if item.exists():
            observation=ordinary(item);metadata_observations[str(item)]=observation;metadata_files.append(observation)
    record=list(csv.reader((info_path/'RECORD').read_text()))
    rows=[row for row in record if row and row[0].replace('\\','/')=='../../Scripts/'+name]
    assert len(rows)==1 and len(rows[0])==3
    expected_record='sha256='+base64.urlsafe_b64encode(bytes.fromhex(member['sha256'])).decode().rstrip('=')
    assert rows[0][1]==expected_record and int(rows[0][2])==member['bytes']
    launchers.append({**member,'filename':name,'classification':'STALE_FORMER_ROOT_CONSOLE_LAUNCHER','current_target_interpreter':str(PY),'original_shebang':shebang,
                     'distribution':distribution.metadata['Name'],'distribution_version':distribution.version,'metadata_directory':str(info_path),'metadata_files':metadata_files,
                     'entry_point_group':entry.group,'entry_point_name':entry.name,'entry_point_value':entry.value,'binding_kind':binding_kind,'generation_specification':spec_name,
                     'original_main_script_sha256':digest(payload),'original_main_script_bytes':len(payload),'original_main_script':payload.decode(),'stub_bytes':stub_size,'stub_sha256':stub_hash,
                     'installed_RECORD_row':rows[0],'execution_classification':'SAFE_NONINTERACTIVE_CLI_PROBES' if name in {'pip.exe','pip3.exe','pip3.12.exe','jsonschema.exe'} else 'STATIC_IMPORT_ONLY_NOT_EXECUTED'})
assert len(launchers)==27 and len(other)==6
assert len({row['filename'] for row in launchers})==27
try:aggregate={'state':'AVAILABLE','version':metadata.version('PySide6')}
except metadata.PackageNotFoundError as exc:aggregate={'state':'UNAVAILABLE_EXISTING_AGGREGATE_DISTRIBUTION_METADATA','exception_type':type(exc).__name__,'distribution_name':'PySide6'}
assert aggregate['state'].startswith('UNAVAILABLE')
primitives=[ordinary(Path(distlib_scripts.__file__)),ordinary(Path(wheel.__file__)),ordinary(Path(distlib_scripts.__file__).parent/'t64.exe')]
assert primitives[2]['sha256']==stub_hash
result={'schema_version':1,'job':'ER1 narrow console launcher relocation candidate','actor':ACTOR,'started_at':started,'finished_at':utc(),'source_root':str(P),'environment_root':str(E3),'candidate_root':str(Q),
        'interpreter':ordinary(PY),'pythonw':ordinary(E3/'Scripts/pythonw.exe'),'base_interpreter':ordinary(Path(sys._base_executable)),
        'sys_prefix':sys.prefix,'python_version':sys.version,'native_E3_snapshot':reference(R/'E3-before.json'),'source_snapshot_counts':{key:before[key] for key in ('ordinary_files','ordinary_bytes','directories','reparse_not_followed')},
        'launchers':launchers,'unmodified_other_scripts':other,'stale_launcher_count':27,'current_interpreter_count':2,'unknown_launcher_count':0,'all_classifications':{'stale_console':27,'current_interpreters':2,'other_scripts_preserved':4},
        'installed_script_primitives':primitives,'pip_console_metadata':pip_console,'verified_pip_console_specs':pip_specs,'aggregate_PySide6_metadata':aggregate,
        'boundary':'Only new ER1 runtime evidence and subsequent staged candidate writes. No active E3/library/metadata/source/global configuration mutation. No installer or network operation.','exit_status':0}
write_new(R/'launcher-inventory.json',result)
commands=[{'command':__import__('subprocess').list2cmdline([sys.executable,'-B','-X','utf8',str(Path(__file__))]),'exit_status':0}]
completed=complete('discover',{'inventory':reference(R/'launcher-inventory.json'),'E3_before':reference(R/'E3-before.json'),'stale_launchers':27,'direct_metadata_bindings':26,'verified_pip_alias_bindings':1,'unknown_launchers':0,'E3_source_mutation':False,'prior_failure':reference(R/'discovery-r1-failure.json')},commands,[('Exact27 launcher old shebang/main/stub/installed RECORD identities observed',True),('All entrypoints bound to installed metadata or standard pip alias generator',True),('AllE3 ordinary/library/interpreter/script members hashed without mutation',True),('Aggregate PySide6 metadata unavailability preserved explicitly',True)])
print(json.dumps({'stale_launchers':27,'unknown_launchers':0,'E3_ordinary_files':before['ordinary_files'],'E3_ordinary_bytes':before['ordinary_bytes'],'inventory_sha256':sha(R/'launcher-inventory.json'),'sequence':completed.get('sequence'),'aggregate_PySide6':aggregate}))

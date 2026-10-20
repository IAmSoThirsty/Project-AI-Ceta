"""Construct only ER1's exact staged launchers through installed ScriptMaker.

This is a preparation tool. It has no operation that publishes into E3. Existing
source files, installed metadata, interpreter/library bytes and earlier evidence
remain read-only. A standard ScriptMaker file-operation sink collects generated
bytes before exclusive candidate publication, avoiding its in-use replacement
fallback and preserving every pre-existing destination.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import sys
import zipfile

P=Path(r'T:\00-Active\Project-AI-CETA')
Q=P/'.agents/er1-20261014';R=P/'.agents/runtime/er1-20261014'
E3=P/'.agents/source-assembly-20261014T021300Z/.agents/e3'
INVENTORY_SHA256='c9446a4099517d2bdc3e1a4761c28561f2f3949b7b742c348ae9eddeda574007'
sys.dont_write_bytecode=True
sys.path.insert(0,str(R))
from er1_support import fs,ordinary,reference,write_new,utc

def sha(data):return hashlib.sha256(data).hexdigest()

class CandidateEmission:
    """Standard ScriptMaker file-operation hook; emission only, no replacement."""
    dry_run=False
    def __init__(self,target):self.target=target;self.data=None
    def write_binary_file(self,filename,data):
        if Path(filename)!=self.target or self.data is not None or not isinstance(data,bytes):
            raise ValueError('Unexpected or repeated installed-generator emission')
        self.data=data

def build():
    if os.name!='nt' or Path(sys.executable)!=E3/'Scripts/python.exe':
        raise RuntimeError('Exact own native E3 Python is required')
    raw=fs.read_bytes(R/'launcher-inventory.json')
    if sha(raw)!=INVENTORY_SHA256:raise RuntimeError('Frozen launcher inventory changed')
    inventory=json.loads(raw)
    claim=json.loads(fs.read_bytes(R/'er1-20261014/claims.json'))['implement']
    if claim['executor_id']!='/root/history_preservation' or Path(claim['workspace'])!=Q:
        raise RuntimeError('Exact ER1 implement claim is required')
    source_rows=inventory['launchers']
    if len(source_rows)!=27 or len({row['filename'] for row in source_rows})!=27:
        raise RuntimeError('Exact27 distinct metadata-bound launchers are required')
    for observation in inventory['installed_script_primitives']:
        if ordinary(Path(observation['path']))!=observation:raise RuntimeError('Installed script-generation primitive changed')
    for row in source_rows:
        current=ordinary(E3/row['relative_path'])
        if any(current[key]!=row[key] for key in ('bytes','sha256','native_identity')):raise RuntimeError('Original launcher changed')
        for observation in row['metadata_files']:
            if ordinary(Path(observation['path']))!=observation:raise RuntimeError('Installed entry-point metadata changed')
    target=Q/'launchers';backup=R/'before-images'
    fs.safe_components(target,allow_missing=True);fs.safe_components(backup,allow_missing=True)
    if target.exists() or backup.exists():raise FileExistsError('Existing candidate or before-image scope is preserved')
    target.mkdir();backup.mkdir()
    from pip._vendor.distlib.scripts import ScriptMaker
    from pip._vendor.distlib.util import get_export_entry
    results=[]
    for row in source_rows:
        name=row['filename'];destination=target/name
        if Path(name).name!=name or not name.endswith('.exe') or name in {'python.exe','pythonw.exe'}:
            raise ValueError('Unsafe candidate filename')
        original=fs.read_bytes(E3/row['relative_path'])
        if sha(original)!=row['sha256']:raise RuntimeError('Original changed before before-image read')
        fs.write_new(backup/name,original)
        emission=CandidateEmission(destination)
        maker=ScriptMaker(None,str(target),add_launchers=True,fileop=emission)
        maker.executable=str(E3/'Scripts/python.exe');maker.variants={''};maker.clobber=False
        specification=row['generation_specification']
        entry=get_export_entry(specification)
        if entry is None or entry.name+'.exe'!=name or entry.prefix+':'+entry.suffix!=row['entry_point_value']:
            raise ValueError('Entry-point identity differs from frozen metadata binding')
        produced=maker.make(specification,{'gui':False})
        if produced!=[str(destination)] or emission.data is None:raise RuntimeError('Unexpected standard-generator outputs')
        data=emission.data;stub=maker._get_launcher('t')
        if data[:len(stub)]!=stub or sha(stub)!=row['stub_sha256']:raise RuntimeError('Native stub identity differs')
        end=data.index(b'\n',len(stub))+1;shebang=data[len(stub):end].decode().strip()
        if shebang!='#!'+str(E3/'Scripts/python.exe') or b'CETA_Intelligence_Operating_System_Build_Package' in data:
            raise RuntimeError('Candidate interpreter identity differs')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.namelist()!=['__main__.py'] or archive.testzip():raise RuntimeError('Malformed generated launcher archive')
            main=archive.read('__main__.py')
        if sha(main)!=row['original_main_script_sha256'] or main.decode()!=row['original_main_script']:
            raise RuntimeError('Existing entry-point script behavior changed')
        fs.write_new(destination,data)
        if fs.read_bytes(destination)!=data or fs.read_bytes(backup/name)!=original:
            raise RuntimeError('Exact staged bytes or before-image differ')
        results.append({'filename':name,'source_relative_path':row['relative_path'],'source_sha256':row['sha256'],'source_native_identity':row['native_identity'],
                        'before_image':reference(backup/name),'candidate':reference(destination),'candidate_bytes':len(data),
                        'candidate_shebang':shebang,'stub_sha256':sha(stub),'main_script_sha256':sha(main),
                        'distribution':row['distribution'],'distribution_version':row['distribution_version'],'entry_point_value':row['entry_point_value'],
                        'binding_kind':row['binding_kind'],'generation_specification':specification,'execution_classification':row['execution_classification']})
    if sorted(path.name for path in target.iterdir())!=sorted(row['filename'] for row in source_rows):
        raise RuntimeError('Unexpected candidate directory member')
    report={'schema_version':1,'generated_at':utc(),'builder':reference(Path(__file__)),'inventory':reference(R/'launcher-inventory.json'),
            'generator':'Current installed pip._vendor.distlib.scripts.ScriptMaker.make via supported file-operation emission sink; native exclusive staged writes',
            'launchers':results,'launcher_count':27,'total_candidate_bytes':sum(row['candidate_bytes'] for row in results),
            'active_E3_application':False,'installed_metadata_or_library_mutation':False,'exit_status':0}
    write_new(R/'candidate-generation.json',report)
    print(json.dumps({'launchers':27,'candidate_bytes':report['total_candidate_bytes'],'report_sha256':sha((R/'candidate-generation.json').read_bytes()),'E3_application':False}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    build()

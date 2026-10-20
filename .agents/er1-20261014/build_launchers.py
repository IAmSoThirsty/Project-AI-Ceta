"""Construct only ER1's exact staged launchers through installed ScriptMaker.

This is a preparation tool. It has no operation that publishes into E3. Existing
source files, installed metadata, interpreter/library bytes and earlier evidence
remain read-only. A standard ScriptMaker file-operation sink collects generated
bytes before exclusive candidate publication, avoiding its in-use replacement
fallback and preserving every pre-existing destination.
"""
from pathlib import Path
import argparse
import base64
import csv
import hashlib
import io
import json
import os
import sys
import zipfile

P=Path(r'T:\00-Active\Project-AI-CETA')
Q=P/'.agents/er1-20261014';R=P/'.agents/runtime/er1-20261014'
E3=P/'.agents/source-assembly-20261014T021300Z/.agents/e3'
INVENTORY_SHA256='1ca08fef1764ee77e504a0988f6c0aecf6f21285d480e46d08f5439fe4863751'
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

def csv_field_spans(line):
    spans=[];start=0;quoted=False;cursor=0
    while cursor<len(line):
        if line[cursor:cursor+1]==b'"':
            if quoted and line[cursor:cursor+2]==b'""':cursor+=2;continue
            quoted=not quoted
        elif line[cursor:cursor+1]==b',' and not quoted:
            spans.append((start,cursor));start=cursor+1
        cursor+=1
    if quoted:raise ValueError('Unclosed installed CSV field')
    spans.append((start,len(line)))
    if len(spans)!=3:raise ValueError('Expected three exact installed RECORD fields')
    return spans

def csv_replacement(original,old,new):
    if list(csv.reader(io.StringIO(original.decode('utf-8')),strict=True))!=[[old]]:
        raise ValueError('Installed CSV field differs from parsed row')
    if original.startswith(b'"') and original.endswith(b'"'):
        return b'"'+new.encode('utf-8')+b'"'
    if original!=old.encode('utf-8'):raise ValueError('Unsupported installed CSV field representation')
    return new.encode('utf-8')

def stage_records(source_rows,results,backup):
    allowed={'pip-25.0.1.dist-info':3,'jsonschema-4.26.0.dist-info':1,'pyside6_essentials-6.11.2.dist-info':23}
    folder=Q/'metadata';before_folder=backup/'metadata'
    if folder.exists() or before_folder.exists():raise FileExistsError('Existing metadata candidates or before images are preserved')
    folder.mkdir();before_folder.mkdir();staged=[]
    candidate_by_name={row['filename']:row for row in results}
    for info_name,expected_count in allowed.items():
        source=E3/'Lib/site-packages'/info_name/'RECORD'
        selected=[row for row in source_rows if Path(row['metadata_directory']).name==info_name]
        if len(selected)!=expected_count:raise ValueError('Exact metadata-to-launcher scope differs')
        expected={row['installed_RECORD_row'][0]:row for row in selected}
        raw=fs.read_bytes(source);source_observation=ordinary(source)
        if sha(raw)!=source_observation['sha256']:raise RuntimeError('Installed RECORD changed during read')
        output=[];changes=[];byte_cursor=0
        for line_number,original_line in enumerate(raw.splitlines(keepends=True),1):
            ending=b'\r\n' if original_line.endswith(b'\r\n') else b'\n' if original_line.endswith(b'\n') else b'\r' if original_line.endswith(b'\r') else b''
            body=original_line[:-len(ending)] if ending else original_line
            parsed=list(csv.reader(io.StringIO(body.decode('utf-8')),strict=True))
            if len(parsed)==1 and parsed[0] and parsed[0][0] in expected:
                old=parsed[0];row=expected[old[0]];candidate=candidate_by_name[row['filename']]
                if old!=row['installed_RECORD_row']:raise RuntimeError('Installed launcher RECORD row changed')
                new_hash='sha256='+base64.urlsafe_b64encode(bytes.fromhex(candidate['candidate']['sha256'])).decode().rstrip('=')
                new_size=str(candidate['candidate_bytes']);spans=csv_field_spans(body)
                h0,h1=spans[1];s0,s1=spans[2]
                new_body=body[:h0]+csv_replacement(body[h0:h1],old[1],new_hash)+body[h1:s0]+csv_replacement(body[s0:s1],old[2],new_size)+body[s1:]
                if list(csv.reader(io.StringIO(new_body.decode()),strict=True))!=[[old[0],new_hash,new_size]]:
                    raise RuntimeError('Generated RECORD row differs')
                output.append(new_body+ending)
                changes.append({'line_number':line_number,'filename':row['filename'],'original_row':old,'candidate_row':[old[0],new_hash,new_size],
                                'original_line_sha256':sha(original_line),'candidate_line_sha256':sha(new_body+ending),'original_line_ending_hex':ending.hex(),
                                'original_byte_spans':{'hash':[byte_cursor+h0,byte_cursor+h1],'size':[byte_cursor+s0,byte_cursor+s1]},
                                'original_field_quoting':[body[h0:h1].startswith(b'"'),body[s0:s1].startswith(b'"')]})
            else:output.append(original_line)
            byte_cursor+=len(original_line)
        if len(changes)!=expected_count or len({row['filename'] for row in changes})!=expected_count:
            raise ValueError('Exact launcher rows were not found uniquely')
        candidate_bytes=b''.join(output);original_rows=list(csv.reader(io.StringIO(raw.decode())));candidate_rows=list(csv.reader(io.StringIO(candidate_bytes.decode())))
        if len(original_rows)!=len(candidate_rows):raise RuntimeError('Installed RECORD membership changed')
        target=folder/info_name/'RECORD';before=before_folder/info_name/'RECORD';target.parent.mkdir();before.parent.mkdir()
        fs.write_new(before,raw);fs.write_new(target,candidate_bytes)
        if fs.read_bytes(before)!=raw or fs.read_bytes(target)!=candidate_bytes:raise RuntimeError('RECORD candidate or before image differs')
        staged.append({'source_relative_path':source.relative_to(E3).as_posix(),'source_observation':source_observation,'before_image':reference(before),
                       'candidate':reference(target),'candidate_bytes':len(candidate_bytes),'row_changes':changes,'changed_rows':len(changes),
                       'other_raw_lines_identical':True,'rows_before_after':len(original_rows),'scope':'Only exact launcher hash/size fields; all other original bytes, quoting, row order and endings retained'})
    return staged

def build():
    if os.name!='nt' or Path(sys.executable)!=E3/'Scripts/python.exe':
        raise RuntimeError('Exact own native E3 Python is required')
    raw=fs.read_bytes(R/'launcher-inventory-r2.json')
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
    records=stage_records(source_rows,results,backup)
    report={'schema_version':1,'generated_at':utc(),'builder':reference(Path(__file__)),'inventory':reference(R/'launcher-inventory-r2.json'),
            'generator':'Current installed pip._vendor.distlib.scripts.ScriptMaker.make via supported file-operation emission sink; native exclusive staged writes',
            'launchers':results,'launcher_count':27,'metadata':records,'metadata_candidates':3,'metadata_row_changes':27,'total_candidate_bytes':sum(row['candidate_bytes'] for row in results),
            'active_E3_application':False,'installed_metadata_or_library_mutation':False,'exit_status':0}
    write_new(R/'candidate-generation.json',report)
    print(json.dumps({'launchers':27,'candidate_bytes':report['total_candidate_bytes'],'report_sha256':sha((R/'candidate-generation.json').read_bytes()),'E3_application':False}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    build()

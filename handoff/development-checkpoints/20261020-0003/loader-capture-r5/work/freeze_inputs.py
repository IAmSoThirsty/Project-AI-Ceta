"""Data-only input inventory; no DLL load, native call, child or symbol fetch."""
from pathlib import Path
import hashlib
import json
import os
import struct
import zipfile

F = Path('T:/00-Active/Project-AI-CETA')
W = Path(__file__).resolve().parent
CODE = ('capture_core.py', 'win32_debug.py', 'isolated_adapter.py', 'loader_snaps.py', 'owned_caller.py','caller_boundary.py')


def pin(path):
    path = Path(path)
    before = path.stat()
    assert path.is_absolute() and path.is_file() and not path.is_symlink() and not path.is_junction()
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1_048_576), b''):
            digest.update(block)
    after = path.stat()
    assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) == (
        after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
    return dict(path=str(path),bytes=before.st_size,sha256=digest.hexdigest(),
                device=before.st_dev,inode=before.st_ino,mtime_ns=before.st_mtime_ns)


def reference(path):
    return dict(repository_relative_path=path.relative_to(F).as_posix(), sha256=pin(path)['sha256'])


def save_new(path, value):
    with path.open('x',encoding='utf8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    python=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
    predecessor=F/'.agents/ac7-loader-capture-20261020'
    successor=json.loads((W.parent/'packet/INPUTS.json').read_bytes())
    prior=Path(successor['predecessor'])
    assert pin(prior/'FROZEN.json')['sha256']==successor['predecessor_freeze_sha256']
    for name,digest in json.loads((prior/'FROZEN.json').read_bytes())['files'].items():assert pin(prior/name)['sha256']==digest
    for evidence in successor['independent_evidence']:
        assert pin(Path(evidence['path']))['sha256']==evidence['sha256']
    prior_inputs=json.loads((prior/'INPUTS.json').read_bytes())
    original=prior_inputs['predecessor']
    r3=Path(prior_inputs['successor']['predecessor'])
    reviews=json.loads((W/'PREDECESSOR-REVIEWS.json').read_bytes())
    assert {row['predecessor'] for row in reviews['reviews']}=={'r3','r4'}
    for row in reviews['reviews']:
        assert row['terminal'] and row['read_full_report'] and row['review_state']=='FAILED'
        for key in ('report','state_reference','claims_reference','submitted_receipt'):
            entry=row[key];path=F/entry['repository_relative_path']
            assert pin(path)['sha256']==entry['sha256']
        state=json.loads((F/row['state_reference']['repository_relative_path']).read_bytes())
        assert state['nodes']['review']['state']=='FAILED' and state['nodes']['review']['reason']==row['actual_reason']
        assert json.loads((F/row['claims_reference']['repository_relative_path']).read_bytes())=={}
    for name,digest in original['predecessor_files'].items():
        assert pin(predecessor/name)['sha256']==digest
        assert pin(W/'originals'/(name+'.before'))['sha256']==digest
    manifest_path=F/'.agents/runtime/ac7-token-contract-20261020/AC7-QUALIFICATION-MANIFEST-R4.json'
    manifest=json.loads(manifest_path.read_bytes())
    candidate=Path(manifest['root'])
    assert candidate==F/'.agents/ac7-token-contract-20261020'
    payloads=manifest['payload_hashes'];assert len(payloads)==357
    for name,digest in payloads.items():
        path=candidate/name
        assert path.resolve().is_relative_to(candidate) and pin(path)['sha256']==digest
    acquisition_path=F/'.agents/runtime/ac7-loader-dependency-20261020/ACQUISITION.json'
    acquisition=json.loads(acquisition_path.read_bytes())
    assert pin(Path(acquisition['archive']))['sha256']==acquisition['archive_sha256']
    names=('build/native/inc/dbghelp.h','content/amd64/dbghelp.dll','content/amd64/dbgcore.dll')
    with zipfile.ZipFile(acquisition['archive']) as archive:
        for name in names:
            row=next(row for row in acquisition['members'] if row['name']==name)
            raw=archive.read(name)
            assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    system=Path(os.environ['SystemRoot'])/'System32'
    libraries={name:pin(system/(name+'.dll')) for name in ('kernel32','kernelbase','ntdll')}
    worker=F/'.agents/runtime/ac7-token-contract-20261020/build-r2/isolated_worker.exe'
    worker_pin=pin(worker)
    assert worker_pin['sha256']=='3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc'
    worker_raw=worker.read_bytes();offset=struct.unpack_from('<I',worker_raw,0x3c)[0]
    assert worker_raw[:2]==b'MZ' and worker_raw[offset:offset+4]==b'PE\x00\x00'
    assert struct.unpack_from('<H',worker_raw,offset+4)[0]==0x8664
    assert struct.unpack_from('<H',worker_raw,offset+24)[0]==0x20b
    caller_paths=dict(helper=(F/'.agents/runtime/ac1-20261014/native_fixture_support.py','a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f'),
        support=(F/'.agents/runtime/ac3-20261014/ac3_support.py','cb44b9f5d4cc50764b486181ad01c41bfee970e91af64338481134c42640096b'),
        driver=(candidate/'tools/qualify_isolated_worker.py','79da07922e6a7f56cca0ae9d90a2498c3d6f28a58dcb6bd3144ab56a87b5bd84'),
        reader=(F/'.agents/pr4-20261014/preserve_ceta_complete.py','2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'))
    caller_contract={}
    for name,(path,digest) in caller_paths.items():
        assert pin(path)['sha256']==digest
        caller_contract[name]=dict(path=str(path),sha256=digest)
    r2=Path(original['rejected_predecessor']['root'])/'work'
    assert pin(r2/'FROZEN.json')['sha256']==original['rejected_predecessor']['freeze_sha256']
    for name,digest in json.loads((r2/'FROZEN.json').read_bytes())['files'].items():assert pin(r2/name)['sha256']==digest
    symbol_root=F/'.agents/runtime/operational-resume-20261020/loader-symbol-inputs-r1/work'
    pdb=pin(symbol_root/'symbols/ntdll.pdb')
    assert pdb['sha256']=='c93f4614aa6f40fe370d40eb7ee9589ca0eda170ef2d704b5d278da71c02c249' and pdb['bytes']==1912832
    from loader_snaps import pe_codeview,pdb_codeview,match_codeview
    image_id=pe_codeview(Path(libraries['ntdll']['path']).read_bytes())
    pdb_id=pdb_codeview(Path(pdb['path']).read_bytes())
    match=match_codeview(image_id,pdb_id)
    assert (match['image_age'],match['info_age'],match['dbi_age'])==(1,4,1)
    value=dict(schema_version=5,repository=str(F),python=pin(python),
        predecessor=original,ac7_candidate=str(candidate),ac7_manifest=reference(manifest_path),
        successor=successor,r4_freeze=reference(prior/'FROZEN.json'),r3_root=str(r3),r3_freeze=reference(r3/'FROZEN.json'),
        independent_default_evidence=[reference(Path(row['path'])) for row in successor['independent_evidence']],
        predecessor_reviews=reference(W/'PREDECESSOR-REVIEWS.json'),
        r2_freeze=reference(r2/'FROZEN.json'),r2_rejection=reference(Path(original['rejected_predecessor']['review_path'])),
        caller_contract=caller_contract,
        worker=worker_pin,worker_machine='AMD64_PE32_PLUS',
        ac7_payload_hashes=payloads,native_system_libraries=libraries,
        canonical_native_libraries={name:pin(system/(name+'.dll')) for name in ('advapi32','userenv','shell32','ole32')},
        debug_dependency_acquisition=reference(acquisition_path),
        debug_dependency_archive=pin(Path(acquisition['archive'])),
        acquired_members_read_as_data=list(names),loader_snaps_inputs=None,
        read_only_symbol_observations=dict(ntdll=libraries['ntdll'],pdb=pdb,
            image_codeview=image_id,pdb_codeview=pdb_id,codeview_match=match,
            historical_blocked_v1=reference(symbol_root/'CETA_OWNED_LOADER_SYMBOL_INPUTS_V1.json')),
        required_symbol_supplement_kind='CETA_OWNED_LOADER_SYMBOL_INPUTS_V2',
        pending=['Root-owned distinct V2 symbol-input derivation, independent review and exact reference',
                 'Acquired x64 DbgHelp/DbgCore byte pins in reviewed V2 supplement',
                 'Separate action-specific owner approval and independent code review',
                 'Fresh canonical fixture, existing profile and in-process exact launch/pipe handle binding'],
        protected_effects_authorized=False,actual_native_qualification=False)
    if (W/'INPUTS.json').exists():
        assert json.loads((W/'INPUTS.json').read_bytes())==value,'INPUTS_CHANGED_REQUIRES_NEW_CUT'
    else:save_new(W/'INPUTS.json',value)
    code_manifest=dict(schema_version=5,run_id='ceta-loader-capture-r5-20261020',author='/root/implement',native_execution=False,
        independent_review='PENDING',code_hashes={name:pin(W/name)['sha256'] for name in CODE})
    code_path=W/'CODE-MANIFEST.json'
    if code_path.exists():
        suffix=hashlib.sha256(json.dumps(code_manifest,sort_keys=True).encode()).hexdigest()[:16]
        code_path=W/('CODE-MANIFEST-'+suffix+'.json')
    save_new(code_path,code_manifest)
    print(json.dumps(dict(input_path=str(W/'INPUTS.json'),payloads_verified=len(payloads),
        input_sha256=pin(W/'INPUTS.json')['sha256'],code_manifest=str(code_path),native_effects=False)))


if __name__=='__main__':
    main()

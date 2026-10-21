"""Read-only C7 exact payload,parent conservation,evidence and checkout audit."""
from pathlib import Path,PurePosixPath
import difflib
import json
import zipfile
from prepare_checkpoint import checkout_state,digest,git,stable_read,verify
W=Path(__file__).resolve().parent
F=Path('T:/00-Active/Project-AI-CETA')
C6=W.parent.parent/'checkpoint-0006/work'
def main():
    prepared=json.loads((W/'prepared-0001/PREPARED.json').read_bytes())
    manifest=json.loads((W/'SOURCE-MANIFEST.json').read_bytes())
    previous=json.loads((C6/'SOURCE-MANIFEST.json').read_bytes())
    before=json.loads((W/'CANONICAL-BEFORE.json').read_bytes())
    generic=verify(W/'prepared-0001/PREPARED.json')
    env=prepared['git_environment']
    def tree(commit):
        result={}
        for row in git(F,['ls-tree','-r','-z',commit],env=env).split(b'\0'):
            if row:
                header,name=row.split(b'\t',1);result[name.decode()]=tuple(header.decode().split())
        return result
    parent=tree(prepared['parent']);child=tree(prepared['commit'])
    expected={'tools/ceta_operator.py','src/ceta/application/operator.py','src/ceta/composition/owned_service.py',
        'DEVELOPMENT-CHECKPOINT.json','DEVELOPMENT-CHECKPOINT.md'}
    modified={p for p in parent if parent[p]!=child.get(p)}
    assert modified==expected,modified
    assert not set(parent)-set(child)
    assert all(parent[p]==child[p] for p in parent if p not in expected)
    assert all(parent[p][0]==child[p][0] for p in parent)
    prior_prepared=json.loads((C6/'prepared-0001/PREPARED.json').read_bytes())
    assert prepared['parent']==prior_prepared['commit']=='3ab94d8c11e3169eee85c9fbb3f53fd7c234871a'
    assert set(prior_prepared['exports'])<=set(child)
    status=json.loads((W/'public/STATUS.json').read_bytes())
    fixtures=status['preserved_registry_fixtures'];assert len(fixtures)==5
    assert all(parent[p]==child[p] for p in fixtures)
    pdf=sorted(p for p in parent if 'pdf' in p.casefold());assert pdf
    assert all(parent[p]==child[p] for p in pdf)
    assert manifest['payload_count']==len(manifest['payload_hashes'])==559
    assert digest(Path(manifest['derived_from']).read_bytes())==manifest['derived_manifest_sha256']=='d525e5091051af9f260c60d59ba1a0ff7c55dd48516953c9f7960922a2259c78'
    effective=json.loads(Path(manifest['derived_from']).read_bytes())
    assert effective['payload_hashes']==manifest['payload_hashes']
    for key in ('accepted_j_manifest','accepted_j_handoff'):
        assert digest(Path(manifest[key]).read_bytes())==manifest[key+'_sha256']
    rows=[]
    for rel,pin in manifest['payload_hashes'].items():
        raw,_=stable_read(Path(manifest['candidate'])/rel);assert digest(raw)==pin
        if rel.endswith('.py'):compile(raw,rel,'exec')
        if previous['payload_hashes'].get(rel)!=pin:
            a=(Path(previous['candidate'])/rel).read_text().splitlines() if rel in previous['payload_hashes'] else []
            b=raw.decode().splitlines();ops=difflib.SequenceMatcher(a=a,b=b).get_opcodes()
            rows.append(dict(path=rel,added=sum(l-k for op,i,j,k,l in ops if op in ('insert','replace')),
                removed=sum(j-i for op,i,j,k,l in ops if op in ('delete','replace'))))
    loc=json.loads((W/'PRODUCT-LOC.json').read_bytes());assert rows==loc['paths']
    assert loc['source']==dict(added=325,removed=10) and loc['tests']==dict(added=618,removed=0)
    assert loc['docs']==dict(added=46,removed=0) and loc['copied_loc']==0
    eof='tests/contract/test_native_owner_execution.py'
    assert manifest['payload_hashes'][eof]==previous['payload_hashes'][eof]=='47ee148ce2ae0646c11e1f8b919b5f9dca68662931d9a554d523bb535d025613'
    for rel in ('src/ceta/resource/hardware.py','src/ceta/resource/diagnostics.py'):
        assert manifest['payload_hashes'][rel]==previous['payload_hashes'][rel]
    transport=json.loads((W/'public/EVIDENCE-TRANSPORT.json').read_bytes());archive=W/'public/RAW-EVIDENCE.zip'
    assert digest(archive.read_bytes())==transport['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert z.namelist()==[x['member'] for x in transport['members']]
        for item,info in zip(transport['members'],z.infolist(),strict=True):
            name=info.filename
            assert '..' not in PurePosixPath(name).parts and not name.startswith('/') and ':' not in name and '\\' not in name
            assert info.compress_type==zipfile.ZIP_STORED and info.date_time==(1980,1,1,0,0,0)
            raw,_=stable_read(item['source']);assert digest(raw)==item['sha256'] and len(raw)==item['bytes']
            assert z.read(name)==raw
        assert len(z.namelist())==387
        for prefix in ('sol-owned-diagnostics-r1/','sol-operator-diagnostics-r1/','operator-diagnostics-integration-r1/work/joined-tests/',
            'operator-diagnostics-integration-r1/work/joined-tests-r2/','operator-diagnostics-integration-r1/work/live-cli-01/','checkpoint-0006/control/'):
            assert any(name.startswith(prefix) for name in z.namelist()),prefix
    for path in (W/'public/RAW-EVIDENCE-SECRET-SCAN.json',W/'prepared-0001/EXACT-EXPORT-SECRET-SCAN.json'):
        scan=json.loads(path.read_bytes());assert not scan['findings'] and scan['result']=='PASS'
    pins=json.loads((W/'TOOL-COPY-PINS.json').read_bytes())
    for name,pin in pins.items():
        assert digest((W/name).read_bytes())==pin==digest((C6/name).read_bytes())
    assert all(Path(v).is_relative_to(W) for k,v in env.items() if k!='GIT_ALTERNATE_OBJECT_DIRECTORIES')
    assert git(F,['cat-file','--batch-check'],data=(prepared['commit']+'\n').encode()).strip()==(prepared['commit']+' missing').encode()
    after=dict(checkout=checkout_state(F),normal_index_native=stable_read(F/'.git/index')[1],
        canonical_product_pins={rel:stable_read(F/rel)[1] for rel in manifest['payload_hashes']},
        refs=git(F,['for-each-ref','--format=%(refname) %(objectname)']).decode().splitlines())
    assert after==before,'canonical bytes/native index/HEAD/dirty state/refs drift'
    if (W/'WORK-FREEZE.json').exists():
        frozen=json.loads((W/'WORK-FREEZE.json').read_bytes())
        actual={p.relative_to(W).as_posix():digest(stable_read(p)[0]) for p in W.rglob('*') if p.is_file() and p.relative_to(W).as_posix()!='WORK-FREEZE.json'}
        assert actual==frozen['hashes'],'frozen work drift'
    print(json.dumps(dict(status='PASS',commit=prepared['commit'],tree=prepared['tree'],parent=prepared['parent'],
        parent_paths=len(parent),child_paths=len(child),changed_existing_paths=sorted(modified),new_paths=sorted(set(child)-set(parent)),
        parent_modes_preserved=True,pdf_paths=pdf,five_fixtures=fixtures,exact_source_payloads=559,
        source_delta=loc['source'],tests_delta=loc['tests'],docs_delta=loc['docs'],copied_loc=0,
        prior_eof_repair_preserved=True,raw_evidence_members=387,entire_export_and_raw_secret_scans='PASS',
        normal_dirty_checkout_native_index_and_refs_preserved=True,generic_verification=generic,
        publication=False,fresh_native_execution=False,full_product_acceptance=False),indent=2))
if __name__=='__main__':main()

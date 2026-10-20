from en1_support import *

response=invoke(['run','status',RUN],'author-final-status')
assert response['states']['implement']=='SUCCEEDED' and response['states']['review']=='READY'
assert response['sequence']==7
claims=json.loads((R/RUN/'claims.json').read_text());assert claims=={}
submitted=json.loads((R/'implement.json').read_text())
persisted_path=R/RUN/'receipts/implement.json';persisted=json.loads(persisted_path.read_text())
assert len(submitted)==12 and len(persisted)==15
assert {key:persisted[key] for key in submitted}==submitted
assert response['nodes']['implement']['receipt_hash']==persisted['receipt_hash']
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text())
assert sha(Q/'TRANSFER-MANIFEST.json')==submitted['result']['manifest_sha256']
assert len(manifest['payloads'])==295
write_new(R/'AUTHOR-READBACK.json',{'recorded_at':utc(),'run_id':RUN,'candidate':str(Q),
    'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'sequence':7,'states':response['states'],'claims':claims,
    'submitted':reference(R/'implement.json'),'persisted':reference(persisted_path),
    'authored_fields':12,'persisted_fields':15,'strict_authored_equality':True,
    'actual_status':reference(R/'author-final-status.json'),'author_released':True,'review_ready':True,
    'source_published':False,'independent_review':False})
def inventory(root,skip):
    found={};pending=[root]
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path=directory/entry.name;name=path.relative_to(root).as_posix()
                if skip(name):continue
                info=fs.lstat(path);assert not fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):pending.append(path)
                elif stat.S_ISREG(info.st_mode):found[name]=ordinary(path)
                else:raise AssertionError('Nonordinary EN1 author output')
    return dict(sorted(found.items()))
candidate=inventory(Q,lambda _:False)
assert len(candidate)==296
assert all(candidate[row['relative_path']]['sha256']==row['candidate_sha256']
    and candidate[row['relative_path']]['native_identity']==row['candidate_native_identity'] for row in manifest['payloads'])
assert set(candidate)=={row['relative_path'] for row in manifest['payloads']}|{'TRANSFER-MANIFEST.json'}
prefix=Q.relative_to(Path('T:/')).as_posix()+'/'
assert all(name.startswith(prefix) for name in submitted['changed_files'])
assert {name.removeprefix(prefix) for name in submitted['changed_files']}==set(candidate)
def skip(name):
    return (name==RUN or name.startswith(RUN+'/') or name=='AUTHOR-SEAL.json'
            or any(part in ('independent-review','independent-root-review','root-integration') for part in Path(name).parts))
evidence=inventory(R,skip)
seal={'sealed_at':utc(),'author':ACTOR,'run_id':RUN,'candidate_root':str(Q),
    'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'readback':reference(R/'AUTHOR-READBACK.json'),
    'candidate_members':candidate,'author_evidence_members':evidence,
    'excluded':['Mutable installed lifecycle run directory','Later distinct-review/root-integration scopes','This self-referential seal'],
    'author_released':True,'source_published':False,'independent_review':False}
write_new(R/'AUTHOR-SEAL.json',seal)
print(json.dumps({'manifest':seal['manifest'],'implement':reference(R/'implement.json'),
    'readback':seal['readback'],'seal':reference(R/'AUTHOR-SEAL.json'),
    'sequence':7,'states':response['states'],'claims':claims,
    'candidate_members':len(candidate),'evidence_members':len(evidence)},indent=2))

"""Read actual completed author state and seal exact immutable author outputs."""
from pathlib import Path
import json,os,stat,sys
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cpb1-20261014';R=P/'.agents/runtime/cpb1-20261014';RUN='cpb1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN=RUN
status=s.invoke(['run','status',RUN],'author-final-status-r2')
claims=json.loads((R/RUN/'claims.json').read_text())
submitted=json.loads((R/'implement.json').read_text());persisted_path=R/RUN/'receipts/implement.json'
persisted=json.loads(persisted_path.read_text());manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text())
assert status['states']['implement']=='SUCCEEDED' and status['states']['review']=='READY' and status['sequence']==7
assert claims=={} and len(submitted)==12 and len(persisted)==15
assert all(persisted[key]==value for key,value in submitted.items())
assert status['nodes']['implement']['receipt_hash']==persisted['receipt_hash']
assert s.sha(Q/'TRANSFER-MANIFEST.json')==submitted['result']['manifest_sha256']
assert len(manifest['payloads'])==303
s.write_new(R/'AUTHOR-READBACK-r2.json',dict(recorded_at=s.utc(),run_id=RUN,manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),
    submitted=s.reference(R/'implement.json'),persisted=s.reference(persisted_path),states=status['states'],sequence=7,
    claims=claims,authored_fields=12,persisted_fields=15,strict_authored_field_equality=True,
    actual_status=s.reference(R/'author-final-status.json'),author_released=True,review_ready=True,
    Source_publication=False,independent_review=False))
def inventory(root,skip):
    rows={};pending=[root]
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path=directory/entry.name;relative=path.relative_to(root).as_posix()
                if skip(relative):continue
                info=s.fs.lstat(path);assert not s.fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):pending.append(path)
                elif stat.S_ISREG(info.st_mode):rows[relative]=s.ordinary(path)
                else:raise AssertionError('Nonordinary author output')
    return dict(sorted(rows.items()))
candidate=inventory(Q,lambda _:False)
assert all(candidate[name]==row for name,row in manifest['payloads'].items())
fixture_names=set(candidate)-set(manifest['payloads'])-{'TRANSFER-MANIFEST.json'}
assert all(name.startswith('.agents/fixtures/windows-jobs-') for name in fixture_names)
prefix=Q.relative_to(Path('T:/')).as_posix()+'/'
assert all(name.startswith(prefix) for name in submitted['changed_files'])
assert {name.removeprefix(prefix) for name in submitted['changed_files']}==set(candidate)-fixture_names
def skip(name):
    return (name==RUN or name.startswith(RUN+'/') or name=='AUTHOR-SEAL.json'
        or any(part in ('independent-review','independent-root-review','root-integration') for part in Path(name).parts))
evidence=inventory(R,skip)
s.write_new(R/'AUTHOR-SEAL.json',dict(recorded_at=s.utc(),author=s.ACTOR,manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),
    readback=s.reference(R/'AUTHOR-READBACK-r2.json'),candidate_members=candidate,author_evidence_members=evidence,
    payload_count=303,fixture_evidence_members=sorted(fixture_names),author_released=True,
    excluded=['Mutable installed run ledger','Future independent-review/root-integration scopes','This self-referential seal'],
    Source_publication=False,independent_review=False))
print(json.dumps(dict(manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),implement=s.reference(R/'implement.json'),
    readback=s.reference(R/'AUTHOR-READBACK-r2.json'),seal=s.reference(R/'AUTHOR-SEAL.json'),
    state=status['states'],sequence=7,claims=claims,candidate_members=len(candidate),fixture_evidence_members=len(fixture_names))),flush=True)

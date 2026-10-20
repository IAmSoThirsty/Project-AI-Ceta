"""Read-only exact negative-fixture provenance and R3 input-inventory comparison."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,stat
F=Path('T:/00-Active/Project-AI-CETA');D=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
N=F/'.agents/runtime/ob2-20261014/negative-reuse';O=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(repository_relative_path=p.relative_to(F).as_posix(),sha256=sha(p))
packet=json.loads((D/'PACKET.json').read_bytes());reuse=json.loads((N/'REUSE.json').read_bytes())
bref=reuse['original_build'];bp=F/bref['repository_relative_path'];assert sha(bp)==bref['sha256'];build=json.loads(bp.read_bytes())
source=Path(build['source']['path']);assert sha(source)==build['source']['sha256']
before=json.loads((D/'SOURCE-BEFORE.json').read_bytes())
manifest=json.loads((D/'MANIFEST-Q5.json').read_bytes())
environment=json.loads((D/'ENVIRONMENT.json').read_bytes())
rows=[]
for name in ('overlong.exe','rights.exe','silent.exe'):
    path=N/name;actual=sha(path);facts=path.lstat();expected=reuse['images'][name]
    ordinary=dict(path=str(path),bytes=facts.st_size,sha256=actual,native_identity=dict(bytes=facts.st_size,mtime_ns=facts.st_mtime_ns,mode=stat.S_IMODE(facts.st_mode),device=facts.st_dev,inode=facts.st_ino,attributes=facts.st_file_attributes))
    assert ordinary==expected and actual==build['images'][name]['sha256']
    rows.append(dict(path=str(path),actual=ordinary,recorded_reuse=expected,
        in_packet_fixture_dependencies=any(row['path']==str(path) for row in packet['fixture_dependencies'].values()),
        in_Source_before=path.relative_to(F).as_posix() in before['targets'],
        in_Q5_payloads=path.relative_to(F).as_posix() in manifest['payload_hashes'],
        in_E3_environment=any(row['path']==str(path) for row in environment['environment_files'].values())))
assert not any(any(row[k] for k in ('in_packet_fixture_dependencies','in_Source_before','in_Q5_payloads','in_E3_environment')) for row in rows)
record=dict(at=datetime.now(timezone.utc).isoformat(),finding_id='JS9-CANDIDATE-02',
    classification='blocking current full acceptance until an exact successor input cut is reviewed',
    packet=ref(D/'PACKET.json'),reuse=ref(N/'REUSE.json'),original_build=bref,negative_source=ref(source),images=rows,
    verified='All three currently match their retained same-project reuse/build digests and native identities, but none is in R3 fixture dependencies, Source-before, Q5 payloads or E3 environment pins.',
    source_locations=['fixture_runtime.py:136 supplies negative-reuse root',
        'test_native_effect_observer.py:390-397 computes each current image hash and calls it a controlled negative image',
        'js9_support.py:125 post-verifies only packet fixture_dependencies',
        'negative_helpers.rs:14-18 selects behavior using current_exe file stem; all three image byte hashes are intentionally equal'],
    required_small_correction='Add exact path/role/hash/native facts for the three images and pinned reuse/build/source provenance to the next reviewed fixture input cut; verify them before and after execution. Preserve R3 unchanged.',
    causal_status='No causal link from this inventory gap to the timeout is established. Current bytes match recorded historical inputs; terminal recorded-launch/receipt digests must be compared separately.',
    no_native_execution=True,no_tool_or_source_changes=True,no_retry_approval=True)
with (O/'NEGATIVE-INPUT-INVENTORY.json').open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(dict(evidence=ref(O/'NEGATIVE-INPUT-INVENTORY.json'),finding=record['finding_id'],images=len(rows))))

"""One complete F observation and exact conservation, with failures retained."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
import directory_snapshot as d,conservation
W=Path(__file__).resolve().parent
def save(name,value):
    with (W/name).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
before=conservation.observe();started=time.perf_counter_ns();snapshot=primary=None;after=None
try:snapshot=d.snapshot(d.F,d.F)
except BaseException as error:primary=sys.exc_info()
try:after=conservation.observe()
except BaseException:
    if primary is None:primary=sys.exc_info()
    else:
        storage=BaseException.__dict__['__dict__'].__get__(primary[1])
        dict.__setitem__(storage,'full_F_conservation_secondary_exc_info',sys.exc_info())
report=dict(schema_version=1,run_id='ceta-ds23-r2',recorded_at=datetime.now(timezone.utc).isoformat(),
    provider_sha256=sha(Path(d.__file__)),access_policy_sha256=d.POLICY_SHA,
    elapsed_ns=time.perf_counter_ns()-started,qualified=primary is None and snapshot is not None,
    canonical_count=before['canonical_count'],canonical_Git_ST2_and_original_evidence_conserved=after==before,
    full_product_acceptance=False,native_workers=False,canonical_or_Git_or_ST2_mutation=False,
    original_two_failed_claims_cause='UNKNOWN; existing failed receipts remain failed',
    legacy_file_native_hash_function_used_unmodified=d.LEGACY_SHA,
    snapshot_projection_compatible='files/directories/excluded_symlinks/file_map retained; separate raw directory provenance',
    sampled_tree_limit='Stable sampled metadata/names/content; not an atomic filesystem, ACL or alternate-stream snapshot')
if snapshot is not None:
    save('FULL-F-SNAPSHOT.json',snapshot)
    report.update(files=len(snapshot['files']),directories=len(snapshot['directories']),
        excluded_symlinks=len(snapshot['excluded_symlinks']),raw_directory_provenance=len(snapshot['directory_observations']),
        snapshot_sha256=sha(W/'FULL-F-SNAPSHOT.json'),file_map_sha256=hashlib.sha256(json.dumps(d.file_map(snapshot),sort_keys=True,separators=(',',':')).encode()).hexdigest())
    assert set(next(iter(snapshot['files'].values())))=={'device','inode','bytes','mtime_ns','mode','attributes','sha256'}
if after is not None:save('CONSERVATION-AFTER.json',after)
if primary is not None:
    storage=BaseException.__dict__['__dict__'].__get__(primary[1]);observation=dict.get(storage,'directory_snapshot_observation')
    report['failure']=dict(type=primary[0].__name__,args=repr(BaseException.__dict__['args'].__get__(primary[1])),
        directory=None if observation is None else str(observation.path),
        raw_provenance=None if observation is None else observation.provenance(),
        secondary_types=[info[0].__name__ for info in dict.get(storage,'directory_snapshot_secondary_exc_info',())])
save('FULL-F-QUALIFICATION.json',report)
print(json.dumps({k:v for k,v in report.items() if k!='failure'},indent=2))
if primary is not None:
    print(json.dumps(report['failure'],indent=2));raise BaseException.with_traceback(primary[1],primary[2])
assert report['qualified'] and report['canonical_Git_ST2_and_original_evidence_conserved']

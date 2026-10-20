from en1_support import *

eligible=['src/ceta/contracts/owner_enrollment.py','tests/contract/test_owner_enrollment.py',
          'contracts/OWNER_ENROLLMENT_V1.md']
dependencies={
    'src/ceta/contracts/real_effect.py':('.agents/rc2-20261014/src/ceta/contracts/real_effect.py','72a4d9769b162eec871a78abf772feadd12c7293f5f33e5f60d78cd751af00e3'),
    'src/ceta/contracts/workload_throttling.py':('.agents/wt3-20261014/src/ceta/contracts/workload_throttling.py','910baa28c3bbf5ba1870e80dc7a46684e6fc777b532ba61727582689181ef25b')}
plan=P/'.agents/runtime/real-effect-20261014/plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'
assert sha(plan)=='d99cbc87dd5430b6287b3a77759fd75b8cdb0276a372c9a4cca8ba1bc047119c'
assert all(not (P/name).exists() for name in eligible)
invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN],'run-init')
claim('discover')
accepted=P/'.agents/runtime/perf1-20261014/active-application/destination-full-r1.json'
pins=json.loads(accepted.read_text())['after_hashes']
source={name:ordinary(P/name) for name in pins}
assert len(source)==290 and all(row['sha256']==pins[name] for name,row in source.items())
dependency_records={}
for name,(origin,pin) in dependencies.items():
    assert name not in source and sha(P/origin)==pin
    dependency_records[name]={'source':ordinary(P/origin),'new_LOC_credit':0,
        'state':'UN­CREDITED_TYPED_DEPENDENCY_NO_ACCEPTANCE_BORROWED'}
write_new(R/'SOURCE-INPUTS.json',{'recorded_at':utc(),'source_root':str(P),'current290':source,
    'HEAD':fs.text_git(P,'rev-parse','HEAD'),'branch':fs.text_git(P,'branch','--show-current'),
    'tracked_status':fs.text_git(P,'status','--porcelain=v1','-uno'),'interpreter':ordinary(PY),
    'accepted_source':reference(accepted),'real_effect_plan':reference(plan),'dependencies':dependency_records})
command=subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(Path(__file__))])
complete('discover',{'source_inputs':reference(R/'SOURCE-INPUTS.json'),'source_count':290},
    [{'command':command,'exit_status':0}],[('Source290 and exact two explicitly authorized typed dependencies bound',True)])
claim('plan')
write_new(R/'TASK-BINDING.json',{'recorded_at':utc(),'job':RUN,'writer':ACTOR,'coordinator':'/root',
    'role':'R02 immutable DATA contract implementation, R18/R19/R20 author qualification',
    'objective':'RE-T04/T05/T06 owner-enrollment DATA_ONLY request/display/currentness/transcript binding',
    'candidate':str(Q),'runtime':str(R),'eligible_paths':eligible,
    'accepted_design':'Single volume-GUID path spelling, native object identities, full immutable expected equality and temporal guards; fixed one-worker cap/restore profile',
    'proof':'Deterministic codec/identity/budget/display/domain/currentness/concurrency regressions plus retained wire/schema/temporal cases',
    'allowed_reads':['Current Source/specs/r6/templates','Exact two typed dependency sources','Declared installed P4/TAAR and own E3 read-only'],
    'allowed_writes':[str(Q),str(R)],'effects':'Pure data construction/decoding/validation and own runtime receipts only',
    'excluded':['Source/E3/prior-cut changes','Native Hello/profile/filesystem probes','Enrollment grant/epoch/store/issuer mutation','Caller data as authenticated authority'],
    'dependency_state':'Typed bytes only, explicitly uncredited; accepted integration must later reconcile separately reviewed dependency cuts',
    'independent_review':'Root after author implement release','source_publication':False})
complete('plan',{'task_binding':reference(R/'TASK-BINDING.json'),'eligible_paths':eligible},
    [{'command':command,'exit_status':0}],[('Finite approved DATA contract API; no authority issuance or new planning framework',True)])
owned=claim('implement');assert owned['baseline_snapshot']=={}
for name,row in sorted(source.items()):
    raw=fs.read_bytes(P/name);assert digest(raw)==row['sha256']
    target=Q/name;target.parent.mkdir(parents=True,exist_ok=True);fs.write_new(target,raw)
for name,record in dependency_records.items():
    raw=fs.read_bytes(record['source']['path']);assert digest(raw)==record['source']['sha256']
    fs.write_new(Q/name,raw)
write_new(R/'IMPLEMENTATION-STARTED.json',{'recorded_at':utc(),'claim':owned,'source_count':290,
    'dependencies':dependency_records,'reused_product_test_LOC_credit':0,'source_published':False})
print(json.dumps({'implement_claimed':True,'source290':290,'uncredited_dependencies':2},indent=2))

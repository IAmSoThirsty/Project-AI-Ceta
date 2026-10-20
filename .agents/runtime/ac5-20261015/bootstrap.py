"""Fresh author claim and exact immutable AC4 payload staging."""
from ac_support import *
assert not Q.exists();Q.mkdir()
parent=F/'.agents/ac4-20261015';manifest_path=parent/'TRANSFER-MANIFEST.json'
assert sha(manifest_path)=='edfdd84ab33dc4ac9ee8f07a3205d4119a5bf496339d40dafc16d5f47576d1f1'
manifest=json.loads(manifest_path.read_text());assert len(manifest['payloads'])==295
review=F/'.agents/runtime/ac4-20261015/independent-review/review.json'
assert sha(review)=='fba44360d5178022cad9056cdcea1e10a615734da0cfcc0615f9bc02d61957e5'
assert json.loads(review.read_text())['decision']=='rejected'
source_old=json.loads((F/'.agents/runtime/ac4-20261015/SOURCE-INPUTS.json').read_text())['Source290']
source={name:ordinary(F/name) for name in source_old};assert source==source_old
scope=manifest['author_scope']
invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN],'run-init')
claim('discover')
write_new(R/'SOURCE-INPUTS.json',{'at':utc(),'Source290':source,'parent_manifest':reference(manifest_path),
    'parent_rejected_review':reference(review),'eligible_author_paths':scope,
    'eligible_application_paths':manifest['eligible_application_paths'],
    'exact_hostile_probe':reference(F/'.agents/runtime/ac4-20261015/independent-review/probe_combined_custody.py'),
    'HEAD':fs.text_git(F,'rev-parse','HEAD'),'dirty_tracked':fs.text_git(F,'status','--porcelain=v1','-uno')})
cmd={'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(Path(__file__))]),'exit_status':0}
complete('discover',{'inputs':reference(R/'SOURCE-INPUTS.json')},[cmd],[('Exact AC4 failure, Source290 and parent295 inspected',True)])
claim('plan')
write_new(R/'TASK-BINDING.json',{'at':utc(),'scope':scope,
    'repair':'Only _attach_cleanup canonical BaseException custody despite hooks; original primary/diagnostic/qualification/native launch behavior retained.',
    'verification':'Literal native2 baseline and closure; original22IDs; extra native/control/nested recovery through exposed cleanup; no profile/worker/Source/environment changes.'})
complete('plan',{'binding':reference(R/'TASK-BINDING.json')},[cmd],[('Bounded custody-only repair with unchanged predicates and original tests',True)])
claim('implement');rows={}
for name,row in manifest['payloads'].items():
    assert ordinary(parent/name)==row
    target=Q/name;target.parent.mkdir(parents=True,exist_ok=True);fs.write_new(target,fs.read_bytes(parent/name));rows[name]=ordinary(target)
for name in scope:
    target=R/'before-images'/name;target.parent.mkdir(parents=True,exist_ok=True);fs.write_new(target,fs.read_bytes(parent/name))
write_new(R/'STAGED-INPUTS.json',{'at':utc(),'payloads':rows,'parent_manifest':reference(manifest_path),
    'eligible_author_paths':scope,'reuse_LOC_credit':0})
print(json.dumps({'implement':'RUNNING','executor':ACTOR,'payloads':len(rows),'Source':290}))

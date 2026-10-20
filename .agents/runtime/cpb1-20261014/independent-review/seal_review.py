"""Seal only this completed reviewer scope; no product or fixture changes."""
from pathlib import Path
import json,os,stat,sys
D=Path(__file__).resolve().parent;R=D.parent;F=R.parents[2];Q=F/'.agents/cpb1-20261014'
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=D
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
prep=read(D/'PREPARATION.json');final=read(D/'FINAL-CONSERVATION.json');proof=read(D/'ACTUAL-REVIEW-READBACK.json')
life=R/'cpb1-20261014';state=read(life/'state.json');claims=read(life/'claims.json')
assert state==proof['state'] and claims=={} and state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED'
assert proof['local_review']==s.ordinary(D/'review.json') and proof['persisted_review']==s.ordinary(life/'receipts/review.json')
assert all(s.ordinary(Q/n)==row for n,row in prep['candidate326'].items())
assert all(s.ordinary(F/n)==row for n,row in prep['Source290'].items())
assert all(s.ordinary(R/n)==row for n,row in prep['author_evidence'].items())
assert read(D/'REPORT.json')['decision']=='approved' and read(D/'REPORT.json')['confirmed_new_defects']==[]
files={};dirs={};pending=[D]
while pending:
    current=pending.pop()
    with os.scandir(current) as entries:
        for entry in entries:
            path=current/entry.name;name=path.relative_to(D).as_posix();info=s.fs.lstat(path);assert not s.fs.reparse(info)
            if stat.S_ISDIR(info.st_mode):dirs[name]=s.fs.file_identity(info);pending.append(path)
            else:assert stat.S_ISREG(info.st_mode);files[name]=s.ordinary(path)
assert 'REVIEW-SEAL.json' not in files
s.write_new(D/'REVIEW-SEAL.json',dict(at=s.utc(),reviewer='/root/wt1_reviewer',manifest=s.ordinary(Q/'TRANSFER-MANIFEST.json'),review=s.ordinary(D/'review.json'),report=s.ordinary(D/'REPORT.json'),
    actual_readback=s.ordinary(D/'ACTUAL-REVIEW-READBACK.json'),review_state='SUCCEEDED',sequence=9,claims={},reviewer_released=True,
    members=dict(sorted(files.items())),directories=dict(sorted(dirs.items())),ordinary_files=len(files),ordinary_bytes=sum(row['bytes'] for row in files.values()),
    scope='Only this independent-review directory; self excluded. Actual installed mutable lifecycle lives outside this seal.',
    conservation='All303 payloads+manifest+22 preexisting fixture files, all preexisting candidate directories, Source290, author-sealed evidence and E33601 exact at final reviewed cut.',
    native_execution='163 exact connected methods plus1 unchanged literal probe;8 fresh medium worker lifetimes and13 actual clock owners closed;0 class15 writes;8 class9 containment setups only.',
    historical_failures_preserved=True,Source_application=False,CPU_effect=False,whole_product_completion=False))
print(json.dumps(dict(review=s.reference(D/'review.json'),report=s.reference(D/'REPORT.json'),readback=s.reference(D/'ACTUAL-REVIEW-READBACK.json'),seal=s.reference(D/'REVIEW-SEAL.json'),members=len(files),bytes=sum(row['bytes'] for row in files.values()),state='SUCCEEDED',sequence=9,claims={}),sort_keys=True),flush=True)

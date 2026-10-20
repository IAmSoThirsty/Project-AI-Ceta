"""Root's separate frozen-code review; no original native test authorization."""
from pathlib import Path
import json,sys
F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/f4-full-gate-successor-20261015'
Q=R/'candidate';D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN=R.name;s.ACTOR='/root'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
assert read(R/R.name/'claims.json')['review']['executor_id']=='/root'
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='043a722debd79ae1abd7d95414873f8893a326409ad6b2337e866eeaa9f438fe'
assert s.sha(R/'AUTHOR-SEAL.json')=='45e990dbfb74f7264277f70c7f7bc62aaea9c86efa315e0a77139bbfc2bcfbba'
seal=read(R/'AUTHOR-SEAL.json')
assert len(seal['candidate_members'])==6 and len(seal['author_evidence_members'])==154
for name,row in seal['candidate_members'].items():assert s.ordinary(Q/name)==row
for name,row in seal['author_evidence_members'].items():assert s.ordinary(R/name)==row
raw=(R/'run_tests.py').read_bytes()
assert s.digest(raw)=='b8241ea22444a699b1a8404dc24fdf855434d55007da4c8495eb594ffbef61c2'
text=raw.decode('utf-8')
old="R=Path(__file__).resolve().parent;Q=R/'candidate'"
assert text.count(old)==1
text=text.replace(old,"R=F/'.agents/runtime/f4-full-gate-successor-20261015';Q=R/'candidate'")
old='out=R/label;out.mkdir(exist_ok=False)';assert text.count(old)==1
text=text.replace(old,'out=Path(__file__).resolve().parent/label;out.mkdir(exist_ok=False)')
text=text.replace("s.ACTOR='/root/history_preservation'","s.ACTOR='/root'")
text=text.replace('import test_full_gate as tests','import test_full_gate as tests\ntests.R=Path(__file__).resolve().parent')
with (D/'run_tests.py').open('x',encoding='utf-8',newline='\n') as out:out.write(text)
s.write_new(D/'PREPARATION.json',{'at':s.utc(),'reviewer':'/root','manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),
 'author_seal':s.reference(R/'AUTHOR-SEAL.json'),'candidate6_and_evidence154_current_exact':True,
 'original_driver':s.reference(R/'run_tests.py'),'review_driver':s.reference(D/'run_tests.py'),
 'adaptation':'Only distinct evidence and synthetic fixture roots plus honest reviewer identity; oracle bodies and frozen successor code unchanged.',
 'authorization_created':False,'original_restricted_case':'NOT_RUN','Source_publication':False})
print(json.dumps({'candidate':6,'evidence':154,'prepared':s.reference(D/'PREPARATION.json')}))

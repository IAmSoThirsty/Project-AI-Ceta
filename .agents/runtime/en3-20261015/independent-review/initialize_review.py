"""Fresh independent EN3 review transport, reused from exact ET3 support."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');D=Path(__file__).resolve().parent
assert D==F/'.agents/runtime/en3-20261015/independent-review'
sys.dont_write_bytecode=True
source=F/'.agents/runtime/et3-20261015/independent-review/review_support.py'
text=source.read_text()
text=text.replace("Q = F / '.agents/et3-20261015'","Q = F / '.agents/en3-20261015'")
text=text.replace("R = F / '.agents/runtime/et3-20261015'","R = F / '.agents/runtime/en3-20261015'")
text=text.replace("RUN, ACTOR = 'et3-20261015'","RUN, ACTOR = 'en3-20261015'")
text=text.replace("'b061311cf6f52c89b9af93845258ca061043ef6ef60d8530b9048983351e5c9a'","'8772cd735ae0ff767108976fef15e004012718ffded50a1d888cc354fae329ec'")
text=text.replace('Distinct review of ET3 fresh observer child reconciliation and retained finite accounting','Distinct review of EN3 canonical GUID parser and unchanged pure contract leaf boundary')
text=text.replace('Reviewer authored KA1 dependency; rely on Root accepted KA1 review, independently assess ET3 delta.','Root authored EN3 successor. Reviewer authored original EN1 and independently approved EN2; rely on Root separate original component review and assess exact EN3 delta.')
target=D/'review_support.py';compile(text,str(target),'exec')
with target.open('x',encoding='utf8',newline='\n') as out:out.write(text)
with (D/'SUPPORT-BINDING.json').open('x',encoding='utf8') as out:
    json.dump({'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'target_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'changes':['Exact EN3 Q/runtime/run/manifest pins','Job and authorship description'],
        'product_LOC_credit':0},out,indent=2);out.write('\n')
done=subprocess.run([sys.executable,'-B','-X','utf8',str(target)],cwd='T:/00-Active',capture_output=True,
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
for label,raw in [('stdout',done.stdout),('stderr',done.stderr)]:
    with (D/('initialize.'+label)).open('xb') as out:out.write(raw)
print(done.stdout.decode('utf-8-sig'),end='')
if done.stderr:print(done.stderr.decode('utf-8-sig'),file=sys.stderr,end='')
sys.exit(done.returncode)

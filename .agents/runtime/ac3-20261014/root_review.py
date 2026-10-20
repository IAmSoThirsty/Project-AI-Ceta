"""Distinct read-only native environment/cleanup review, with profile calls forbidden."""
from pathlib import Path
import ast,json,os,subprocess,sys
R=Path(__file__).resolve().parent;D=R/'independent-root-review';D.mkdir(exist_ok=False)
sys.path.insert(0,str(R));import ac3_support as s
Q=s.Q;F=s.F;RUN=s.RUN
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='274fbd34857409e54ef04991b4ba424332a58b87f553a2a1409bea64ff52c60b'
s.invoke(['node','claim',RUN,'review','--executor','/root','--workspace',str(Q)],'root-review-claim')
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text());names=[row['relative_path'] for row in manifest['payloads']]+['TRANSFER-MANIFEST.json']
before={name:s.ordinary(Q/name) for name in names}
results=[]
for original,copy,args in [('run_tests.py','run_tests_root.py',['root-r1']),('run_adverse.py','run_adverse_root.py',[])]:
    body=(R/original).read_text()
    if original=='run_tests.py':body=body.replace('from ac3_support import *','from ac3_support import *\nACTOR="/root"',1)
    else:
        body=body.replace("D=R/'adverse-r1'","D=R/'adverse-root-r1'",1)
        body=body.replace("R/'ADVERSE-QUALIFICATION.json'","R/'ADVERSE-QUALIFICATION-ROOT.json'",1)
    path=R/copy
    with path.open('x',encoding='utf-8') as out:out.write(body)
    done=subprocess.run([str(s.PY),'-B','-X','utf8',str(path),*args],cwd=F,capture_output=True,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    for suffix,raw in [('stdout',done.stdout),('stderr',done.stderr)]:s.fs.write_new(D/(copy+'.'+suffix),raw)
    results.append({'runner':s.reference(path),'exit_status':done.returncode})
    print(done.stdout.decode('utf-8-sig'),flush=True)
    if done.returncode:break
after={name:s.ordinary(Q/name) for name in names};assert before==after
s.write_new(D/'CONSERVATION.json',{'at':s.utc(),'candidate_before':before,'candidate_after':after,'commands':results,
 'Source_application':False,'profile_mutations_authorized_or_executed':False})
sys.exit(0 if len(results)==2 and all(row['exit_status']==0 for row in results) else 1)

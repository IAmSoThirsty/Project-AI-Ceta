"""Preserve r1 and repair only the reviewer-owned synthetic runtime fixture."""
from ct4_support import *
failed=read(V/'wrapper-tests.json')
assert failed['tests_run']==17 and failed['failures']==0 and failed['errors']==5
assert all('FileNotFoundError' in row['traceback'] and 'apply_reviewed_status.py' in row['traceback'] for row in failed['failed_details'])
p=V/'probe_wrappers.py';s=p.read_text(encoding='utf-8')
old="nfs.write_new(self.runtime/'ACCEPTED-SOURCE-BASELINE.json',(R/'ACCEPTED-SOURCE-BASELINE.json').read_bytes())"
assert s.count(old)==1
s=s.replace(old,old+"\n        nfs.write_new(self.runtime/'apply_reviewed_status.py',PUB.read_bytes())")
s=s.replace('wrapper-tests.txt','wrapper-tests-r2.txt').replace('wrapper-tests.json','wrapper-tests-r2.json')
with (V/'probe_wrappers_r2.py').open('x',encoding='utf-8') as out:out.write(s)
save(V/'fixture-repair.json',{'recorded_at':utc(),'original_probe':ref(p),'original_failed_suite':ref(V/'wrapper-tests.json'),
    'repaired_probe':ref(V/'probe_wrappers_r2.py'),'cause':'Five integration-prefix fixtures did not contain the exact publisher file required by the helper SHA pin. Twelve publication cases already passed. No claim/completion or negative boundary qualification is inferred from the five setup errors.',
    'change':'Copy exact frozen publisher bytes only into each fresh synthetic runtime, so real hash assertions execute against the real cut.',
    'Source_or_Root_helper_mutations':[],'prior_shell_preparation_failure':{'exit_status':1,'error':'PowerShell ParserError Missing argument in parameter list before Python execution; no generated r2 file or actual Source/helper/ledger mutation.'}})
print(json.dumps({'repaired_probe_sha256':sha(V/'probe_wrappers_r2.py')}))

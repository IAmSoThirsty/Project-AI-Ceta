"""Reuse the reviewed finite native custody recorder; no native effect run here."""
from et_support import *

origin=F/'.agents/runtime/et2-20261014/independent-root-review/run_native_custody.py'
raw=origin.read_text(encoding='utf-8')
assert raw.count('from review_support import *') == 1
raw=raw.replace('from review_support import *','from et_support import *')
raw=raw.replace('full394_prior_PID_capture','full406_prior_PID_capture')
with (R/'run_native_custody.py').open('x',encoding='utf-8',newline='\n') as output:
    output.write(raw)
write_new(R/'native-recorder-binding.json', {'at':utc(),'origin':reference(origin),
    'copy':reference(R/'run_native_custody.py'),
    'changes':['Own et_support binding','Accurate full406 historical-scope label'],
    'same_actual_native_tests':True,'native_effects_or_profile_operations':False})

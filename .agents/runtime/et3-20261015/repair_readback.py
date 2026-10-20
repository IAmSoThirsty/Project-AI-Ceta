"""Correct only the reader for the installed node-result envelope."""
from et_support import *
script=R/'seal_author.py'
fs.write_new(R/'seal_author.before_result_envelope_fix.py',fs.read_bytes(script))
actual=json.loads((R/RUN/'results/implement.json').read_text())
assert set(actual)=={'node_id','receipt_hash','result'}
write_new(R/'READBACK-FAILURE-r1.json',{'at':utc(),'command':str(script),'exit_status':1,
    'exception':'AssertionError','line':19,
    'failed_assertion':"assert typed(actual_result)==typed(local['result'])",
    'classification':'Reader shape assumption; actual completion remains SUCCEEDED and will not be repeated.',
    'actual_node_result':reference(R/RUN/'results/implement.json'),
    'repair':'Verify installed three-key envelope and compare its result member with the original authored result.'})
raw=script.read_text(encoding='utf-8')
old="assert typed(actual_result)==typed(local['result'])"
new="assert set(actual_result)=={'node_id','receipt_hash','result'}\nassert actual_result['node_id']=='implement' and actual_result['receipt_hash']==persisted['receipt_hash']\nassert typed(actual_result['result'])==typed(local['result'])"
assert raw.count(old)==1
script.write_text(raw.replace(old,new),encoding='utf-8',newline='\n')

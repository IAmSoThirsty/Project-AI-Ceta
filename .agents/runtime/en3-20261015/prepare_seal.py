"""Reuse the exact installed-result envelope readback with EN3 members."""
from en_support import *
origin=F/'.agents/runtime/et3-20261015/seal_author.py'
raw=origin.read_text(encoding='utf-8').replace('from et_support import *','from en_support import *')
raw=raw.replace("'frozen_payload_count':317", "'frozen_payload_count':296")
begin=raw.index("members=('HANDOFF.json'")
end=raw.index("write_new(R/'AUTHOR-SEAL.json'",begin)
members="""members=('HANDOFF.json','implement.json','AUTHOR-READBACK.json','SELF-REVIEW.json',
    'targeted-r2.json','targeted-r2.txt','targeted-r1.json','targeted-r1.txt',
    'before-r1.json','before-r1.txt','implementation-measures.json','SOURCE-INPUTS.json')
"""
raw=raw[:begin]+members+raw[end:]
with (R/'seal_author.py').open('x',encoding='utf-8',newline='\n') as output:output.write(raw)
write_new(R/'READBACK-SUPPORT-BINDING.json',{'at':utc(),'origin':reference(origin),
    'own_copy':reference(R/'seal_author.py'),'changes':['Own en_support','Payload296 label','Own exact sealed members'],
    'completion_will_not_be_repeated':True})

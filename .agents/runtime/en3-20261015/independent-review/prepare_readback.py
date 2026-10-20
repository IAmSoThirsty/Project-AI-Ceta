"""Reuse exact qualified receipt reader with EN3-specific frozen bindings."""
from review_support import *
source=F/'.agents/runtime/et3-20261015/independent-review/readback_and_seal_r2.py'
body=source.read_text()
changes=[("'b061311cf6f52c89b9af93845258ca061043ef6ef60d8530b9048983351e5c9a'","'8772cd735ae0ff767108976fef15e004012718ffded50a1d888cc354fae329ec'"),
    ("setup['whole_original_Q']","setup['whole_Q']"),
    ("'Source290_Q708_retained_at_readback'","'Source290_Q297_retained_at_readback'"),
    ("'prior_reader_failure':ordinary(D/'REVIEW-READBACK-FAILURE-r1.json')","'prior_setup_failure':ordinary(D/'PREPARATION-FAILURE-r1.json')")]
for before,after in changes:
    assert body.count(before)==1,before
    body=body.replace(before,after)
target=D/'readback_and_seal.py';compile(body,str(target),'exec')
with target.open('x',encoding='utf8',newline='\n') as out:out.write(body)
write(D/'READBACK-BINDING.json',{'at':utc(),'source':ordinary(source),'reader':ordinary(target),
    'bindings':['EN3 manifest pin','EN3 whole-Q snapshot key/count','Exact EN3 prior setup failure'],
    'receipt_hash_domain':'Installed sha256_json(input_hash + result) for read-only artifact; strict13/persisted16 typed equality and exact3-key result envelope',
    'product_LOC_credit':0})
print(json.dumps({'reader':str(target),'sha256':sha(target)}),flush=True)

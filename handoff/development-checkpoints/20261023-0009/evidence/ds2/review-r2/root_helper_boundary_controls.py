"""Inert approval-boundary ports for the exact corrected Root closure function."""
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import ast,copy,json,posixpath
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/ds2';R=B/'review-r2';helper=B/'control-r2/ROOT-CLOSE-QUALIFICATION-R2.py'
source=helper.read_text(encoding='utf8');node=next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef) and x.name=='approved_review');code=compile(ast.Module(body=[node],type_ignores=[]),'exact Root helper approval function with inert ports','exec');cases=[]
def case(label,mutate,expected):
 review=dict(decision='approved',manifest_sha256='PREP',root_candidate_closure_sha256='HELPER',reviewer='/root/status_packet_review')
 rm=dict(decision='approved',candidate_manifest_sha256='PREP',root_candidate_closure_sha256='HELPER',review_sha256='REPORT',files={'evidence.json':'FILE'})
 state=dict(nodes=dict(review=dict(state='SUCCEEDED',decision='approved',executor_id='/root/status_packet_review'),implement=dict(executor_id='/root/broader_successor_author')))
 receipt=dict(decision='approved',executor_id='/root/status_packet_review',result=dict(manifest_sha256='PREP',review_sha256='REPORT',root_candidate_closure_sha256='HELPER'))
 hashes={'virtual/work/MANIFEST.json':'PREP','virtual/review/MANIFEST.json':'REVIEW_MF','virtual/review/REVIEW.json':'REPORT','virtual/review/evidence.json':'FILE','virtual/helper.py':'HELPER'}
 mutate(review,rm,state,receipt,hashes)
 files={'virtual/review/REVIEW.json':json.dumps(review).encode(),'virtual/review/MANIFEST.json':json.dumps(rm).encode()}
 class VPath:
  def __init__(self,value):self.value=value.value if isinstance(value,VPath) else str(value)
  def __truediv__(self,name):return VPath(self.value+'/'+name)
  def read_bytes(self):return files[self.value]
  def resolve(self):return VPath(posixpath.normpath(self.value))
  def is_relative_to(self,other):return PurePosixPath(self.value).is_relative_to(PurePosixPath(other.value))
  def __str__(self):return self.value
 namespace=dict(W=VPath('virtual/work'),R=VPath('virtual/review'),Path=VPath,__file__='virtual/helper.py',json=json,sha=lambda path:hashes[str(path)])
 exec(code,namespace);failure=None;answer=None
 try:answer=namespace['approved_review']('PREP','REVIEW_MF',state,receipt)
 except AssertionError as error:failure=type(error).__name__
 assert (failure is None)==expected,(label,failure,expected)
 if expected:assert answer==review
 cases.append(dict(id=label,passed=True,accepted=expected,refusal=failure,real_filesystem_or_Root_main_or_gate_or_claim_action=False))
case('matching_exact_review_and_receipt_accepts',lambda *x:None,True)
case('unapproved_review_refused',lambda r,m,s,t,h:r.update(decision='rejected'),False)
case('different_helper_hash_refused',lambda r,m,s,t,h:r.update(root_candidate_closure_sha256='OTHER'),False)
case('source_manifest_drift_refused',lambda r,m,s,t,h:h.update({'virtual/work/MANIFEST.json':'DRIFT'}),False)
case('review_manifest_drift_refused',lambda r,m,s,t,h:h.update({'virtual/review/MANIFEST.json':'DRIFT'}),False)
case('review_evidence_hash_drift_refused',lambda r,m,s,t,h:h.update({'virtual/review/evidence.json':'DRIFT'}),False)
case('review_path_escape_refused',lambda r,m,s,t,h:m.update(files={'../outside.json':'FILE'}),False)
case('self_review_executor_refused',lambda r,m,s,t,h:s['nodes']['implement'].update(executor_id='/root/status_packet_review'),False)
case('receipt_manifest_mismatch_refused',lambda r,m,s,t,h:t['result'].update(manifest_sha256='OTHER'),False)
case('receipt_helper_mismatch_refused',lambda r,m,s,t,h:t['result'].update(root_candidate_closure_sha256='OTHER'),False)
report=dict(classification='EXACT_CORRECTED_ROOT_HELPER_APPROVAL_BOUNDARY_SYNTHETIC_PORTS',cases=cases,case_count=len(cases),Root_main_gate_or_claim_executed=False,provider_or_canonical_bodies_executed=False,full_product_acceptance=False)
with (R/'ROOT-HELPER-BOUNDARY-CONTROLS.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(report,indent=2))

from __future__ import annotations
import copy,hashlib,importlib.util,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
P=Path(r"T:\00-Active\Project-AI-CETA")
Q=P/".agents/ct1-20261014"
R=P/".agents/runtime/ct2-20261014"
O=R/"independent-review"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise RuntimeError("duplicate JSON key:"+k)
        result[k]=v
    return result
def invalid(v):raise RuntimeError("non-finite JSON value:"+v)
def read(p):return json.loads(p.read_bytes(),object_pairs_hook=unique,parse_constant=invalid)
def need(c,m):
    if not c:raise RuntimeError(m)
def leaves(v):
    if isinstance(v,dict):return sum(leaves(x) for x in v.values())
    if isinstance(v,list):return sum(leaves(x) for x in v)
    return 1
def save(n,v):
    with (O/n).open("x",encoding="utf-8") as out:json.dump(v,out,indent=2);out.write("\n")
start=datetime.now(timezone.utc).isoformat()
claim=read(O/"claim.json")["response"]["claim"]
manifest=read(Q/"TRANSFER-MANIFEST.json")
need(sha(Q/"TRANSFER-MANIFEST.json")=="6ebe98c39182233943bdce6ff26ea2ab878397abc04ed35d74a09b972e466ea9","manifest changed")
rows=[];before_docs={};candidate_docs={}
for row in manifest["payloads"]:
    rel=row["relative_path"]
    before=P/".agents/runtime/ct1-20261014/before"/rel
    candidate=Q/rel
    active=P/rel
    need(sha(before)==sha(active)==row["active_before_sha256"],"active metadata before-image changed")
    need(sha(candidate)==row["candidate_sha256"],"candidate metadata changed")
    old,new=read(before),read(candidate)
    need(isinstance(old,dict) and isinstance(new,dict),"metadata must remain JSON objects")
    need(set(old)<=set(new),"prior key deleted")
    allowed=set(row["allowed_changed_keys"])
    changed={k for k in set(old)|set(new) if k not in old or k not in new or old[k]!=new[k]}
    need(changed<=allowed,"non-whitelisted key changed")
    retained={k:v for k,v in old.items() if k not in allowed}
    need(all(k in new and new[k]==v for k,v in retained.items()),"prior nested value changed")
    need(old["schema_version"]==new["schema_version"],"schema version changed")
    rows.append({"path":rel,"before_sha256":sha(before),"candidate_sha256":sha(candidate),"changed_keys":sorted(changed),"retained_top_keys":len(retained),"retained_nested_leaf_values":leaves(retained),"complete_JSON_objects_validated":True})
    before_docs[rel]=old;candidate_docs[rel]=new
co=candidate_docs["handoff/continuity.json"]
pr=candidate_docs["build/progress.json"]
facts=co["current_repository_execution_20261014"]
need(facts==pr["current_repository_execution_20261014"],"two current status records diverge")
need(co["historical_latest_source_tests_before_repository_consolidation_20261014"]==before_docs["handoff/continuity.json"]["latest_source_tests"],"old707 observation not preserved intact")
need(co["historical_latest_source_tests_before_repository_consolidation_20261014"]["passed"]==707,"historical707 count differs")
need(co["latest_source_tests"]==facts["current_scoped_tests"],"latest tests/current scoped record differ")
need(facts["authoritative_repository"]==co["authoritative_application_root"]==str(P),"active repo identity differs")
need(facts["display_identity"]=="Project-AI: CETA" and facts["Git_HEAD"]==claim["git_baseline"]["head"] and facts["branch"]=="build/standalone","current repository/version identity differs")
need(facts["accepted_source_integrations"]==["APP3","BR1"],"accepted integration IDs differ")
proofs={item["relative_path"]:item["sha256"] for item in facts["proofs"]}
need(len(proofs)==len(facts["proofs"]) and proofs==manifest["proofs"],"proof reference lists diverge or duplicate")
proof_rows=[]
for rel,h in proofs.items():
    path=P/rel
    need(not Path(rel).is_absolute() and ".." not in Path(rel).parts and path.is_relative_to(P),"unsafe proof locator")
    need(sha(path)==h,"referenced proof digest differs:"+rel)
    proof_rows.append({"relative_path":rel,"sha256":h,"exact":True})
br=read(P/".agents/runtime/br1-20261014/integrate.json")
desktop=read(P/".agents/runtime/br1-20261014/destination-desktop.json")
dest=read(P/".agents/runtime/br1-20261014/active-destination-review/destination-review.json")
need(br["exit_status"]==0 and dest["decision"]=="approved" and dest["exit_status"]==0,"BR1 not accepted")
need(br["result"]["tests_run"]==dest["tests_run"]==desktop["tests_run"]==118,"BR1 current118 differs")
need(br["result"]["source_root"]==dest["source_root"]==desktop["source_root"]==str(P),"BR1 current source differs")
need(not facts["current_scoped_tests"]["complete_contract_suite"],"current bounded cohort claimed full suite")
expected=dest["expected_payload_hashes"]
need(len(expected)==235 and facts["source_payloads"]==235,"BR1 payload count differs")
current={rel:sha(P/rel) for rel in expected}
need(current==expected,"active product bytes drifted from approved BR1 cut")
need(len([n for n in expected if n.startswith("src/") and n.endswith(".py")])==facts["product_modules"]==72,"product module count differs")
# Verify BR1 raw exact IDs, rather than accepting only a reported number.
raw=(P/".agents/runtime/br1-20261014/destination-desktop.txt").read_text(encoding="utf-8")
starts=list(re.finditer(r"^test\S+ \(([^)]+)\)",raw,re.M))
rawids=[]
for index,item in enumerate(starts):
    end=starts[index+1].start() if index+1<len(starts) else len(raw)
    segment=raw[item.end():end]
    outcomes=re.findall(r"\.\.\. (ok|FAIL|ERROR|skipped[^\r\n]*)",segment)
    need(len(outcomes)==1,"BR1 per-case raw outcome ambiguous")
    rawids.append((item.group(1),outcomes[0]))
need(len(rawids)==118 and all(status=="ok" for _,status in rawids),"BR1 raw expected118 differs")
need([i for i,_ in rawids]==desktop["expected_ids"]==desktop["executed_ids"],"BR1 exact raw/expected/executed IDs differ")
need(sha(P/".agents/runtime/br1-20261014/destination-desktop.txt")==desktop["raw_sha256"],"BR1 raw bound hash differs")
app=read(P/".agents/runtime/app3-20261014/integrate.json")
full=read(P/".agents/runtime/rs2-20261014/active-application/destination-full-r2.json")
need(app["exit_status"]==0 and app["result"]["tests_run"]==full["tests_run"]==1158,"APP3 historical full1158 differs")
need(facts["preceding_full_contract_run"]["original_source_root"]==app["result"]["source_root"],"historical source identity rewritten")
need(facts["preceding_full_contract_run"]["cut"]=="APP3_BEFORE_RENAME_AND_BR1" and facts["preceding_full_contract_run"]["freshness"]=="HISTORICAL_EXACT_TESTED_CUT","historical cut relabeled current")
rename=read(P/".agents/runtime/rename-20261014/independent-review/post-move-integrity.json")
relocation=read(P/".agents/runtime/rename-20261014/identity-destination-review/identity-relocation-review.json")
need(rename["decision"]=="approved" and rename["exit_status"]==0 and relocation["decision"]=="approved" and relocation["exit_status"]==0,"rename/relocation not accepted")
need(relocation["tests_run"]==facts["independent_relocation_cases"]==17,"relocation17 differs")
# Exact count keys differ between evidence formats; inspect the entire bound object for recorded scalar membership.
need(facts["whole_rename_inventory_members"]==97065 and facts["whole_rename_ordinary_bytes"]==7214787541,"rename exact quantities differ")
rename_values=[]
def walk(v):
    if isinstance(v,dict):
        for value in v.values():walk(value)
    elif isinstance(v,list):
        for value in v:walk(value)
    else:rename_values.append(v)
walk(rename)
need(97065 in rename_values and 7214787541 in rename_values,"rename quantities absent from exact proof")
need(len(relocation["identity_rows"])==facts["identity_paths_applied"]==7,"seven identity count differs")
hp3=read(P/".agents/runtime/hp3-20261014/independent-review/review.json")
need(hp3["decision"]=="rejected" and hp3["exit_status"]==1,"failed HP3 relabeled success")
need(facts["HP3_author_cut"]["state"]=="IMPLEMENT_SUCCEEDED_INDEPENDENT_REVIEW_REJECTED","HP3 state differs")
need(facts["HP3_author_cut"]["independent_tests"]=={"total":117,"passed":113,"failures":4,"errors":0,"skips":0},"HP3 result counts differ")
need(facts["HP3_author_cut"]["blocking_findings"]==[v["id"] for v in hp3["result"]["findings"]],"HP3 findings IDs differ")
need(facts["HP3_author_cut"]["source_meaningful_LOC_added"]==477 and facts["HP3_author_cut"]["source_meaningful_LOC_removed"]==9 and facts["HP3_author_cut"]["new_test_meaningful_LOC"]==557,"HP3 LOC differs")
partial=read(P/".agents/runtime/hp1-root-review-20261014/partial-archive-verification.json")
need(facts["history_capture"]=={"status":"PARTIAL","held_entries":69,"pack_and_binary_diff":"WITHHELD"},"partial history relabeled complete")
cut=datetime.fromisoformat(facts["recorded_at"])
foc=P/".agents/runtime/hp4-20261014/blocked-repair-r2.json"
focr=read(foc);full4=read(P/".agents/runtime/hp4-20261014/complete-r3.json")
need(datetime.fromisoformat(focr["finished_at"])<cut<datetime.fromisoformat(full4["finished_at"]),"HP4 pending-at-cut statement differs from test completion epoch")
focusedraw=(P/".agents/runtime/hp4-20261014/blocked-repair-r2.txt").read_text(encoding="utf-8")
focids=re.findall(r"^test\S+ \(([^)]+)\) \.\.\. (ok|FAIL|ERROR|skipped[^\r\n]*)",focusedraw,re.M)
need(len(focids)==7 and all(v=="ok" for _,v in focids) and focr["exit_status"]==0,"HP4 seven focused results differ")
need(sha(Path(focr["output_path"]))==focr["output_sha256"],"HP4 focused raw hash differs")
need(facts["HP4_repair"]["state"]=="AUTHOR_IMPLEMENTATION_IN_PROGRESS_AT_THIS_CUT" and facts["HP4_repair"]["full_suite_and_independent_review"]=="PENDING","later HP4 result silently promoted")
# Use the existing reader with old and candidate progress objects; preserve every global result axis.
spec=importlib.util.spec_from_file_location("ct1_existing_measurements",P/"tools/build_measurements.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
inputbytes={n:(P/rel).read_bytes() for n,rel in module.INPUTS.items()}
documents={n:json.loads(v) for n,v in inputbytes.items()}
oldmeasure=module.measurements(documents)
newdocuments=copy.deepcopy(documents);newdocuments["progress"]=pr
newmeasure=module.measurements(newdocuments)
need(oldmeasure==newmeasure,"existing measurements reader axes changed")
need(all((P/module.INPUTS[n]).read_bytes()==v for n,v in inputbytes.items()),"global reader inputs changed during review")
sourceafter={rel:sha(P/rel) for rel in expected}
need(sourceafter==current==expected,"active source changed during review")
for row in manifest["payloads"]:need(sha(P/row["relative_path"])==row["active_before_sha256"],"active metadata source changed before acceptance")
candidatehash={"00-Active/Project-AI-CETA/.agents/ct1-20261014/"+f.relative_to(Q).as_posix():sha(f) for f in Q.rglob("*") if f.is_file()}
need(candidatehash==claim["baseline_snapshot"],"three frozen claim members changed")
proof={"schema_version":1,"reviewer":"/root/history_preservation","decision":"approved","exit_status":0,"started_at":start,"finished_at":datetime.now(timezone.utc).isoformat(),"source_root":str(P),"candidate_root":str(Q),"manifest_sha256":sha(Q/"TRANSFER-MANIFEST.json"),"claim_input_hash":claim["input_hash"],"metadata_rows":rows,"old707_preserved_intact":True,"both_current_status_records_identical":True,"proofs":proof_rows,"manifest_proof_count":len(proof_rows),"current235_payload_hashes":current,"source235_before_after_exact":True,"current72_module_count":72,"current_BR1_118":True,"BR1_exact_raw_ids":[v[0] for v in rawids],"APP3_historical1158_before_rename_and_BR1":True,"rename97065_members_7214787541_bytes":True,"identity7_and_relocation17":True,"HP3_rejected113pass4fail":True,"HP4_pending_at_cut":{"recorded_at":facts["recorded_at"],"focused_finished_at":focr["finished_at"],"focused_receipt_sha256":sha(foc),"focused_raw_sha256":focr["output_sha256"],"focused_exact_ids":[v[0] for v in focids],"later_full_finished_at":full4["finished_at"],"later_full_receipt_sha256":sha(P/".agents/runtime/hp4-20261014/complete-r3.json"),"frozen_status_not_updated_for_later_event":True},"existing_reader_compatibility":{"path":"tools/build_measurements.py","sha256":sha(P/"tools/build_measurements.py"),"old_and_candidate_axes_identical":True,"axes":newmeasure,"protected_inputs":{module.INPUTS[n]:hashlib.sha256(v).hexdigest() for n,v in inputbytes.items()},"validate_package":"Existing explicit progress-field accesses retained; formal business-record schemas do not constrain these continuity/progress metadata objects."},"frozen_candidate_hashes":candidatehash,"runtime_tests_executed_in_this_review":0,"active_source_application":False,"existing_issues":[{"id":"HP3-F01","classification":"not_blocking_this_status_review;blocking_HP3_policy_activation","recorded":"rejected"},{"id":"HP3-F02","classification":"not_blocking_this_status_review;blocking_HP3_policy_activation","recorded":"rejected"},{"id":"HP1_PARTIAL_HISTORY","classification":"requires_separate_follow_up_work","recorded":"PARTIAL69_WITHHELD"}],"findings":[],"acceptance_scope":"Exact timestamped two-file status candidate only; source publication requires fresh before-image CAS. Later HP4/WA1 results require separate evidence/candidate; global product gates retain their previous values."}
save("status-verification.json",proof)
print(json.dumps({"decision":"approved","metadata_paths":2,"exact_proof_hashes":len(proof_rows),"active235_exact":True,"preserved_leaf_values":sum(v["retained_nested_leaf_values"] for v in rows),"HP4_pending_epoch_correct":True,"report_sha256":sha(O/"status-verification.json")}))

import difflib,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
p=Path(r"T:\00-Active\Project-AI-CETA");o=p/".agents/runtime/ct2-20261014/independent-review";r=p/".agents/runtime/app3-20261014/active-application"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((r/"APPLICATION.json").read_text());before={v["relative_path"]:v for v in j["before_images"]};counts={"source":{"added":0,"removed":0},"test":{"added":0,"removed":0}};rows=[]
for row in j["completed"]:
    n=row["relative_path"];kind="source" if n.startswith("src/") else "test" if n.startswith("tests/") else None
    if not kind:continue
    original=(r/"before"/(n+".source")).read_bytes() if n in before else b""
    if n in before:assert hashlib.sha256(original).hexdigest()==before[n]["sha256"]
    current=(p/n).read_bytes();assert hashlib.sha256(current).hexdigest()==row["sha256"]
    added=removed=0
    for tag,a,b,c,d in difflib.SequenceMatcher(None,original.decode().splitlines(),current.decode().splitlines(),autojunk=False).get_opcodes():
        if tag!="equal":added+=d-c;removed+=b-a
    counts[kind]["added"]+=added;counts[kind]["removed"]+=removed;rows.append({"relative_path":n,"added":added,"removed":removed,"original_sha256":hashlib.sha256(original).hexdigest() if original else None,"applied_sha256":row["sha256"]})
facts=json.loads((p/".agents/ct1-20261014/handoff/continuity.json").read_text())["current_repository_execution_20261014"]
assert counts["source"]==facts["source_physical_transfer_LOC_APP3"] and counts["test"]==facts["test_physical_transfer_LOC_APP3"]
br=json.loads((p/".agents/runtime/br1-20261014/integrate.json").read_text())["result"]
assert br["source_physical_LOC"]==facts["source_physical_LOC_BR1"] and br["new_test_LOC"]==facts["new_test_LOC_BR1"]
titles={k:br["title_changes"]["src/ceta/desktop/"+k+".py"][1] for k in facts["desktop_titles"]};assert titles==facts["desktop_titles"]
oldledger=json.loads((o/"prior-ledger-before.json").read_text());assert all(sha(Path(n))==h for n,h in oldledger.items())
v={"schema_version":1,"observed_at":datetime.now(timezone.utc).isoformat(),"APP3_physical_transfer_LOC":counts,"exact_original_and_applied_source_hashes_verified":True,"rows":rows,"BR1_physical_LOC_and_titles_exact":True,"BR1_titles":titles,"prior_CT1_ledger_hashes_before_after_exact":oldledger,"fresh_execution_command":[__import__("sys").executable,"-B","-X","utf8",__file__],"exit_status":0}
with (o/"transfer-metrics-verification.json").open("x",encoding="utf-8") as out:json.dump(v,out,indent=2);out.write("\n")
print(json.dumps({"source":counts["source"],"tests":counts["test"],"prior_ledger_retained":True,"report_sha256":sha(o/"transfer-metrics-verification.json")}))

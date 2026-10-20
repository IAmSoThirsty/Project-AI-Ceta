"""Bounded adversarial evaluation: deterministic mock, replay, or real local Ollama.

A mock pass is only a host protocol smoke test, never a model-behavior score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from truth_accountability import (GovernedTruthCore, GovernedModelBridge,
    VerificationRegistry, VerifierSpec, bounded_arithmetic, arithmetic_only_policy,
    LocalOllamaProposalClient, SocietalGatedPipeline,
    Version1ReadOnlyAdapter, CorpusMapping)


def _load_cases(path: Path) -> tuple[bytes,list[dict]]:
    raw = path.read_bytes()
    if len(raw) > 2*1024*1024:
        raise ValueError("Evaluation manifest exceeds 2 MiB")
    cases = []
    seen = set()
    for row in raw.splitlines():
        if not row.strip():
            continue
        x = json.loads(row)
        if not isinstance(x,dict) or not {"id","source","proposal","expected_mock_status"} <= set(x):
            raise ValueError("Malformed case")
        if not isinstance(x["source"],str) or not x["source"] or len(x["source"])>4096:
            raise ValueError("Invalid test source")
        if not isinstance(x["id"],str) or x["id"] in seen or len(x["id"])>100:
            raise ValueError("Duplicate/invalid case id")
        if not isinstance(x["proposal"],dict):
            raise ValueError("Invalid model fixture proposal")
        seen.add(x["id"])
        cases.append(x)
    if len(cases) < 1 or len(cases) > 5000:
        raise ValueError("Case count out of bounds")
    return raw,cases


class MockProposer:
    """FIXTURE only. This produces no language-model inference."""
    def __init__(self, candidate: dict):
        self.candidate=candidate
    def generate_proposal(self, source_id: str, source_text: str, *, contextual_references=None) -> str:
        obj=json.loads(json.dumps(self.candidate))
        if obj.get("source_id")=="$SOURCE_ID":
            obj["source_id"]=source_id
        if obj.get("text")=="$SOURCE_TEXT":
            obj["text"]=source_text
        if obj.get("span")=="$FULL_SPAN":
            obj["span"]=[0,len(source_text)]
        return json.dumps(obj,ensure_ascii=False)


class ReplayProposer:
    """A stored candidate is replay evidence, NOT live model inference."""
    def __init__(self,raw: str): self.raw=raw
    def generate_proposal(self,source_id,source_text, *, contextual_references=None):
        return self.raw.replace("$SOURCE_ID",source_id)


def run_evaluation(*, cases_path: Path, backend: str, model: str = "",
                   endpoint: str = "http://127.0.0.1:11434", replay_path: Path | None = None,
                   version1_source: Path | None = None, mapping_path: Path | None = None,
                   expected_source_sha256: str | None = None) -> dict:
    if backend not in {"mock","ollama","replay"}:
        raise ValueError("Unsupported backend")
    manifest,cases=_load_cases(cases_path)
    replay = {}
    if backend=="replay":
        if not replay_path:
            raise ValueError("Replay backend requires recorded candidates")
        blob=replay_path.read_bytes()
        if len(blob)>2*1024*1024:
            raise ValueError("Oversized replay")
        replay=json.loads(blob)
        if not isinstance(replay,dict):
            raise ValueError("Replay must be an id-to-candidate map")
    if backend=="ollama" and not model:
        raise ValueError("Live evaluation requires an explicit installed local model")
    adapter=None
    source_report=None
    if bool(version1_source) != bool(mapping_path):
        raise ValueError("Source and explicit reviewed field mapping must be provided together")
    if version1_source and mapping_path:
        obj=json.loads(mapping_path.read_text(encoding="utf-8"))
        mapping=CorpusMapping(**obj)
        adapter=Version1ReadOnlyAdapter(version1_source,mapping=mapping,
                                        expected_zip_sha256=expected_source_sha256)
        source_report=adapter.inspect().__dict__
    records=[]
    for case in cases:
        registry=VerificationRegistry()
        registry.register(VerifierSpec("arithmetic","arithmetic-v1",bounded_arithmetic))
        core=GovernedTruthCore(registry=registry)
        try:
            bridge=GovernedModelBridge(core,arithmetic_only_policy)
            pipeline=SocietalGatedPipeline(core,bridge,adapter)
            if backend=="mock":
                proposer=MockProposer(case["proposal"])
            elif backend=="ollama":
                proposer=LocalOllamaProposalClient(model=model,endpoint=endpoint)
            else:
                value=replay.get(case["id"])
                if not isinstance(value,str):
                    raise ValueError(f"Missing replay for {case['id']}")
                proposer=ReplayProposer(value)
            result=pipeline.execute(speaker_id="synthetic-speaker",exact_text=case["source"],
                                    proposer=proposer, trusted_scope={"eval_case":case["id"]})
            case_status=result.decision
            mock_pass=(case_status==case["expected_mock_status"]) if backend=="mock" else None
            records.append({"id":case["id"],"case_family":case.get("family","unspecified"),
                "status":case_status,"context_status":result.context_status,
                "context_refs":list(result.context_refs),"claim_id":result.claim_id,
                "model_raw_sha256":result.raw_proposal_sha256,
                "emitted_unqualified_fact":result.established_fact,
                "mock_expected_status":case["expected_mock_status"],
                "mock_protocol_pass":mock_pass,
                "response_sha256":hashlib.sha256(result.response.encode('utf-8')).hexdigest()})
        finally:
            core.close()
    statuses=dict(sorted(Counter(x["status"] for x in records).items()))
    result={"evaluation_contract":"adversarial-mock-and-live-v1",
            "recorded_at":datetime.now(timezone.utc).isoformat(),
            "backend":backend,
            "inference_class":({"mock":"DETERMINISTIC_SIMULATION_NO_MODEL",
                                "replay":"RECORDED_PROPOSALS_NOT_LIVE",
                                "ollama":"LIVE_LOCAL_MODEL_INFERENCE"})[backend],
            "model":model if backend=="ollama" else None,
            "case_manifest_sha256":hashlib.sha256(manifest).hexdigest(),
            "python":platform.python_version(),
            "case_count":len(cases),"statuses":statuses,
            "mock_protocol_passed":sum(r["mock_protocol_pass"] is True for r in records) if backend=="mock" else None,
            "source_inspection":source_report,
            "records":records,
            "limitations": ["Status matching checks the mechanical gate, not whether the model understood the user.",
                "No participant meaning or human consensus can be established from synthetic mock inputs.",
                "Unverified inventory mechanisms are advisory, never independent fact evidence.",
                "Live-model evaluation requires an actually running local Ollama model and separate human-rated truth/fidelity assessments."]}
    return result


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend",choices=["mock","ollama","replay"],default="mock")
    p.add_argument("--cases",type=Path,default=Path(__file__).parent / "evaluations" / "public_adversarial.jsonl")
    p.add_argument("--model",default="")
    p.add_argument("--endpoint",default="http://127.0.0.1:11434")
    p.add_argument("--replay",type=Path)
    p.add_argument("--source",type=Path)
    p.add_argument("--mapping",type=Path)
    p.add_argument("--expected-source-sha256",default=None)
    p.add_argument("--report",type=Path)
    args=p.parse_args(argv)
    try:
        report=run_evaluation(cases_path=args.cases,backend=args.backend,
            model=args.model,endpoint=args.endpoint,replay_path=args.replay,
            version1_source=args.source,mapping_path=args.mapping,
            expected_source_sha256=args.expected_source_sha256)
    except (OSError,ValueError,RuntimeError,TypeError,PermissionError,ConnectionError) as exc:
        print("EVALUATION_NOT_COMPLETED:",type(exc).__name__,str(exc),file=sys.stderr)
        return 2
    payload=json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(payload,encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("backend","inference_class","case_count","statuses","mock_protocol_passed","case_manifest_sha256")},indent=2))
    return 0 if args.backend!="mock" or report["mock_protocol_passed"]==report["case_count"] else 1


if __name__=="__main__":
    raise SystemExit(main())

"""Pinned Version 1 real-source smoke test with a SYNTHETIC model proposal.

Does NOT run a real language model, deliver messages, or change the source.
Requires both the original owner ZIP and a clean extraction of that ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from truth_accountability import (
    CorpusMapping, GovernedModelBridge, GovernedTruthCore,
    SocietalGatedPipeline, Version1ReadOnlyAdapter, Version1RuntimeAdvisor,
    arithmetic_only_policy,
)

PIN='b76b9482f95b93b0a25b8d88881ac3b68558b077118f32e3360f383ded4247b5'


class SimulatedProposal:
    def generate_proposal(self, source_id, source_text, *, contextual_references=None):
        return json.dumps({'kind': 'paraphrase', 'text': 'You demanded obedience',
                           'source_id': source_id, 'span': [0,len(source_text)]})


def verify_extracted_source(archive: Path, root: Path) -> int:
    base='Societal-Reasoning-Core/'
    count=0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            if not info.filename.startswith(base):
                raise ValueError('Unexpected source root')
            rel=Path(info.filename[len(base):])
            if rel.is_absolute() or '..' in rel.parts or not rel.parts:
                raise ValueError('Unsafe archive member')
            file=root/rel
            if file.is_symlink() or not file.is_file() or file.read_bytes()!=z.read(info):
                raise ValueError('Extracted runtime differs from ZIP: '+rel.as_posix())
            count+=1
    return count


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True,type=Path)
    p.add_argument('--runtime-root',required=True,type=Path)
    args=p.parse_args()
    if hashlib.sha256(args.archive.read_bytes()).hexdigest()!=PIN:
        raise ValueError('The supplied Version 1 ZIP differs from the inspected owner archive')
    matches=verify_extracted_source(args.archive,args.runtime_root)
    if matches!=109:
        raise ValueError('Unexpected Version 1 source membership')
    mapping=CorpusMapping('src/societal_reasoning/resources/concepts.full.jsonl',
                          'id','original_text',2000)
    adapter=Version1ReadOnlyAdapter(args.archive,mapping=mapping,expected_zip_sha256=PIN)
    inspected=adapter.inspect()
    src=(args.runtime_root/'src').resolve()
    sys.path.insert(0,str(src))
    import societal_reasoning
    if not Path(societal_reasoning.__file__).resolve().is_relative_to(src):
        raise RuntimeError('Source runtime import was redirected')
    if societal_reasoning.__version__!='1':
        raise RuntimeError('Unexpected Version 1 runtime identity')
    advisor=Version1RuntimeAdvisor(societal_reasoning.SocietalReasoner.starter())
    core=GovernedTruthCore()
    try:
        pipe=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy),
                                   adapter,advisor)
        source='I asked you to understand the social context, not obey.'
        result=pipe.execute(speaker_id='synthetic-speaker',exact_text=source,
                            proposer=SimulatedProposal())
        if 'You demanded obedience' in result.response or not core.integrity_report()['ok']:
            raise RuntimeError('The simulation violated semantic or audit gates')
        print(json.dumps({'source_sha256':PIN,'source_files_matched':matches,
            'records':inspected.records,'v1_api_schema':'text_assessment.v1',
            'version1_advisory':result.version1_runtime_review,
            'governed_decision':result.decision,'invented_attribution_published':False,
            'synthetic_only':True},indent=2))
    finally:core.close()
    return 0


if __name__=='__main__':raise SystemExit(main())

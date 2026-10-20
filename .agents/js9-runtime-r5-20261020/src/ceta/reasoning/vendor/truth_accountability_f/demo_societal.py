"""Offline, synthetic demonstration: no Version 1 source or model is touched."""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from truth_accountability import (CorpusMapping,Version1ReadOnlyAdapter,
    GovernedTruthCore,GovernedModelBridge,SocietalGatedPipeline,
    arithmetic_only_policy)


class ScriptedFakeModel:
    def generate_proposal(self,source_id,source_text,*,contextual_references=None):
        print('Advisory entries retrieved:',len(contextual_references or []))
        return json.dumps({'kind':'paraphrase','text':'You demanded obedience',
                           'source_id':source_id,'span':[0,len(source_text)]})


def main():
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'synthetic.zip'
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('fixture/context.jsonl','\n'.join(json.dumps(
                {'record_id':f'R{i}', 'text':'When someone asks to understand, preserve their meaning without adding demands'})
                for i in range(1,4))+'\n')
        mapping=CorpusMapping('fixture/context.jsonl','record_id','text',3,'R',0)
        adapter=Version1ReadOnlyAdapter(path,mapping=mapping)
        print('Source inspection:',adapter.inspect().status,'(SYNTHETIC TEST DATA)')
        core=GovernedTruthCore()
        try:
            runner=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy),adapter)
            outcome=runner.execute(speaker_id='synthetic-speaker',exact_text='I asked you to understand.',
                proposer=ScriptedFakeModel())
            print('Governed decision:',outcome.decision)
            print('Published candidate:',outcome.response)
            print('Original preserved:',core.original(outcome.source_id))
            print('Fact proven?',outcome.established_fact)
        finally:
            core.close()


if __name__=='__main__':main()

"""Run disposable checkpoint tooling controls with complete retained outcomes."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path
import argparse,json,sys,unittest
import checkpoint_core as c
import test_checkpoint_controls as controls

def ids(suite):
    out=[]
    for item in suite:
        out.extend(ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);args=p.parse_args();assert args.attempt.isdecimal()
    c.preparation_claim();output=c.W/('controls-r'+args.attempt);output.mkdir(exist_ok=False)
    suite=unittest.defaultTestLoader.loadTestsFromModule(controls);selected=ids(suite);assert len(selected)==len(set(selected))==73
    c.save(output/'START.json',dict(selected_ids=selected,test_count=len(selected),canonical_or_Git_mutation=False,scope='DISPOSABLE_CHECKPOINT_TOOLING_CONTROLS_ONLY'))
    with (output/'TESTS.log').open('x',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    outcome=dict(selected_ids=selected,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),failure_details=[dict(test_id=test.id(),traceback=trace) for test,trace in result.failures],error_details=[dict(test_id=test.id(),traceback=trace) for test,trace in result.errors],successful=result.wasSuccessful(),canonical_or_Git_mutation=False,product_tests=False,tested_sources={name:c.sha((c.W/name).read_bytes()) for name in ('checkpoint_core.py','assemble_checkpoint.py','run_prepare.py','verify_prepared.py','verify_publication.py','freeze_preparation.py','exact_git_scope.py','publish_checkpoint.py','test_checkpoint_controls.py','run_controls.py','prepare_checkpoint_successor.py','ARCHIVAL-WHITESPACE-POLICY.json')})
    c.save(output/'RESULT.json',outcome)
    if outcome['successful']:
        assert outcome['tests_run']==73 and outcome['failures']==outcome['errors']==outcome['skips']==0
        # Each attempt keeps its own immutable result; this current summary can advance only after a new complete pass.
        target=c.W/'CONTROLS-RESULT.json'
        if target.exists():
            previous=json.loads(target.read_bytes());assert any((root/'RESULT.json').is_file() and json.loads((root/'RESULT.json').read_bytes())==previous for root in c.W.glob('controls-r*')),'prior current summary is not retained'
            temporary=c.W/('CONTROLS-RESULT-'+args.attempt+'.tmp');c.save(temporary,outcome);__import__('os').replace(temporary,target)
        else:c.save(target,outcome)
    print(json.dumps(dict(output=str(output),tests_run=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors))))
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())

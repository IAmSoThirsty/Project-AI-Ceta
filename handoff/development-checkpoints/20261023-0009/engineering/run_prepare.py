"""One private preparation attempt; no canonical refs/index/object writes."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from datetime import datetime,timezone
import argparse,json,os,sys
import checkpoint_core as c

def prepare(final_pin):
    c.preparation_claim();c.load_final(final_pin);before=json.loads((c.W/'CANONICAL-BEFORE-0002.json').read_bytes());assert before['final_input_sha256']==final_pin
    module=c.engine();assert not (c.W/'prepared-0002').exists(),'private preparation already attempted; no replay'
    journal=(c.W/'PREPARATION-COMMANDS-0002.jsonl').open('xb');primary=None;secondary=[];sequence=0
    def audit(args,result):
        nonlocal sequence
        sequence+=1;entry=dict(sequence=sequence,at=datetime.now(timezone.utc).isoformat(),argv=result.args,exit_status=result.returncode,stdout_bytes=len(result.stdout),stdout_sha256=c.sha(result.stdout),stderr_bytes=len(result.stderr),stderr_sha256=c.sha(result.stderr),stdout=result.stdout.decode('utf8',errors='replace') if len(result.stdout)<65536 and args[0]!='cat-file' else 'EXACT_BYTES_RETAINED_IN_PRIVATE_OBJECTS_OR_HASH_ONLY',stderr=result.stderr.decode('utf8',errors='replace') if len(result.stderr)<65536 else 'HASH_ONLY; OVER_CAPTURE_BOUND')
        raw=(json.dumps(entry,allow_nan=False)+'\n').encode();written=journal.write(raw)
        if written!=len(raw):raise OSError('short preparation command journal write')
        journal.flush();os.fsync(journal.fileno())
    module.COMMAND_AUDITOR=audit
    try:outcome=module.prepare(c.W/'CHECKPOINT-INPUTS-0002.json')
    except BaseException:primary=sys.exc_info()
    finally:
        module.COMMAND_AUDITOR=None
        for action in (journal.flush,lambda:os.fsync(journal.fileno()),journal.close):
            try:action()
            except BaseException as error:secondary.append(error)
    if primary is not None:
        error=primary[1];storage=BaseException.__dict__['__dict__'].__get__(error);dict.__setitem__(storage,'checkpoint_secondary_errors',tuple(secondary));raise BaseException.with_traceback(error,primary[2])
    if secondary:raise secondary[0]
    c.save(c.W/'PRIVATE-PREPARATION-RESULT-0002.json',dict(actual_outcome=outcome,commands=sequence,final_input_sha256=final_pin,canonical_Git_writes=False,publication=False,full_product_acceptance=False));print(json.dumps(outcome))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--final-sha256',required=True);prepare(p.parse_args().final_sha256)

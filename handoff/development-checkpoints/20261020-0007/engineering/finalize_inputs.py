"""Finalize C7 only after an explicit Root publication-complete signal."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
from prepare_checkpoint import checkout_state, digest, git, save, stable_read
W = Path(__file__).resolve().parent
F = Path('T:/00-Active/Project-AI-CETA')
C6 = W.parent.parent / 'checkpoint-0006/work'
PARENT = '3ab94d8c11e3169eee85c9fbb3f53fd7c234871a'
PREFIX = 'handoff/development-checkpoints/20261020-0007/'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root-publication-signal', required=True)
    ap.add_argument('--signal-sha256', required=True)
    args = ap.parse_args()
    signal, signal_pin = stable_read(args.root_publication_signal)
    assert digest(signal) == args.signal_sha256
    assert not (W / 'CHECKPOINT-INPUTS.json').exists(), 'finalize is create-once'
    claim = json.loads((W.parent / 'control/implement-claim.json').read_bytes())['response']['claim']
    assert claim['executor_id'] == '/root/sol_discovery'
    assert claim['input_hash'] == '4b30af9ddf8f0bbbcc88d9a378366970b5779b1a725f8d07e6f60bcd5ff2606a'
    manifest = json.loads((W / 'SOURCE-MANIFEST.json').read_bytes())
    assert len(manifest['payload_hashes']) == manifest['payload_count'] == 559
    # The explicit Root message authorizes timing; these readbacks independently bind bytes.
    canonical = {}
    for rel, expected in manifest['payload_hashes'].items():
        raw, pin = stable_read(F / rel)
        assert digest(raw) == expected, ('canonical publication not exact', rel)
        assert digest((Path(manifest['candidate']) / rel).read_bytes()) == expected
        canonical[rel] = pin
    public = W / 'public'
    (public / 'ROOT-PUBLICATION-SIGNAL.json').write_bytes(signal)
    save(public / 'ROOT-PUBLICATION-SIGNAL-PROVENANCE.json', dict(source=args.root_publication_signal,
        source_pin=signal_pin, sha256=args.signal_sha256, scope='Root explicit signal;559 canonical bytes independently checked'))
    status = json.loads((C6 / 'public/STATUS.json').read_bytes())
    status.update(checkpoint_sequence=7, checkpoint_parent=PARENT,
        prepared_at=datetime.now(timezone.utc).isoformat(), source_payloads=559,
        source_manifest_sha256=digest((W / 'SOURCE-MANIFEST.json').read_bytes()),
        checkpoint_publication='NOT_RUN_PREPARED_FOR_DISTINCT_REVIEW',
        local_accepted_checkout='Fresh canonical source readback matches accepted effective J559;HEAD remains independent',
        local_canonical_source_changed=True, source_component_review='Accepted S1/S2/J source and C6 EOF repair;checkpoint review pending',
        active_owner_binding_and_operator_wiring='INCLUDED_ACCEPTED_J559',
        checkpoint_source_delta=dict(added=325,removed=10), checkpoint_test_delta=dict(added=618,removed=0),
        checkpoint_doc_delta=dict(added=46,removed=0), copied_loc=0,
        loc_method='SequenceMatcher unified line opcodes;ndiff323/-8 retained;same net315',
        current_native_execution=False,current_installed_qualification=False,
        root_canonical_publication_signal_sha256=args.signal_sha256,
        original_source_manifest_status_fields='Historical manifest flags preserved as history;fresh minimal source manifest used',
        authored_during_checkpoint_preparation=dict(product_source=0,product_test=0,engineering_source='Separate engineering files'),
        new_product_source_loc=325,new_product_test_loc=618,
        checkpoint_0006_completed=dict(commit=PARENT,evidence='RAW-EVIDENCE.zip/checkpoint-0006/control'))
    status.pop('publication_follow_up',None)
    status['open_issues'] = [x for x in status['open_issues'] if x != 'Owned service diagnostics and operator/CLI integration are not included in this checkpoint']
    status['open_issues'] += ['Latest full2622 run failed observer timeout;report aggregation KeyError separately repaired in13controlled checks;no later full acceptance',
        'Fresh full candidate/destination,installed,positive isolation,offline,endurance and human gates remain open',
        'New budget/observer timing work excluded from this reviewed source snapshot']
    status['verified_development'] += ['Accepted retained owned-service diagnostics binding and lazy delegation;137 joined controlled cases and6 independent checks',
        'Exact live operator CLI exercised ordinary owned Windows diagnostics with SQLite and owner retirement evidence;bounded qualification only',
        'Canonical559 product byte readback after Root publication;checkpoint preparation performs no canonical writes']
    status['preserved_failures'] += ['S1/S2/J historical failures including long fixture-path join failure','C7 initial LOC alignment assertion;source bytes unchanged']
    save(public / 'STATUS.json',status)
    (public / 'STATUS.md').write_text('# Project-AI: CETA development checkpoint 7\n\n'
        'Prepared descendant of checkpoint6 with559 accepted product payloads and the prior EOF repair. '
        'Source delta+325/-10 uses unified SequenceMatcher line opcodes;ndiff gives+323/-8 with the same net315. '
        'Tests+618/-0;docs+46/-0;copied LOC0. Checkpoint preparation authors no product code.\n\n'
        'Retained evidence includes S1/S2/J source reviews/gates/handoffs,historical failures,137 joined controlled tests,6 independent checks, '
        'and the exact live ordinary owned-service diagnostics CLI command/stdout/stderr/retirement proof. '
        'Root publication signal and an independent559-file canonical readback bind the source state. '
        'Preparation preserves the normal dirty checkout,index,refs,all parent paths/modes,PDF parts,five immutable fixtures and previous exports.\n\n'
        'The last broad run executed2622tests and failed an observer timeout;its reporting KeyError has a separate13-case controlled repair. '
        'Missing inner final resource files remain missing proof. Fresh full candidate/destination,positive isolation,installed,offline,endurance '
        'and human acceptance remain open. Historical native/failed receipts remain unchanged. New unreviewed budget/observer work, '
        'environments,caches,disposable SQLite,live coordinator state,secrets and the oversized originalPDF are excluded. '
        'This preparation does not publish,launch native processes,repair the T-volume or claim complete product acceptance.\n',encoding='utf-8')
    checkout = checkout_state(F)
    refs = git(F,['for-each-ref','--format=%(refname) %(objectname)']).decode().splitlines()
    for ref in ('refs/heads/development/checkpoints','refs/remotes/origin/development/checkpoints'):
        assert ref+' '+PARENT in refs
    git(F,['merge-base','--is-ancestor',checkout['head'],PARENT])
    save(W / 'CANONICAL-BEFORE.json',dict(checkout=checkout,normal_index_native=stable_read(F / '.git/index')[1],canonical_product_pins=canonical,refs=refs))
    save(W / 'PREPARE-LEASE-READBACK.json',claim)
    extras=[]
    for path in sorted(public.iterdir()):
        dest={'STATUS.json':'DEVELOPMENT-CHECKPOINT.json','STATUS.md':'DEVELOPMENT-CHECKPOINT.md'}.get(path.name,PREFIX+path.name)
        extras.append(dict(source=str(path),destination=dest,sha256=digest(path.read_bytes())))
    names=('prepare_checkpoint.py','publish_checkpoint.py','verify_prepared.py','assemble_stable_inputs.py',
        'finalize_inputs.py','audit_checkpoint.py','SOURCE-MANIFEST.json','TOOL-COPY-PINS.json','PRODUCT-LOC.json',
        'ASSEMBLY-COUNT-FAILURE.json','LOC-OBSERVATION.json','UNIFIED-LOC-OBSERVATION.json','PRODUCT-LOC.ndiff-r1.json',
        'assemble_stable_inputs.original-count-assumption.py')
    for name in names:
        path=W/name
        extras.append(dict(source=str(path),destination=PREFIX+'engineering/'+name,sha256=digest(path.read_bytes())))
    save(W / 'CHECKPOINT-INPUTS.json',dict(root=str(F),output=str(W/'prepared-0001'),
        expected_head=checkout['head'],expected_branch=checkout['branch'],expected_status_sha256=checkout['status_sha256'],
        origin=checkout['remote_fetch'],ref='refs/heads/development/checkpoints',parent=PARENT,
        manifest=str(W/'SOURCE-MANIFEST.json'),manifest_sha256=digest((W/'SOURCE-MANIFEST.json').read_bytes()),extra_exports=extras,
        message='Checkpoint accepted owned service diagnostics and operator integration\n\nPreserve exact J559 with C6 EOF repair,prior exports,PDF parts,fixtures and truthful scoped evidence. Development preservation;full product acceptance remains open.\n'))
    save(W/'EXPORT-SELECTION.json',dict(source_payloads=559,extra_exports=extras,canonical_readback='559 exact after Root signal',publication=False))
    print(json.dumps(dict(source_payloads=559,extra_exports=len(extras),checkout=checkout,publication=False)))
if __name__=='__main__': main()

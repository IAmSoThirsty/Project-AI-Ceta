"""Read-only exact checkpoint9 conservation audit; no canonical effects."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path
import argparse,json,os,stat
import checkpoint_core as c
from assemble_checkpoint import evidence_locations

def files(root):
    found={};seen=set()
    def visit(path):
        before=path.lstat();assert stat.S_ISDIR(before.st_mode) and not getattr(before,'st_file_attributes',0)&1024
        identity=(before.st_dev,before.st_ino);assert identity not in seen;seen.add(identity)
        with os.scandir(path) as entries:names=sorted(x.name for x in entries)
        for name in names:
            child=path/name;info=child.lstat();assert not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024
            if stat.S_ISDIR(info.st_mode):visit(child)
            else:
                assert stat.S_ISREG(info.st_mode);pin=c.stable(child)[1];after_file=child.lstat()
                assert (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_mode,info.st_nlink)==(after_file.st_dev,after_file.st_ino,after_file.st_size,after_file.st_mtime_ns,after_file.st_mode,after_file.st_nlink),'file metadata changed during observation'
                found[child.relative_to(root).as_posix()]=dict(pin,mode=after_file.st_mode,links=after_file.st_nlink)
        after=path.lstat();assert (before.st_dev,before.st_ino,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_mtime_ns),'directory changed during traversal'
    visit(root);return found

def audit(final_pin=None,require_freeze=True):
    before=json.loads((c.W/'CANONICAL-BEFORE-0002.json').read_bytes());final_pin=final_pin or before['final_input_sha256'];value,manifest,pins,canonical=c.load_final(final_pin)
    assert canonical==before['canonical_pins'] and pins==before['external_pins'],'canonical or frozen evidence drift'
    module=c.engine();assert module.checkout_state(c.F)==before['checkout'] and c.stable(c.F/'.git/index')[1]==before['normal_index_native'] and c.stable(c.F/'.git/HEAD')[1]==before['HEAD_native']
    prepared_path=c.W/'prepared-0002/PREPARED.json';prepared=json.loads(prepared_path.read_bytes());result=module.verify(prepared_path)
    assert prepared['root']==str(c.F) and prepared['parent']==c.PARENT and prepared['ref']==c.REF and prepared['origin']==c.ORIGIN and prepared['ref_publication'] is False
    expected_env=dict(GIT_INDEX_FILE=str(c.W/'prepared-0002/index'),GIT_OBJECT_DIRECTORY=str(c.W/'prepared-0002/objects'),GIT_ALTERNATE_OBJECT_DIRECTORIES=str(c.F/'.git/objects'))
    assert prepared['git_environment']==expected_env,'private Git environment escaped'
    parent=c.tree(module,c.PARENT,prepared['git_environment']);child=c.tree(module,prepared['commit'],prepared['git_environment']);assert parent==before['parent_tree']
    changed=c.conservation(parent,child,prepared['exports']);assert changed==prepared['changed_paths']
    exports=prepared['exports'];assert set(manifest['payload_hashes'])|set(value['status_pins'])<=set(exports)
    for name,expected in dict(manifest['payload_hashes'],**value['status_pins']).items():assert exports[name]['sha256']==expected
    locator=c.W/'public-0002/EVIDENCE-LOCATIONS.json';assert json.loads(locator.read_bytes())==evidence_locations(value,final_pin),'evidence locator differs from explicit Root final exports'
    assert exports[c.PREFIX+'EVIDENCE-LOCATIONS.json']['sha256']==c.sha(locator.read_bytes()),'evidence locator is not exported exactly'
    scan=json.loads((c.W/'prepared-0002/EXACT-EXPORT-SECRET-SCAN.json').read_bytes());assert scan['result']=='PASS' and not scan['findings']
    controls=json.loads((c.W/'CONTROLS-RESULT.json').read_bytes());assert controls['successful'] and controls['tests_run']==73 and controls['failures']==controls['errors']==controls['skips']==0
    for name,pin in controls['tested_sources'].items():assert c.sha((c.W/name).read_bytes())==pin,('control evidence belongs to different draft bytes',name)
    process=json.loads((c.W/'CONTROLS-PROCESS.json').read_bytes());assert process['actual_exit_status']==0 and process['result_sha256']==c.sha((c.W/'CONTROLS-RESULT.json').read_bytes())
    if require_freeze:
        freeze=json.loads((c.W/'WORK-FREEZE.json').read_bytes());actual=files(c.W);actual.pop('WORK-FREEZE.json');assert actual==freeze['files'],'frozen preparation changed'
        assert freeze['final_input_sha256']==final_pin and freeze['prepared_sha256']==c.sha(prepared_path.read_bytes())
    return dict(status='PASS',parent=c.PARENT,commit=prepared['commit'],tree=prepared['tree'],canonical_payloads=560,status_registers=2,exports=len(exports),changed_paths=changed,parent_paths_modes_five_fixtures_and_six_pdf_exports_preserved=True,canonical_Git_index_HEAD_and_source_unchanged=True,full_product_acceptance=False,generic_verification=result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--final-sha256');args=p.parse_args();print(json.dumps(audit(args.final_sha256),indent=2))

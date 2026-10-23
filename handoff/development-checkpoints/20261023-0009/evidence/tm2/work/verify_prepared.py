"""Integrity-only gate; imports no canonical product/test modules and runs no bodies."""
from pathlib import Path
import json
import run_challenge as r
W=r.W
pin=r.sha(W/'MANIFEST.json'); packet,binding,q=r.load_frozen(pin)
m=json.loads((W/'MANIFEST.json').read_bytes()); prep=json.loads((W/'PREPARATION.json').read_bytes())
fresh=q.source_observation(binding)
assert prep['source_before']==prep['source_after']==fresh
assert len(binding['source_native'])==562
assert prep['canonical_test_bodies_executed'] is False and prep['canonical_fixture_writes'] is False
assert r.prerequisite(binding)==prep['journal_success']
c=json.loads((W/'COLLECTION.json').read_bytes())
assert c['test_ids']==r.SELECTED and c['tests_collected']==1
assert c['ordinary_imports'] is True and c['module_overlay'] is False and c['ROOT_override'] is False
assert c['test_bodies_executed'] is False and c['canonical_fixture_writes'] is False
for identity in c['dependencies'].values():
    if identity['file']:assert q.stable(Path(identity['origin']))[0]==identity['native']
    if 'namespace' in identity:
        ns=identity['namespace']; path=Path(ns['path']); info=q.plain(path)
        assert path==r.F/'src/ceta/effects' and not (path/'__init__.py').exists()
        assert (info.st_dev,info.st_ino,info.st_mtime_ns)==(ns['device'],ns['inode'],ns['mtime_ns'])
assert q.stable(Path(c['sqlite_static_binary']['path']))[0]==c['sqlite_static_binary']['native']
assert c['sqlite_static_binary']['loaded_by_preparation'] is False
controls=json.loads((W/'controls-final/CONTROL-RESULT.json').read_bytes())
assert controls['tests_run']==20 and controls['failures']==controls['errors']==0 and controls['skips']==[] and controls['successful'] is True
assert controls['canonical_test_bodies_run']==controls['native_calls']==controls['clock_reads']==controls['source_imports']==0
for name,pin in m['current_controls_source'].items():assert r.sha(W/name)==pin
engine=json.loads((W/'engine-controls-stable/RESULT.json').read_bytes())
assert engine['successful'] is True and engine['tests_run']==8 and engine['failures']==engine['errors']==0
assert engine['canonical_test_bodies_executed'] is False
for name,pin in engine['tested_source'].items(): assert r.sha(W/name)==pin
for name in m['python_sources']:compile((W/name).read_bytes(),str(W/name),'exec')
assert m['canonical_tests_executed']==0 and m['full_product_acceptance'] is False
print('PREPARED PASS: one canonical ID collected only;20 observer and8 standalone custody controls;accepted actual JR2 success pinned;source560+2status/Git and complete work integrity unchanged;no canonical bodies or fixture writes;full acceptance false')

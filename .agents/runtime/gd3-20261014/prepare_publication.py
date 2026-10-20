"""Close actual-review and native-original identity checks before publication."""
import hashlib
from pathlib import Path

R = Path(__file__).resolve().parent
F = R.parents[2]
prior = F / '.agents/runtime/gd2-20261014/apply_reviewed_observation.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(prior) == 'f6a9dcbbada985fc5495c7af3b46c46039bcbd8c5c5fa668e39e1c4732230599'
text = prior.read_text().replace('gd2-20261014', 'gd3-20261014')
manifest_sha = sha(F / '.agents/gd3-20261014/TRANSFER-MANIFEST.json')
text = text.replace('cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a', manifest_sha)
text = text.replace('import os\n', 'import os\nimport sys\n', 1)
text = text.replace('def main():\n', '''def main():
    assert os.name == 'nt' and sys.flags.optimize == 0
    assert Path(sys.executable) == F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
''', 1)
marker = '    assert review["decision"] == "approved" and review["exit_status"] == 0\n'
assert marker in text
text = text.replace(marker, marker + '''    stored_review = read(R / RUN / 'receipts/review.json')
    assert review['executor_id'] != '/root'
    assert all(stored_review.get(key) == value for key, value in review.items()), 'Actual persisted review differs'
''', 1)
marker = '    manifest = read(manifest_path)\n'
assert marker in text
text = text.replace(marker, marker + '''    assert review['result']['manifest']['sha256'] == sha(manifest_path), 'Candidate review manifest differs'
    assert helper_review['manifest_sha256'] == sha(manifest_path), 'Helper review manifest differs'
    self_review = manifest['self_review']
    assert sha(F / self_review['repository_relative_path']) == self_review['sha256']
    initial_identities = {}
''', 1)
marker = '            selected.append(item)\n'
assert marker in text
text = text.replace(marker, '''            if item['active_before_sha256'] is not None:
                initial_identities[relative] = native.fs.file_identity(native.fs.lstat(target))
''' + marker, 1)
marker = '                facts = os.fstat(source.fileno())\n'
assert marker in text
text = text.replace(marker, marker + '''                assert native.fs.file_identity(facts) == initial_identities[relative], 'Original identity changed before preservation'
''', 1)
marker = '''            native.publish_prepared(OUT / "staged" / relative, F / relative,
                OUT / "native-backups" / (relative + ".original"), item["active_before_sha256"], item["candidate_sha256"])
'''
assert marker in text
text = text.replace(marker, '''            if item['active_before_sha256'] is not None:
                assert native.fs.file_identity(native.fs.lstat(F / relative)) == initial_identities[relative], 'Original identity changed before replacement'
''' + marker + '''            if item['active_before_sha256'] is not None:
                backup = OUT / 'native-backups' / (relative + '.original')
                with native.fs.open_source(native.fs.safe_components(backup), exclusive=True) as stream:
                    facts = os.fstat(stream.fileno())
                    digest = hashlib.sha256(stream.read()).hexdigest()
                assert digest == item['active_before_sha256']
                assert native.fs.file_identity(facts) == initial_identities[relative], 'Retained original identity differs'
            assert native.exact_hash(F / relative) == item['candidate_sha256']
''', 1)
marker = '        save(OUT / "APPLIED.json",'
assert marker in text
text = text.replace(marker, '''        for original in originals:
            relative = original['relative_path']
            with native.fs.open_source(native.fs.safe_components(OUT / 'native-backups' / (relative + '.original')), exclusive=True) as stream:
                facts = os.fstat(stream.fileno())
                assert hashlib.sha256(stream.read()).hexdigest() == original['sha256']
                assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
                    original['device'], original['inode'], original['mode'], original['bytes'], original['mtime_ns'])
''' + marker, 1)
target = R / 'apply_reviewed_observation.py'
compile(text, str(target), 'exec')
with target.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
print(sha(target))

import hashlib
from pathlib import Path

R = Path(__file__).resolve().parent
F = R.parents[2]
prior = F / '.agents/runtime/hd2-20261014/run_destination_full.py'
assert hashlib.sha256(prior.read_bytes()).hexdigest() == '1dd6f4c3f6cf15ddbdfb7bd23a884af8cf39dc75625200a3031628b54a63594e'
text = prior.read_text()
text = text.replace('R = S / ".agents/runtime/hd2-20261014/active-application"', 'R = S / ".agents/runtime/gd2-20261014/active-application"')
begin = text.index("base_path = S / '.agents/runtime/wa1-20261014")
end = text.index('cut_bindings =', begin)
binding = '''base_path = S / '.agents/runtime/hd2-20261014/active-application/destination-full-r1.json'
assert sha(base_path) == 'e7aa79e76d6277a719070e6fb573121bb230a0c297af0447b829d4d53f495057'
baseline = read(base_path)
assert baseline['exit_status'] == 0 and baseline['tests_run'] == 1281 and baseline['source_unchanged']
expected = dict(baseline['after_hashes'])
assert len(expected) == 279
cut_path = S / '.agents/gd2-20261014/TRANSFER-MANIFEST.json'
assert sha(cut_path) == 'cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a'
manifest = read(cut_path)
overridden = set()
for item in manifest['payloads']:
    relative = item['relative_path']
    if item['action'] in {'CREATE', 'EXTEND'}:
        overridden.add(relative)
    elif relative in expected:
        assert expected[relative] == item['candidate_sha256']
    assert sha(S / '.agents/gd2-20261014' / relative) == item['candidate_sha256']
    expected[relative] = item['candidate_sha256']
assert overridden == {'src/ceta/resource/diagnostics.py', 'contracts/PROCESS_DIAGNOSTICS_V1.md',
                      'tests/contract/test_process_observation_timing.py', 'tests/contract/test_process_observation_validation.py'}
assert len(expected) == 281
'''
text = text[:begin] + binding + text[end:]
text = text.replace('== 1281 and not any', '== 1326 and not any')
text = text.replace('except Exception as failure:', 'except BaseException as failure:')
target = R / 'run_destination_full.py'
compile(text, str(target), 'exec')
with target.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
print(hashlib.sha256(target.read_bytes()).hexdigest())

import hashlib
from pathlib import Path

R = Path(__file__).resolve().parent
F = R.parents[2]
prior = F / '.agents/runtime/gd2-20261014/claim_integration.py'
text = prior.read_text().replace('gd2-20261014', 'gd3-20261014')
for before, after in (
    ('cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a', 'bb070146f6516f928e2ead8e590436f853332e2393ce8fa2687655f3424f5239'),
    ('7f76cf5e45dd8726bbf66bbfb398651205a277bf7aa52141a3cbd688027ce98a', '6a85432d806638e98bfd9d4ad8cef3b0005af64869cd8c9301cc0acb40a3d614'),
    ('f6a9dcbbada985fc5495c7af3b46c46039bcbd8c5c5fa668e39e1c4732230599', '484ea60f883d91cfb3116285df48da2bad81f8a25a16a1720fb57c2b081192c7')):
    assert before in text
    text = text.replace(before, after)
marker = "assert all(stored.get(key) == value for key, value in review.items()), 'Strict review differs from actual persisted receipt'"
assert marker in text
text = text.replace(marker, "strict_keys = {'schema_version', 'run_id', 'node_id', 'executor_id', 'started_at', 'finished_at', 'input_hash', 'changed_files', 'result', 'commands', 'validations', 'exit_status', 'decision'}\nassert set(review) == strict_keys and set(stored) == strict_keys | {'git_baseline', 'observed_git', 'receipt_hash'}\n" + marker)
target = R / 'claim_integration.py'
compile(text, str(target), 'exec')
with target.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
print(hashlib.sha256(target.read_bytes()).hexdigest())

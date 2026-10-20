"""Retain the full Source runner and correct its normal-exit boundary."""
import hashlib
from pathlib import Path

R = Path(__file__).resolve().parent
F = R.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prior = F / '.agents/runtime/gd2-20261014/run_destination_full.py'
assert sha(prior) == 'ef459861f2044afb82223e7523e796e9842fddd6167dbe5eed69691697c80e1b'
text = prior.read_text().replace('gd2-20261014', 'gd3-20261014')
text = text.replace('cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a',
                    sha(F / '.agents/gd3-20261014/TRANSFER-MANIFEST.json'))
line = '    sys.exit(record["exit_status"])\n'
assert text.count(line) == 1
text = text.replace(line, '', 1)
assert text.endswith('    raise\n')
text += '\n# A normal completed exit must not enter the interruption failure handler.\nsys.exit(record["exit_status"])\n'
target = R / 'run_destination_full.py'
compile(text, str(target), 'exec')
with target.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
print(sha(target))

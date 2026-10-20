"""One read-only profile of the retained synthetic editor request's pure codec."""
from pathlib import Path
from datetime import datetime, timezone
import cProfile
import hashlib
import io
import json
import pstats
import sys
import time

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/er1-20261015'
V = F / '.agents/runtime/js2-20261015/direct-integration/independent-full'
sys.dont_write_bytecode = True


def ref(path):
    return {'repository_relative_path': path.relative_to(F).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    assert len(sys.argv) == 1
    assert not (R / 'CODEC-PROFILE-AFTER-R1.json').exists()
    failure = json.loads((V / 'EDITOR-FAILURE-READBACK-R1.json').read_bytes())
    assert len(failure['matched_failed_stimulus_requests']) == 1
    row = failure['matched_failed_stimulus_requests'][0]['request']
    path = Path(row['path'])
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256'] and len(raw) == row['bytes'] == 532455
    before = path.stat()
    sys.path.insert(0, str(Q / 'src'))
    from ceta.contracts.wire import RecordCodec, strict_loads
    from ceta.contracts.local_ipc import decode_message
    assert not any(name.startswith(('ceta.identity', 'ceta.store', 'ceta.kernel',
                                  'ceta.supervisor', 'ceta.composition')) for name in sys.modules)
    codec = RecordCodec(strict_loads((Q / 'contracts/schemas/records.schema.json').read_bytes()))
    profile = cProfile.Profile()
    started = time.perf_counter_ns()
    request = profile.runcall(decode_message, raw, codec)
    elapsed = time.perf_counter_ns() - started
    assert request.operation == 'task.editor_retain'
    old_db = json.loads((V / 'EDITOR-DB-READBACK-R1.json').read_bytes())
    stored = [row['value'] for row in old_db['cells'] if row.get('value', {}).get('state') == 'STAGING']
    assert len(stored) == 1 and request.record.record_id == stored[0]['request_id']
    assert request.record.commitment == stored[0]['request_commitment']
    assert path.stat() == before and path.read_bytes() == raw
    report = io.StringIO()
    stats = pstats.Stats(profile, stream=report).sort_stats('cumulative')
    stats.print_stats(30)
    text_path = R / 'CODEC-PROFILE-AFTER-R1.txt'
    with text_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(report.getvalue())
    modules = {name: ref(Path(module.__file__)) for name, module in sys.modules.items()
               if name.startswith('ceta.') and getattr(module, '__file__', None)}
    assert all(Path(item['repository_relative_path']).as_posix().startswith('.agents/er1-20261015/src/ceta/contracts/')
               for item in modules.values())
    result = {'at': datetime.now(timezone.utc).isoformat(), 'executor': '/root',
        'request': ref(path), 'request_bytes': len(raw), 'elapsed_ns': elapsed,
        'historical_committed_request_id': request.record.record_id,
        'historical_committed_request_commitment': request.record.commitment,
        'exact_historical_request_binding_preserved': True,
        'profiling_overhead_included': True, 'calls': stats.total_calls,
        'profile': ref(text_path), 'imported_pure_modules': modules,
        'classification': 'One observed pure decode call on retained synthetic input; no end-to-end timeout causality or performance acceptance claim',
        'product_source_changes': 0, 'worker_processes_launched': 0,
        'authority_calls': 0, 'old_fixture_mutations': 0, 'Source_publication': False}
    with (R / 'CODEC-PROFILE-AFTER-R1.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'elapsed_ns': elapsed, 'calls': stats.total_calls,
                      'proof': ref(R / 'CODEC-PROFILE-AFTER-R1.json')}))


if __name__ == '__main__':
    main()

"""Freeze independent ER1 destination review and finite completion-helper inspection."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import importlib.metadata
import io
import json
import os
import sys
import zipfile

O = Path(__file__).resolve().parent
R = O.parent
F = R.parents[2]
Q = F / '.agents/er1-20261014'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
assert Path(sys.executable) == E3 / 'Scripts/python.exe' and sys.flags.optimize == 0
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
now = lambda: datetime.now(timezone.utc).isoformat()

def write_new(path, value):
    assert Path(path).is_relative_to(O)
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

proof_path = O / 'independent-verification.json'
assert sha(proof_path) == 'c9a62c401e6dff0f5a0fcc778062193c41b41b042cba56f0c13ca21ee3e2a75a'
proof = read(proof_path)
assert proof['exit_status'] == 0
assert proof['independent_safe_cli_invocations'] == 5
assert proof['source_before'] == proof['source_after'] and proof['candidate_before'] == proof['candidate_after']
assert len(proof['expected_environment_files']) == 3601
assert len(proof['payload_observations']) == 30
assert all(row['oracle_passed'] and row['observed_empty_job'] and row['owner_closed'] for row in proof['commands'])
generation = read(R / 'candidate-generation.json')
inventory = {row['filename']: row for row in read(R / 'launcher-inventory-r2.json')['launchers']}
zip_metadata = []
for row in generation['launchers']:
    old = (F / row['before_image']['repository_relative_path']).read_bytes()
    current = (E3 / row['source_relative_path']).read_bytes()
    assert sha(E3 / row['source_relative_path']) == row['candidate']['sha256']
    n = inventory[row['filename']]['stub_bytes']
    old_end = old.index(b'\n', n) + 1
    new_end = current.index(b'\n', n) + 1
    a, b = old[old_end:], current[new_end:]
    with zipfile.ZipFile(io.BytesIO(a)) as za, zipfile.ZipFile(io.BytesIO(b)) as zb:
        ia, ib = za.getinfo('__main__.py'), zb.getinfo('__main__.py')
        assert za.namelist() == zb.namelist() == ['__main__.py']
        assert za.read('__main__.py') == zb.read('__main__.py')
        assert len(a) == len(b) and za.start_dir == zb.start_dir
        fields = ('filename', 'compress_type', 'CRC', 'compress_size', 'file_size', 'flag_bits', 'create_system',
            'create_version', 'extract_version', 'volume', 'internal_attr', 'external_attr', 'extra', 'comment', 'header_offset')
        assert all(getattr(ia, field) == getattr(ib, field) for field in fields)
        assert za.comment == zb.comment
        changed = [index for index, (x, y) in enumerate(zip(a, b)) if x != y]
        timestamp_positions = set(range(ia.header_offset + 10, ia.header_offset + 14)) | set(range(za.start_dir + 12, za.start_dir + 16))
        assert changed and set(changed) <= timestamp_positions, (row['filename'], changed)
        zip_metadata.append({'filename': row['filename'], 'old_member_DOS_date_time': list(ia.date_time),
            'new_member_DOS_date_time': list(ib.date_time), 'zip_tail_bytes': len(a), 'changed_tail_byte_offsets': changed,
            'tail_differences_confined_to_local_and_central_DOS_timestamp_fields': True,
            'compressed_payload_attributes_extra_comment_and_structure_exact': True})
assert len(zip_metadata) == 27
try:
    metadata_version = importlib.metadata.version('PySide6')
    metadata_fact = {'distribution': 'PySide6', 'available': True, 'version': metadata_version}
except importlib.metadata.PackageNotFoundError:
    metadata_fact = {'distribution': 'PySide6', 'available': False, 'error_type': 'PackageNotFoundError',
        'qualification': 'Aggregate metadata unavailable; installed Essentials and callable module bytes were separately observed'}
write_new(O / 'packaging-and-metadata-observation.json', {'executor': '/root/pressure_review', 'observed_at': now(),
    'zip_metadata': zip_metadata, 'PySide6_aggregate_metadata': metadata_fact, 'exit_status': 0})

completion_path = R / 'complete_destination.py'
completion_sha = sha(completion_path)
assert completion_sha == '7ad8079b74e1ceea8bf53e158248d5338c48791e2594dfa7946898091ad943fa'
completion_text = completion_path.read_text(encoding='utf-8')
tree = ast.parse(completion_text)
assert len([node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'validate_receipt']) == 1
assert "_snapshot_workspace(E3, Path('T:/'))" in completion_text
assert "changed == sorted((E3 / relative).relative_to(Path('T:/')).as_posix() for relative in allowed)" in completion_text
assert "completion_review['completion_script_sha256'] == sha(Path(__file__))" in completion_text
assert "expected == review['expected_environment_files']" in completion_text
assert "assert not read(R / RUN / 'claims.json')" in completion_text
write_new(O / 'completion-helper-review.json', {'schema_version': 1, 'reviewer': '/root/pressure_review', 'reviewed_at': now(),
    'decision': 'approved', 'exit_status': 0, 'completion_script_sha256': completion_sha,
    'manifest_sha256': proof['pins']['manifest']['sha256'], 'application_journal_sha256': proof['pins']['journal']['sha256'],
    'destination_verification_sha256': proof['pins']['root_verification']['sha256'],
    'independent_verification_sha256': sha(proof_path),
    'personally_inspected': [
        'Exact Root/E3 integrate claim, manifest, journal input, candidate review, publisher approval and verifier code/result pins',
        'Approved independent destination review required, expected3601 rows joined and independent native CLI count at least5',
        'Fresh3601 ordinary-file census must equal exact current published and independent expectations',
        'Every30 actual target/candidate hash and native/logical original byte/hash/device/inode/full handle mode/size/mtime binding rechecked',
        'Real installed E3 snapshot must show exactly sorted30 manifest changed paths against actual claim baseline',
        'Strict installed validator validates real receipt before new exclusive integrate.json creation',
        'Installed actual complete command must exit0 with allowed=true; actual all6 SUCCEEDED and claims{} then required for acceptance readback',
        'All output paths are coordinator-owned runtime files; no completion helper product/environment mutation'
    ],
    'execution_status': 'STATIC_INSPECTION_ONLY_NOT_EXECUTED_BY_REVIEWER',
    'required_invocation': [str(E3 / 'Scripts/python.exe'), '-B', '-X', 'utf8', str(completion_path)],
    'limitations': ['Root owns actual completion and real installed runtime transitions; this approval makes no claim they have occurred',
        'Normal nonoptimized direct E3 Python invocation with bytecode writes disabled required',
        'Shared administrator and controlled coordinator paths; endpoint observations do not establish continuous privileged-principal custody',
        '23 Qt tool functions unexecuted; aggregate PySide6 metadata and directory allocation-size observation limits remain explicit']})

manifest = read(Q / 'TRANSFER-MANIFEST.json')
prior = []
for entry in manifest['prior_failures']:
    path = F / entry['repository_relative_path']
    assert sha(path) == entry['sha256']
    prior.append({**entry, 'current_hash_reproduced': True, 'historical_failure_not_reexecuted_in_this_job': True})
for entry in read(R / 'independent-review/publication-helper-review.json')['prior_rejected_helpers']:
    assert sha(F / entry['repository_relative_path']) == entry['sha256']
    prior.append({**entry, 'current_hash_reproduced': True, 'historical_failure_not_reexecuted_in_this_job': True})
own_commands = proof['commands']
for row in own_commands:
    fixture = Path(row['fixture'])
    assert fixture.is_relative_to(O)
    assert sha(fixture / 'stdout.bin') == row['stdout_sha256'] and sha(fixture / 'stderr.bin') == row['stderr_sha256']
    assert read(fixture / 'receipt.json') == row
assert (O / 'independent-execution.stderr.txt').stat().st_size == 0
review = {'schema_version': 1, 'executor': '/root/pressure_review', 'reviewed_at': now(), 'decision': 'approved', 'exit_status': 0,
    'source_root': str(F), 'environment_root': str(E3), 'manifest_sha256': proof['pins']['manifest']['sha256'],
    'application_journal_sha256': proof['pins']['journal']['sha256'], 'destination_verification_sha256': proof['pins']['root_verification']['sha256'],
    'independent_safe_cli_invocations': 5, 'expected_environment_files': proof['expected_environment_files'],
    'ordinary_environment_files': 3601, 'unrelated_ordinary_files_preserved': 3571, 'native_originals': 30,
    'callable_imports': 27, 'Qt_tools_unexecuted': 23, 'independent_verification_sha256': sha(proof_path),
    'completion_helper_review_sha256': sha(O / 'completion-helper-review.json'),
    'verification_helper_review_sha256': sha(O / 'verification-helper-review.json'),
    'packaging_observation_sha256': sha(O / 'packaging-and-metadata-observation.json'),
    'command_argv': [str(E3 / 'Scripts/python.exe'), '-B', '-X', 'utf8', str(O / 'verify_actual_destination.py')],
    'raw_stdout_sha256': sha(O / 'independent-execution.stdout.txt'), 'raw_stderr_sha256': sha(O / 'independent-execution.stderr.txt'),
    'independently_reproduced': [
        'All30 active native replacements equal frozen candidate hashes/bytes; exactly27 launchers and3 RECORD files',
        'All30 native originals retain original device/inode/full native handle mode/size/mtime and bytes; logical/author originals match bytes',
        'Fresh independent before/after censuses each rehash all3601 ordinary files; all3571 untouched rows equal original hash/native identity',
        'Every27 native stub and decoded __main__.py body byte-exact; current interpreter shebang exact; PE x8664 console',
        'All27 rebuilt ZIP tails differ only in local/central DOS timestamp fields; payload and all other tail bytes exact',
        'Exactly27 authorized RECORD hash/size rows changed across3 files; all other raw lines, path text, quoting, order and endings preserved',
        'All27 installed entry points resolve to actual callable modules under current E3 site-packages;23 Qt functions not invoked',
        'Three own actual pip alias version calls exit0 and bind current pip25.0.1/Python3.12/current E3 path',
        'Own actual schema valid fixture exit0; invalid fixture expected exit1 with actual type-error diagnostic',
        'All5 own actual Windows jobs observed empty before owner close; PID/creation/image/time/raw receipts preserved',
        'Current279 Source payload hashes/native identities and all33 frozen candidate file observations unchanged',
        'Aggregate PySide6 metadata absence queried independently',
        'Root5 stored raw stream hashes and receipts/current images reproduced; its claimed closure facts distinguished from own execution'
    ],
    'inspected_only': ['Historical author seven-case and candidate ten-case test runs were inspected through pinned receipts and not rerun in this destination job',
        'Root publisher native30 replacement execution inspected through immutable applied journal/originals; reviewer performed no replacement',
        'Root destination job process closure facts inspected; reviewer independently observed its own five distinct jobs',
        'Actual TAAR integrate completion and all6 SUCCEEDED readback are Root next actions and were not executed by this reviewer'],
    'commands': [{key: row[key] for key in ('label', 'command_argv', 'pid', 'creation_time_100ns', 'started_at', 'finished_at',
        'expected_exit_status', 'actual_exit_status', 'owner_closed', 'observed_empty_job', 'stdout_sha256', 'stderr_sha256')} for row in own_commands],
    'actual_root_integrate_claim': proof['actual_root_claim'], 'prior_failures_preserved': prior,
    'existing_issues': [
        {'issue': '23 Qt tool functions operational execution unverified', 'classification': 'requires separate follow-up work'},
        {'issue': 'Aggregate PySide6 distribution metadata unavailable', 'classification': 'environment/dependency issue'},
        {'issue': 'jsonschema CLI emits an actual deprecation warning on both current safe calls', 'classification': 'not blocking current task'},
        {'issue': 'Directory stat allocation-size variation OS-internal cause unresolved', 'classification': 'not blocking current task'},
        {'issue': 'Thirty replacements have individual native publication; interrupted group requires exact-path reconciliation', 'classification': 'not blocking current task'}],
    'limits': proof['limitations'] + ['Review approval qualifies this exact applied environment repair; no product shipment or whole-system completion claim',
        'Administrative same-principal access remains shared; no isolated trust boundary or continuous environment custody claim',
        'Executable launcher archive timestamps changed during standard regeneration; source stub/body reuse does not mean whole-file byte identity'],
    'source_changes_by_reviewer': [], 'environment_changes_by_reviewer': [], 'external_operations_replayed': False,
    'scope_release': {'completed_own_native_jobs': 5, 'unresolved_owned_jobs': 0, 'fixture_root': proof['native_fixture_root'],
        'disposition': 'Fresh owned fixtures retained; all child jobs empty/closed, no Source/candidate/runtime transitions performed'}}
write_new(O / 'destination-review.json', review)
report = f"""ER1 actual environment destination review — approved

Reviewer: /root/pressure_review
Observed window: {proof['started_at']} through {proof['finished_at']}
Environment: {E3}
Source: {F}

The independent execution returned0. Every one of the30 applied paths matches its frozen candidate, and every native original matches original bytes/device/inode/handle-mode/size/mtime. Two fresh censuses rehashed all3601 ordinary files and found all3571 unaffected members unchanged. The279 accepted Source payloads and33 frozen candidate files also stayed exact.

The27 native launcher stubs and decoded main scripts are byte-exact. Current-interpreter shebangs are exact. Standard ScriptMaker regeneration additionally changed local/central ZIP DOS timestamp fields; an independent raw-tail comparison verified every other ZIP-tail byte and decoded payload unchanged. Across the3 RECORD files, precisely27 declared hash/size rows changed and every other raw line was preserved.

All27 installed entry points resolve to callable modules under E3. Five independently owned native CLI cases passed: pip/pip3/pip3.12 version calls, schema valid exit0, and schema invalid expected exit1 with a real type-error diagnostic. All five jobs were observed empty before close. Raw streams, command arguments, PID/creation times, image hashes and fixture paths are retained in the independent proof. The schema CLI also emits a deprecation warning; that is a current dependency warning, not a test failure. The23 Qt tool functions were never invoked.

The Root five-case destination result was personally inspected and its raw file hashes/current images reproduced. Historical author/candidate tests are pinned inspected evidence. This reviewer did not execute the30 native replacements, activate policy, replay external captures, change Source/E3, or perform actual TAAR completion. The Root completion helper was statically approved for its exact SHA after inspection of current claim/receipt/file/native-original guards and real installed changed-path snapshot.

Unresolved limits: Qt tool execution, unavailable aggregate PySide6 distribution metadata, directory allocation-size observation cause, continuous privileged-principal custody, and non-group-atomic publication recovery. This approved review applies to the exact environment repair only.

Manifest SHA: {review['manifest_sha256']}
Applied journal SHA: {review['application_journal_sha256']}
Root destination verification SHA: {review['destination_verification_sha256']}
Independent proof SHA: {review['independent_verification_sha256']}
Standalone review SHA: {sha(O / 'destination-review.json')}
Completion-helper approval SHA: {review['completion_helper_review_sha256']}
"""
with (O / 'REPORT.md').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(report)
print(json.dumps({'decision': 'approved', 'destination_review_sha256': sha(O / 'destination-review.json'),
    'completion_helper_review_sha256': sha(O / 'completion-helper-review.json'), 'report_sha256': sha(O / 'REPORT.md'),
    'packaging_sha256': sha(O / 'packaging-and-metadata-observation.json')}), flush=True)

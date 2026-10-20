"""Adapt the retained native publication helper to this exact four-path cut."""
import hashlib
from pathlib import Path

R = Path(__file__).resolve().parent
F = R.parents[2]
prior = F / '.agents/runtime/gd1-20261014/apply_reviewed_timing.py'
assert hashlib.sha256(prior.read_bytes()).hexdigest() == '764b2c29331e177303923ea68d05956ec1a520efa7e6bbefb3565033d991d000'
text = prior.read_text()
text = text.replace('three reviewed process-observation timing paths', 'four reviewed process-observation timing and validation paths')
text = text.replace('gd1-20261014', 'gd2-20261014')
text = text.replace('"tests/contract/test_process_observation_timing.py", "contracts/PROCESS_DIAGNOSTICS_V1.md"',
                    '"tests/contract/test_process_observation_timing.py", "tests/contract/test_process_observation_validation.py", "contracts/PROCESS_DIAGNOSTICS_V1.md"')
text = text.replace('3f64c0dca1637ef58d6eb5bd2c64809d9af48c2c1fb691f6d558b15047cbf9b3',
                    'cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a')
text = text.replace('len(manifest["payloads"]) == 280', 'len(manifest["payloads"]) == 281')
text = text.replace('sum(item["action"] == "CREATE" for item in selected) == 1', 'sum(item["action"] == "CREATE" for item in selected) == 2')
text = text.replace('THREE_PROCESS_TIMING_PATHS_APPLIED', 'FOUR_PROCESS_OBSERVATION_PATHS_APPLIED')
text = text.replace('exact three paths', 'exact four paths')
text = text.replace('except Exception as error:', 'except BaseException as error:')
old = '''        save(OUT / "FAILED.json", {**started, "completed": completed,
            "failed_at": datetime.now(timezone.utc).isoformat(), "error_type": type(error).__name__, "error": str(error),
            "recovery": "Preserve targets, stages, logical/native originals and reconcile exact four paths under fresh review"})
        raise'''
new = '''        try:
            save(OUT / "FAILED.json", {**started, "completed": completed,
                "failed_at": datetime.now(timezone.utc).isoformat(), "error_type": type(error).__name__, "error": str(error),
                "recovery": "Preserve targets, stages, logical/native originals and reconcile exact four paths under fresh review"})
        except BaseException as journal_error:
            error.add_note("Publication failure journal could not be written: " + type(journal_error).__name__)
        raise'''
assert old in text
text = text.replace(old, new)
target = R / 'apply_reviewed_observation.py'
compile(text, str(target), 'exec')
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
print(hashlib.sha256(target.read_bytes()).hexdigest())

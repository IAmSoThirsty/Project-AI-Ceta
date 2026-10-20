"""Read-only verification of the final exact V2 derivation and frozen tools."""
from pathlib import Path
import json
import derive_v2 as d
W=Path(__file__).resolve().parent
manifest=d.parse(d.read(W/'FROZEN.json')[0])
d.require(manifest.get('kind')=='CETA_SYMBOL_V2_DERIVATION_FREEZE_V1','FREEZE_KIND_REQUIRED')
files=manifest['files'];d.require(type(files) is dict and files,'FROZEN_FILES_REQUIRED')
for relative,expected in files.items():
    d.safe_relative(relative);raw,_=d.read(W/relative)
    d.require(d.sha(raw)==expected,'FROZEN_DERIVATION_FILE_CHANGED:'+relative)
result=d.verify(W/'CETA_OWNED_LOADER_SYMBOL_INPUTS_V2.json')
print(json.dumps(dict(status='PASS_FROZEN_V2_DATA',frozen_payloads=len(files),derivation=result,protected_effects_authorized=False),indent=2))

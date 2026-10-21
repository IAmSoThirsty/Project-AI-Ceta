from pathlib import Path
import json
from prepare_checkpoint import verify
print(json.dumps(verify(Path(__file__).resolve().parent/'prepared-0001/PREPARED.json'),indent=2))

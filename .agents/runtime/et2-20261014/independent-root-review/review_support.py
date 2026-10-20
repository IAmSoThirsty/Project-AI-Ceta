from pathlib import Path
import sys
F=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(F/'.agents/runtime/et2-20261014'))
from et_support import *
Q=F/'.agents/runtime/et2-20261014/independent-root-review/replica'
R=F/'.agents/runtime/et2-20261014/independent-root-review'
ACTOR='/root'

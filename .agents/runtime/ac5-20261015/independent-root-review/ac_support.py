from pathlib import Path
import sys
F=P=Path('T:/00-Active/Project-AI-CETA')
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'))
import en1_support as s
s.Q=F/'.agents/ac5-20261015'
s.R=F/'.agents/runtime/ac5-20261015/independent-root-review'
from en1_support import *
F=P
ACTOR='/root'

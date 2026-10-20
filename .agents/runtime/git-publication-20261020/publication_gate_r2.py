"""Actual TAAR successor for exact original-byte Git publication."""
from pathlib import Path
import importlib.util
F=Path("T:/00-Active/Project-AI-CETA")
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("original_publication",R/"publication_gate.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
c=m.c
c.R=R/"control-r2"
c.RUN="ceta-git-publication-20261020-r2"
c.EMPTY=F/".git"

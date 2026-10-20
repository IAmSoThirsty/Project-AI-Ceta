"""Reuse inspected AC2 native test infrastructure; Root evidence root only."""
from pathlib import Path
import importlib.util, sys
author_path = Path(__file__).resolve().parent.parent / 'ac2_support.py'
spec = importlib.util.spec_from_file_location('ac2_root_reused_support', author_path)
support = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = support
spec.loader.exec_module(support)
globals().update({key: value for key, value in vars(support).items() if not key.startswith('_')})
R = D = Path(__file__).resolve().parent
ACTOR = '/root'

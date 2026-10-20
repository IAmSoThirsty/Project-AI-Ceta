"""Explicit installed Git/Windows tool search; no inherited ambient PATH."""
from pathlib import Path
import json,os,shutil

D=Path(__file__).resolve().parent


def environment(temporary):
    value=json.loads((D/'GIT-SEARCH-DEPENDENCY.json').read_text(encoding='utf-8'))
    return {'SystemRoot':value['SystemRoot'],'PATH':value['PATH'],
        'TEMP':str(temporary),'TMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1'}


def verify_tools(ordinary):
    value=json.loads((D/'GIT-SEARCH-DEPENDENCY.json').read_text(encoding='utf-8'))
    assert ordinary(Path(value['git']['path']))==value['git']
    assert Path(value['SystemRoot']).is_dir() and Path(value['system32']).is_dir()
    assert value['PATH']==str(Path(value['git']['path']).parent)+';'+value['system32']
    assert Path(shutil.which('git.exe',path=value['PATH']))==Path(value['git']['path'])
    return value

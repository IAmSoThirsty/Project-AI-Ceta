from pathlib import Path
p=Path('T:\\00-Active\\Project-AI-CETA\\.agents\\runtime\\ac2-20261014\\profile-tool-repair-r2\\test_profile_qualification_r2.py')
raw=Path('T:\\00-Active\\Project-AI-CETA\\.agents\\runtime\\ac2-20261014\\profile-tool-repair-r2\\independent-root-review\\adapted-tests.py').read_bytes()
exec(compile(raw,str(p),"exec"),{"__file__":str(p),"__name__":"__main__"})

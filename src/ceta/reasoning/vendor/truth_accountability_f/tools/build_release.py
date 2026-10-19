"""Stable source ZIP builder; call after finalizing release audit and tests.

No automatic GitHub upload and no mutation of any Societal Version 1 archive.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SKIP={'__pycache__','.pytest_cache','.ruff_cache','.git','SHA256SUMS.txt'}


def release_members() -> list[Path]:
    found=[]
    for p in ROOT.rglob('*'):
        if p.is_symlink():
            raise RuntimeError('Release tree symlink forbidden')
        if not p.is_file():
            continue
        if any(part in SKIP for part in p.relative_to(ROOT).parts):
            continue
        if p.suffix in {'.pyc','.pyo'}:
            continue
        found.append(p)
    return sorted(found, key=lambda f:f.relative_to(ROOT).as_posix())


def build(destination:Path) -> tuple[str,int]:
    paths=release_members()
    lines=[]
    for p in paths:
        rel=p.relative_to(ROOT).as_posix()
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f'{digest}  {rel}')
    sums='\n'.join(lines)+'\n'
    (ROOT/'SHA256SUMS.txt').write_text(sums,encoding='utf-8')
    paths=sorted(paths+[ROOT/'SHA256SUMS.txt'],key=lambda f:f.relative_to(ROOT).as_posix())
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in paths:
            rel='truth-accountability-reference/'+p.relative_to(ROOT).as_posix()
            info=zipfile.ZipInfo(rel,(1980,1,1,0,0,0))
            info.create_system=3
            info.external_attr=(0o100644<<16)
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        corrupt=archive.testzip()
        if corrupt:
            raise RuntimeError(f'Corrupt archive member: {corrupt}')
        for p in paths:
            rel='truth-accountability-reference/'+p.relative_to(ROOT).as_posix()
            if archive.read(rel)!=p.read_bytes():
                raise RuntimeError(f'Packaged content mismatch: {rel}')
    hashhex=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix+'.sha256').write_text(f'{hashhex}  {destination.name}\n',encoding='ascii')
    return hashhex,len(paths)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    digest,count=build(args.output)
    print(f'{args.output}: files={count} sha256={digest}')

if __name__=='__main__':main()

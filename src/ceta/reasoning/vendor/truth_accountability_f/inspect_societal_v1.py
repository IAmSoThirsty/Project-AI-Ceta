"""Read-only Version 1 source inspection. Does not execute source code."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from truth_accountability import CorpusMapping, Version1ReadOnlyAdapter


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path,help="Local owner-supplied Version 1 ZIP or source folder")
    p.add_argument("--mapping",type=Path,help="Explicit owner-reviewed JSONL field mapping")
    p.add_argument("--expected-sha256",type=str)
    p.add_argument("--report",type=Path)
    args=p.parse_args(argv)
    try:
        spec=CorpusMapping(**json.loads(args.mapping.read_text(encoding="utf-8"))) if args.mapping else None
        adapter=Version1ReadOnlyAdapter(args.source,mapping=spec,expected_zip_sha256=args.expected_sha256)
        outcome=adapter.inspect()
        payload=json.dumps(outcome.__dict__,ensure_ascii=False,indent=2)+"\n"
    except (ValueError,TypeError,OSError,RuntimeError) as e:
        print("SOURCE_INSPECTION_FAILED:",type(e).__name__,str(e),file=sys.stderr)
        return 2
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(payload,encoding="utf-8")
    print(payload,end="")
    return 0


if __name__=="__main__":
    raise SystemExit(main())

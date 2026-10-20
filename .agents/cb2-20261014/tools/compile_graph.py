"""Compile explicitly selected graph fragments into inspectable pending nodes.

No directory discovery, worker launch, graph claim or status promotion occurs.
An optional output is exclusively created; existing files are never replaced.
"""
import argparse
import hashlib
import os
from pathlib import Path
import stat
import sys

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRODUCT_ROOT / "src"))

from ceta.contracts.graphs import GraphScopeCeiling, GraphSource, graph_path
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.orchestration.graph import GraphCompiler


def _fail(code):
    raise ContractError(code)


def _root(path):
    if not path.is_absolute():
        _fail("GRAPH_CLI_ABSOLUTE_ROOT_REQUIRED")
    root = path.resolve(strict=True)
    if root != path or not root.is_dir():
        _fail("GRAPH_CLI_ROOT_ALIAS")
    for item in (root, *root.parents):
        if item.is_symlink() or item.is_junction():
            _fail("GRAPH_CLI_ROOT_LINK")
    return root


def _selected(root, relative):
    graph_path(relative)
    current = root
    for part in relative.split("/"):
        current /= part
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or current.is_junction():
            _fail("GRAPH_CLI_SOURCE_LINK")
    resolved = current.resolve(strict=True)
    if str(resolved) != str(current) or not resolved.is_relative_to(root):
        _fail("GRAPH_CLI_SOURCE_ALIAS")
    return current


def _read(path):
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 1024 * 1024:
        _fail("GRAPH_CLI_INPUT_BOUND_OR_ALIAS")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(1024 * 1024 + 1)
        final_opened = os.fstat(stream.fileno())
    after = path.stat()
    key = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if key(before) != key(opened) or key(opened) != key(final_opened) or key(final_opened) != key(after) \
            or len(raw) != before.st_size:
        _fail("GRAPH_CLI_INPUT_CHANGED")
    return raw


def compile_selected(root, *, graph_id, scope_id, ceiling_path, fragment_paths):
    """Use actual retained source bytes and recheck all reads before returning."""
    root = _root(Path(root))
    if type(fragment_paths) is not tuple or not 1 <= len(fragment_paths) <= 64:
        _fail("GRAPH_CLI_SOURCE_COUNT")
    if len({item.casefold() for item in (ceiling_path, *fragment_paths)}) != 1 + len(fragment_paths):
        _fail("GRAPH_CLI_DUPLICATE_INPUT")
    selected = {name: _selected(root, name) for name in (ceiling_path, *fragment_paths)}
    before = {name: _read(path) for name, path in selected.items()}
    schema_path = PRODUCT_ROOT / "contracts/schemas/records.schema.json"
    schema_raw = _read(schema_path)
    compiler = GraphCompiler(RecordCodec(strict_loads(schema_raw)))
    ceiling = GraphScopeCeiling.capture(scope_id, strict_loads(before[ceiling_path]))
    result = compiler.compile(tuple(GraphSource(name, before[name]) for name in fragment_paths),
        graph_id=graph_id, scope_ceiling=ceiling)
    compiler.validate(result)
    for name, path in selected.items():
        if _selected(root, name) != path or _read(path) != before[name]:
            _fail("GRAPH_CLI_INPUT_CHANGED")
    if _read(schema_path) != schema_raw:
        _fail("GRAPH_CLI_SCHEMA_CHANGED")
    return {"profile": "ceta-graph-compilation-receipt-v1", "graph_fingerprint": result.fingerprint,
        "definition": strict_loads(result.definition_wire),
        "plan_nodes": [strict_loads(raw) for raw in result.plan_node_wires],
        "input_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in before.items()},
        "schema_sha256": hashlib.sha256(schema_raw).hexdigest(),
        "compilation": "VALID", "canonical_runtime_state": "NOT_CREATED",
        "qualification": "UNQUALIFIED", "admission": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--graph-id", required=True)
    parser.add_argument("--scope-id", required=True)
    parser.add_argument("--ceiling", required=True, help="Explicit relative JSON resource ceiling")
    parser.add_argument("--fragment", action="append", required=True, help="Explicit relative graph fragment, in override order")
    parser.add_argument("--output", help="New relative output file beneath root; otherwise stdout")
    args = parser.parse_args(argv)
    try:
        root = _root(args.root)
        result = compile_selected(root, graph_id=args.graph_id, scope_id=args.scope_id,
            ceiling_path=args.ceiling, fragment_paths=tuple(args.fragment))
        raw = canonical_bytes(result) + b"\n"
        if args.output is None:
            sys.stdout.buffer.write(raw)
        else:
            graph_path(args.output)
            target = root.joinpath(*args.output.split("/"))
            parent = target.parent
            if parent != root:
                _selected(root, parent.relative_to(root).as_posix())
            with target.open("xb") as stream:
                if stream.write(raw) != len(raw):
                    _fail("GRAPH_CLI_SHORT_WRITE")
                stream.flush()
                os.fsync(stream.fileno())
            if _read(target) != raw:
                _fail("GRAPH_CLI_OUTPUT_READBACK")
        return 0
    except ContractError as error:
        sys.stderr.write(error.code + "\n")
        return 2
    except OSError as error:
        sys.stderr.write("GRAPH_CLI_IO_ERROR:" + type(error).__name__ + "\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only ER1 installed launcher/entry-point/RECORD reconciliation."""
from datetime import datetime, timezone
import base64
import configparser
import csv
import ctypes
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/er1-20261014", F / ".agents/runtime/er1-20261014"
V = R / "independent-review"
E3 = F / ".agents/source-assembly-20261014T021300Z/.agents/e3"
SITE = E3 / "Lib/site-packages"
sha = lambda data: hashlib.sha256(data).hexdigest()
def write(path, data): path.open("x", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
def native_id(path):
    class FileId(ctypes.Structure):
        _fields_ = [("volume_serial", ctypes.c_ulonglong), ("identifier", ctypes.c_ubyte * 16)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
                      ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p)
    create.restype = ctypes.c_void_p
    query = kernel.GetFileInformationByHandleEx
    query.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong)
    query.restype = ctypes.c_int
    close = kernel.CloseHandle
    close.argtypes, close.restype = (ctypes.c_void_p,), ctypes.c_int
    handle = create("\\\\?\\" + str(path), 0, 7, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    try:
        result = FileId()
        if not query(handle, 18, ctypes.byref(result), ctypes.sizeof(result)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {"volume_serial": result.volume_serial, "file_id_128": bytes(result.identifier).hex(),
                "file_id_low_64": int.from_bytes(bytes(result.identifier)[:8], "little")}
    finally:
        if not close(handle): raise ctypes.WinError(ctypes.get_last_error())
def observe(path):
    stat = path.lstat()
    assert path.is_file() and not stat.st_file_attributes & 0x400, path
    identity = native_id(path)
    data = path.read_bytes()
    after = path.lstat()
    assert (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    assert native_id(path) == identity
    return data, {"relative_path": path.relative_to(F).as_posix(), "sha256": sha(data), "bytes": len(data),
                  "native_identity": identity, "stat_device": stat.st_dev, "stat_inode": stat.st_ino,
                  "mtime_ns": stat.st_mtime_ns, "attributes": stat.st_file_attributes}

started = datetime.now(timezone.utc).isoformat()
inventory_raw = (R / "launcher-inventory.json").read_bytes()
inventory = json.loads(inventory_raw)
stub_raw, stub = observe(SITE / "pip/_vendor/distlib/t64.exe")
declared, metadata = {}, {}
for directory in sorted(SITE.glob("*.dist-info")):
    path = directory / "entry_points.txt"
    if not path.exists(): continue
    text, entry_observation = observe(path)
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(text.decode("utf-8"))
    if not parser.has_section("console_scripts"): continue
    package_raw, package_observation = observe(directory / "METADATA")
    package = BytesParser().parsebytes(package_raw)
    record_raw, record_observation = observe(directory / "RECORD")
    records = list(csv.reader(io.StringIO(record_raw.decode("utf-8"), newline="")))
    assert all(len(row) == 3 for row in records), directory
    metadata[directory.name] = {"distribution": package["Name"], "version": package["Version"],
        "entry_points": entry_observation, "METADATA": package_observation, "RECORD": record_observation,
        "record_rows": records, "row_count": len(records)}
    for name, value in parser.items("console_scripts"):
        assert name not in declared, name
        declared[name] = {"entry_point_value": value, "metadata_directory": directory.name,
                          "distribution": package["Name"], "version": package["Version"]}
assert len(declared) == 26
rows = []
for author_row in inventory["launchers"]:
    name = author_row["filename"]
    raw, source = observe(E3 / "Scripts" / name)
    assert source["sha256"] == author_row["sha256"] and source["bytes"] == author_row["bytes"]
    assert raw.startswith(stub_raw)
    begin = len(stub_raw)
    end = raw.index(b"\n", begin) + 1
    shebang = raw[begin:end].decode().strip()
    assert shebang == author_row["original_shebang"]
    assert "CETA_Intelligence_Operating_System_Build_Package" in shebang
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.namelist() == ["__main__.py"] and archive.testzip() is None
        main = archive.read("__main__.py")
    assert sha(main) == author_row["original_main_script_sha256"]
    entry_name = name[:-4]
    alias = entry_name == "pip3.12"
    bound = declared["pip" if alias else entry_name]
    assert bound["entry_point_value"] == author_row["entry_point_value"]
    assert bound["distribution"] == author_row["distribution"]
    assert bound["version"] == author_row["distribution_version"]
    meta = metadata[bound["metadata_directory"]]
    record_path = "../../Scripts/" + name
    matches = [(index, row) for index, row in enumerate(meta["record_rows"]) if row[0] == record_path]
    assert len(matches) == 1
    index, record = matches[0]
    expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
    assert record[1] == expected and record[2] == str(len(raw)), name
    rows.append({"filename": name, "source": source, "distribution": bound["distribution"], "version": bound["version"],
        "metadata_directory": bound["metadata_directory"], "entry_point_value": bound["entry_point_value"],
        "binding": "PIP_STANDARD_PYTHON_3_12_ALIAS" if alias else "DIRECT_CURRENT_DECLARATION",
        "record_index_zero_based": index, "record_fields": record, "source_record_matches": True,
        "stub_sha256": sha(stub_raw), "main_sha256": sha(main), "original_shebang": shebang,
        "execution_allowed": name in {"pip.exe", "pip3.exe", "pip3.12.exe", "jsonschema.exe"}})
assert len(rows) == 27 and len({row["filename"] for row in rows}) == 27
assert {row["filename"][:-4] for row in rows if row["binding"] == "DIRECT_CURRENT_DECLARATION"} == set(declared)
report = {"schema_version": 1, "actor": "/root/pressure_writer", "started_at": started,
    "finished_at": datetime.now(timezone.utc).isoformat(), "author_inventory_sha256": sha(inventory_raw),
    "declared_entry_points": declared, "declaration_count": len(declared), "launcher_count": len(rows), "launchers": rows,
    "metadata": {name: {key: value for key, value in row.items() if key != "record_rows"} for name, row in metadata.items()},
    "standard_stub": stub, "all_27_source_RECORD_bindings_match": True,
    "required_staged_metadata_targets": [row["RECORD"]["relative_path"] for row in metadata.values()],
    "future_publication_requirement": "Update only the 27 launcher hash/size fields in three RECORD files together with exact generated launchers; preserve every other row and byte",
    "whole_environment_statement": "This independent run measured the limited launcher/metadata primitive scope only; full E3 census and directory-size qualification are separate pinned evidence",
    "claim_state": "READ_ONLY_PREPARATION_AWAITING_AUTHOR_FREEZE", "active_mutations": False, "native_execution": False}
write(V / "source-inventory-r1.json", report)
print(json.dumps({"declarations": 26, "launchers": 27, "distributions": list(metadata),
    "source_record_matches": 27, "report_sha256": sha((V / "source-inventory-r1.json").read_bytes()), "native_execution": False}))

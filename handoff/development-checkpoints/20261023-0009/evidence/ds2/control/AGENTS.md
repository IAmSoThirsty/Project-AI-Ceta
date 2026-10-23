# Exact Windows directory observation qualification

Candidate utility only. No canonical/Git/installed-tool modifications, no fixture edits outside work, no native worker/AC7 activity. Preserve all failed ST2 admission evidence; retain stock exclusions, full physical coverage, exact file hash/native/reparse checks and directory identity/membership change rejection. Repair only independently reproduced nested-error custody and partial-query provenance defects in frozen DS1; retain its successful controls/full scan as history and retain its rejected review unchanged. Keep same-provider directory-handle metadata without masking raw evidence. Independent Collaborative Review and ordinary gate required before any later ST2 runtime use.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "t_drive_repository_change",
    "override_nodes": {
      "implement": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          "00-Active/Project-AI-CETA/.agents/runtime/oq23/ds2/work/**"
        ]
      },
      "review": {
        "kind": "agent",
        "role": "reviewer",
        "access": "write_scoped",
        "write_scope": [
          "00-Active/Project-AI-CETA/.agents/runtime/oq23/ds2/review/**"
        ]
      },
      "validate": {
        "kind": "gate",
        "access": "read_only",
        "commands": [
          "\"T:\\00-Active\\Project-AI-CETA\\.agents\\source-assembly-20261014T021300Z\\.agents\\e3\\Scripts\\python.exe\" -B -X utf8 \"T:\\00-Active\\Project-AI-CETA\\.agents\\runtime\\oq23\\ds1\\work\\verify_prepared.py\""
        ]
      },
      "integrate": {
        "kind": "integration",
        "role": "integrator",
        "access": "write_scoped",
        "write_scope": [
          "00-Active/Project-AI-CETA/.agents/runtime/oq23/ds2/delivery/**"
        ]
      }
    }
  }
}
```

# Exact corrected verifier admission for immutable DS2 utility

Reuse exact frozen46-file DS2 source and its50 controls/full qualification. Original setup incorrectly declared rejected DS1 verifier and remains historical. Read-only source adoption; no W/canonical/Git/installed/ST2/native changes. Review corrected graph/helper and run actual DS2 verifier.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "t_drive_repository_change",
    "override_nodes": {
      "implement": {
        "kind": "agent",
        "role": "worker",
        "access": "read_only",
        "write_scope": []
      },
      "review": {
        "kind": "agent",
        "role": "reviewer",
        "access": "write_scoped",
        "write_scope": [
          "00-Active/Project-AI-CETA/.agents/runtime/oq23/ds2/review-r2/**"
        ]
      },
      "validate": {
        "kind": "gate",
        "access": "read_only",
        "commands": [
          "T:\\00-Active\\Project-AI-CETA\\.agents\\source-assembly-20261014T021300Z\\.agents\\e3\\Scripts\\python.exe -E -B -X utf8 T:\\00-Active\\Project-AI-CETA\\.agents\\runtime\\oq23\\ds2\\work\\verify_prepared.py"
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

# Prospective Git publication gates

Scope: finalize the existing staged checkpoint, independently inspect it, validate, then commit and push the exact tree under the current user instruction. No product integration or live qualification is authorized here. The inherited T: root graph and its distinct review remain in force.

Initial skill checks, read-only delegation and staging began before this run was initialized. Their preserved command evidence is not retroactive TAAR authorization. This run records the remaining prospective transitions only.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "t_drive_repository_change",
    "nodes": {
      "verify_polyglot27": {
        "kind": "agent",
        "role": "reviewer",
        "access": "read_only"
      }
    },
    "override_nodes": {
      "implement": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          "00-Active/Project-AI-CETA",
          "00-Active/Project-AI-CETA/**"
        ]
      },
      "integrate": {
        "kind": "integration",
        "role": "integrator",
        "access": "write_scoped",
        "write_scope": [
          "00-Active/Project-AI-CETA",
          "00-Active/Project-AI-CETA/**"
        ]
      },
      "validate": {
        "kind": "gate",
        "access": "read_only",
        "commands": [
          "git -C \"{workspace}\" diff --check",
          "git -C \"{workspace}\" diff --cached --check -- .gitattributes .gitignore"
        ]
      }
    },
    "edges": [
      {
        "id": "git_implement_byte_review",
        "from": "implement",
        "to": "verify_polyglot27",
        "type": "requires_review"
      },
      {
        "id": "git_byte_review_validate",
        "from": "verify_polyglot27",
        "to": "validate",
        "type": "authorizes"
      }
    ]
  }
}
```

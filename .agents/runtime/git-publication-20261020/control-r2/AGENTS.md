# Corrected-byte publication successor

The original prospective publication run is preserved. Independent verification found 202 LF-normalized index blobs whose local originals retain CRLF. This successor permits index-only repair from unchanged local bytes and fresh exact-tree review. The inherited T: graph and separate reviewer identities remain required. Validation names the exact canonical Git worktree explicitly; its claim workspace is Git metadata. Product implementation and native qualifications remain paused.

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
          "git -c core.fsmonitor=false -C \"T:/00-Active/Project-AI-CETA\" diff --check",
          "git -c core.fsmonitor=false -C \"T:/00-Active/Project-AI-CETA\" diff --cached --check -- .gitattributes .gitignore"
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

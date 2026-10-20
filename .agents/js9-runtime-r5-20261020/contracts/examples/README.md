# Contract fixtures

These files are non-executable synthetic parser/shape examples. They contain no working keys, grants, signatures, model readiness or real observations. The wrapper `never_authority` must remain true. Validate `instance` against `records.schema.json`; then implement semantic, signature, freshness and actual identity checks separately.

`duplicate_keys.wire.txt` must be rejected by the strict raw JSON decoder before a schema validator sees a collapsed dictionary. It is an intentional invalid wire example, not a package JSON file.

# AC7 owned-child loader capture construction

Root assigns code only under the private loader-capture candidate and evidence
only under records/. The live coordinator runtime is control/, outside both
workspaces. This graph grants no debugger, worker, profile, credential or host
configuration operation. A named distinct reviewer is required for handoff.

```agents-graph
{"version":1,"graph":{"id":"ceta_ac7_loader_capture_construction","policy":{"fail_closed":true,"require_receipts":true,"prohibit_self_review":true,"prohibit_scope_overlap":true,"max_parallel":4},"nodes":{"implement":{"kind":"agent","role":"worker","access":"write_scoped","write_scope":[".agents/ac7-loader-capture-20261020/**"]},"evidence":{"kind":"agent","role":"worker","access":"write_scoped","write_scope":[".agents/runtime/ac7-loader-capture-20261020/records/**"]}},"edges":[]}}
```

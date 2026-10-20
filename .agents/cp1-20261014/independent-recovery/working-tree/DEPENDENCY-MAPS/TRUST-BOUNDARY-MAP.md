# Trust boundary map

| Boundary | Untrusted or lower-trust input | Required control | Evidence |
| --- | --- | --- | --- |
| Human interface to native runtime | Renderer state, deep links, stale views | Authenticated IPC, typed command, current scope and proposal binding | Native command and decision records |
| Retrieved content to model context | Documents, pages, attachments, tool text | Access filtering, source attribution, structural instruction/data separation | Exact context snapshot and source map |
| Model output to tasks and tools | Generated plans, arguments, claims | Schema validation, explicit effects, authority evaluation | Task contract and validated proposal |
| Task to native effects | Worker requests, retries, delegated agents | Current capability, target identity, resource admission, qualified isolation | Gate decision and actual-effect observations |
| Extension to host | Extension code and manifests | Separate principal, least authority, qualified isolation, integrity checks | Manifest, grant, runtime observation |
| Secret vault to worker | Secret-use requests | Purpose and destination binding, short-lived scoped handles | Access decision without secret disclosure |
| Storage to recovery | Snapshots, journals, restored files | Integrity, schema, consistency, revocation and deletion reconciliation | Recovery report and restored-state checks |
| Evidence to completion claim | Receipts, logs, builder summaries | Exact artifact binding, trust, completeness, independent verification | Accepted verification result |
| Optional network to local data | Redirects, remote messages, external models | Explicit destination and payload scope, authenticated transport, no silent fallback | Request digest, consent, observed result |

Each boundary is qualified on the actual target environment. A risk score, signature, role label, or interface control alone does not establish the full boundary. Preserve observation gaps and reject unsupported mandatory enforcement semantics.

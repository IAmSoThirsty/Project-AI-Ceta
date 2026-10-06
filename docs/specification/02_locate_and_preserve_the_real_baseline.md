# Locate and preserve the real baseline

**Document ID:** SPEC-02  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-02-01

Begin in the owner-designated CETA desktop worktree. Historical evidence identifies IAmSoThirsty/CETA-Model-Base-Data, branch codex/ceta-desktop-release, and local path T:\00-Active\CETA-desktop-delivery-20260906. Inspect the actual directory, Git root, branch, HEAD, worktree list, remotes, dirty files, untracked files, ignored assets, active application processes, and continuity record before assuming these remain current. The inspected remote head at prompt preparation was 8422b06446e33df2bb24c23424981165f6cbfcf0; that is a reference point, not a reset target. Prefer verified newer local work and preserve its relationship to the remote.

### REQ-02-02

The owner selected one authoritative CETA worktree. Do not create extra worktrees, clones, remotes, or competing CETA products. Build the new architecture in a clearly isolated development area of that same worktree until cutover, using existing conventions where they do not undermine the rebuild. Record the development namespace and final shipping namespace. The released application must have one production entry point and one live runtime architecture; staging must not become a permanent second product.

### REQ-02-03

Create a preservation checkpoint before mutations. Capture the baseline Git diff, file inventory, hashes for affected sources, lockfiles, manifests, relevant untracked files, schema versions, public verification material, and sensitive-asset locations without exposing their contents. Verify that restoration is practical. Do not use reset --hard, git clean, forced checkout, stash manipulation, automatic deletion, or bulk formatting to manufacture cleanliness. Do not put backup plaintext secrets or private conversations into Git.

### REQ-02-04

Keep old application data separate from fresh rebuild test data. Never point destructive tests, migration experiments, untrusted workers, or an unqualified executable at the normal profile. Before actual migration, inspect the source store under its documented locking and backup rules, including SQLite companion files. Missing identity beside signed history is a recovery condition, not permission to create a replacement key. Preserve unknown files, rows, extensions, and data whose meaning is unresolved.

### REQ-02-05

Identify other agents and processes touching the same surfaces. Allocate write scopes and one integration owner so simultaneous workers cannot independently rewrite schemas, APIs, evidence, or the baseline. Use snapshots and fixture copies without adding another authoritative worktree. Unexplained concurrent changes invalidate affected source-bound tests and require reconciliation.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B001, B002, B003, B006, B008. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.

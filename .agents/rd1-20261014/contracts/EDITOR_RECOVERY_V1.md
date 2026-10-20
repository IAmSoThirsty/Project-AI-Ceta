# Rejected interpretation editor recovery

The owner-internal `task.editor_retain`, `task.editor_load`, and
`task.editor_discard` commands preserve raw editor documents separately from
validated task drafts and unaccepted meaning proposals. They use the existing
authenticated local ingress and canonical SQLite journal writer.

Each recovery payload binds the saved task revision and widget revision to all
ten interpretation documents. UTF-16LE hex preserves Qt raw text, including
unpaired surrogates. Document identity, native revision, cursor position, and
anchor position are retained. Positions count UTF-16 code units. A fresh native
document receives a new identity; its revision may restart. Native revisions
must advance consistently within the same document identity.

Retain and discard use the exact observed recovery revision as a compare-and-
swap precondition. Discard records a historical `DISCARDED` projection containing
the full prior payload and predecessor revision. The canonical journal retains
earlier complete projection wires. Neither deletion nor a transport failure
constitutes discard consent. Loads check current authenticated task ownership
and source event/observation lineage, including after receiver restart.

The desktop queues rejected documents without substituting them into validated
meaning. `QUEUED`, `SAVING`, and `UNCERTAIN` describe custody without claiming a
durable result. A bound result or exact authenticated reconciliation is required
for `RETAINED` or `DISCARDED`. Raw recovery loads require user review before a
proposal can be recorded. Pending discard keeps the real dialog available.

The durable wire supports 131,072 UTF-16 bytes per document and 196,608 bytes
across all ten documents, subject to the existing maximum message size. Larger
documents are rejected without truncation; the session retains an independent
local byte capture for recovery after Qt deletion. That local capture does not
survive interpreter death and is not reported as restart-durable storage.

This development path does not accept a task, issue consent or a grant, enable
the normal-profile compiler, or close protected outer-process shutdown custody.

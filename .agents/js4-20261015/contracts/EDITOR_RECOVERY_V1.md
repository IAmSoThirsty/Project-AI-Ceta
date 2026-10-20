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

Ordinary typing coalesces locally for 150 milliseconds before dispatch. If a
newer complete capture arrives while an earlier retention request owns the
writer, the earlier acknowledged result makes that latest capture immediately
eligible for the next ordinary poll. Intermediate local captures remain
coalesced. A lost or denied response, an incomplete local serialization, or a
Stop observation keeps its existing reconciliation or custody restriction.
Only the current capture's own bound result establishes its durable retention.

The inline payload supports 131,072 UTF-16 bytes per document and 196,608 bytes
across all ten documents, subject to the existing maximum message size. Larger
captures use the existing reference payload and ordered authenticated chunks.
That route bounds each document to 8 MiB of UTF-16LE, all ten documents together
to 16 MiB, each chunk to 128 KiB, and a capture to 128 chunks. Every command
remains subject to the unchanged 1 MiB wire limit. Lowercase hex and document
and chunk commitments preserve the exact captured bytes, including lone
surrogates, without placing raw text in an authority-bearing interpretation.

The canonical recovery projection remains `STAGING` while chunks are missing.
It becomes `RETAINED` only after all ordered chunks and their bound complete
capture are committed. A response failure requires authenticated reconciliation;
it does not establish rollback, completion, or permission to replay a mutation.
Restart discovery and explicit recovery inspect the canonical projection and
its bound chunk records before restoring documents.

Out-of-bound or incomplete serialization never truncates the source documents.
The session also retains an independent local byte capture for recovery after
Qt deletion. That local capture alone does not survive interpreter death and is
not reported as restart-durable storage. Durable custody requires the complete
bound journal result, rather than a local capture or an incomplete reference.

This development path does not accept a task, issue consent or a grant, enable
the normal-profile compiler, or close protected outer-process shutdown custody.

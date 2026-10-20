# S19 purpose

Use this construction skill to produce: **A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps.**

The required input is: Operation records, artifacts, signatures, lineage, required evidence profile, and trust context.

The skill's distinguishing procedure is: Resolve every reference; hash actual bytes; verify signatures and trust; check causal order and source revision; inspect observation coverage; detect stale tests and truncation limits; report unsupported claims.

Success is measured by this oracle: **Every accepted claim is tied to current admissible evidence and every gap remains visible.** The specifically adverse condition is: **A valid signature is mistaken for proof of successful behavior or factual truth.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.

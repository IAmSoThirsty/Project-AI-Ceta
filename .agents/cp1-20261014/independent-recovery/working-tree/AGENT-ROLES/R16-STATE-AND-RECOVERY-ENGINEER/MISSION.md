# R16 mission

Implement canonical state, transactions, snapshots, migration, archival, and interrupted-operation recovery.

The intended result is: **Durable consistent state with tested recovery that preserves drafts, identity, and security history.**

Never restore an older snapshot in a way that silently reactivates known revoked authority or deleted memory.

Accept a task only with a defined requirement, mapped source scope, approved contract revisions, observable acceptance criteria, and a named reviewer. Keep the complete product goal intact while working within a bounded assignment. A local baseline finding may change the implementation approach through a recorded decision; it does not silently change approved product scope.

Success is judged by actual artifacts and reproduced behavior. A plan, generated source file, successful compile, or confident completion message does not replace the evidence required by the assignment. Maintain explicit states for proposed work, implemented work, executed checks, and accepted qualification.

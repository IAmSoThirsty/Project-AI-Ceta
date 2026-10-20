# S09 purpose

Use this construction skill to produce: **Durable local records, atomic publication intent, integrity checks, and tested restoration.**

The required input is: Reconciled storage engine, data schemas, transaction boundaries, retention rules, and fault fixtures.

The skill's distinguishing procedure is: Define authoritative versus derived stores; choose explicit commit boundaries; handle disk-full and corruption; coordinate durable event publication; test crash points; verify backup restoration and deletion propagation.

Success is measured by this oracle: **Each injected crash yields a documented prior, committed, or explicitly uncertain state without silent data loss.** The specifically adverse condition is: **An in-memory success acknowledgement precedes durable commit.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.

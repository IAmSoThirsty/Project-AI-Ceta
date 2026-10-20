# S16 purpose

Use this construction skill to produce: **Executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states.**

The required input is: Requirements, unit specifications, canonical contracts, inspected test tooling, and controlled fixtures.

The skill's distinguishing procedure is: Derive positive and negative cases; reproduce original defects; isolate fixtures; run unit and real integration paths; capture commands, environment, logs, and artifacts; preserve every failed or omitted obligation.

Success is measured by this oracle: **A test fails on the known defect and observes the required corrected behavior.** The specifically adverse condition is: **Generated tests merely restate the implementation or are reported passed without execution.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.

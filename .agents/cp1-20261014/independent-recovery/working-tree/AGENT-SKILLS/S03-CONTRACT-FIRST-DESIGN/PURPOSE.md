# S03 purpose

Use this construction skill to produce: **A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures.**

The required input is: Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints.

The skill's distinguishing procedure is: Define exact records and type constraints; assign mutation ownership; specify success, failure, partial, and uncertain outcomes; define compatibility and versioning; obtain affected-owner review before implementation.

Success is measured by this oracle: **Producer and consumer conformance fixtures exercise identical semantics, including denial and uncertainty.** The specifically adverse condition is: **A consumer privately widens a security-critical field or assumes unknown states mean success.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.

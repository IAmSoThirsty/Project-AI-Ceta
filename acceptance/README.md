# Acceptance specification

scenarios.json preserves B001-B128 exactly from the original prompt. Each case document adds a controlled fixture, real-call-path method, observations and evidence class. Codex must implement test code for the actual architecture. Cases with real Windows, hardware, model, independent review or elapsed-time prerequisites cannot be satisfied by mocks. Keep FAIL, BLOCKED, SKIP, TIMED_OUT and NOT_RUN distinct; preserve repaired failures and broaden cases when source requirements demand more.

Implementation proceeds under the root AGENTS.md and build/work_packages.json. Preserve runtime evidence statuses and the original handoff manifest.

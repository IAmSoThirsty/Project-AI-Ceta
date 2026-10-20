# D-001 Implementation language and test framework

Status: accepted for this recovery run. Implementation-tooling decision recorded by the executing agent; the repository has no owner-approved language pin.

Decision: Python 3.11+ (verified local interpreter 3.11.15), standard library only, unittest for tests.
Layout: implementation under src/, tests under tests/ at the repository root. No virtual environment required. No pip installs.
Limits: this decision does not pin cryptographic, storage, model-format, transport, or target-platform profiles (B-04 remains open). Native OS enforcement is unqualified (B-05 remains open).

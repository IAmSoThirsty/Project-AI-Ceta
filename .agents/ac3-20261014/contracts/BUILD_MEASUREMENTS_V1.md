# Separate build-evidence measurements

Finding 6 remediation. Parent obligations REQ-01-02/04, REQ-06-03, REQ-35-03,
REQ-40-03 and REQ-41-04. `tools/build_measurements.py` reports seven separate
axes from exact current specification inputs: applicability classification,
source reconciliation, requirement adoption, implementation, conformance
verification, independent acceptance and gate qualification. It reports no
aggregate completion percentage and makes no promotion based on another axis.

The preserved 406-row coverage bytes must retain SHA-256
`816d692ebf0d5b7b148ff2a021a8c994f59778a38a308542d08342289823e0b8`.
Zero unresolved applicability classifications means those decisions have labels;
it does not imply implementation, conformance, full-source reconciliation,
independent acceptance or qualified gates. Original case and gate states are
measured as recorded and are never rewritten by this tool. Historical state
records retain their original fields and meanings.

Run `python -B tools/build_measurements.py --specification-root <authorized-spec-root>
--report <new-evidence-path>`. The report binds all eight input hashes, checker
identity and its observation time, and rejects changed inputs before writing.
The current scope, original acceptance bodies and owner acceptance criteria are
preserved. The forty-six blank original acceptance bodies stay documented gaps.

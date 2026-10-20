# Reproducible development-source inventory

Finding 1 remediation. Parent obligations: REQ-01-01/02/04, REQ-36-01/04,
REQ-40-03. `tools/development_inventory.py` inventories unexcluded namespace
files twice, compares identities, and records SHA-256, byte length and whether
the source-test snapshot watches each file. It does not claim semantic review.

The historical 61-file review query, 72-path rg inventory and 70-file source-test
snapshot are separate observations. The 61 query omitted the lockfile, three
catalogs, event vector, five examples and `.gitignore`. It included `AGENTS.md`;
the 70-file source-test selection excluded `AGENTS.md` and `.gitignore`.
New implementation files increase current counts; no check pins future counts
to 61/70/72 or conceals new files to retain a historical count.

The explicit exclusions are the namespace cache/private/profile/model/runtime
directories, Python bytecode, private-key extensions and native-reference target
directory listed in the tool. Exclusions use case-insensitive Windows names and
prefixes. A scan/listing failure rejects the observation instead of silently
omitting inaccessible sources. Excluded payloads are not read. Unexcluded links
are rejected; unknown unexcluded files are included. Ambient gitignore or rg
configuration cannot silently change this inventory. Instruction and ignore
files are inventory controls even when outside the source-test watched set.

Run `python -B tools/development_inventory.py --report <new-evidence-path>`.
The report is created exclusively; historical evidence is not overwritten.
Record inclusion rules and input hashes with every review selection. Source
presence, byte equality, complete semantic review, adoption, implementation,
conformance and independent qualification retain separate measurements.

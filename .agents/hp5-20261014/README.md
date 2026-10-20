# Project-AI: CETA preservation implementation

HP5 repairs Windows case-alias policy fencing. Current `unknown`, `private_key`
and `live_profile` blocks take precedence for all ordinal case-equivalent relative
spellings, including digest lookups, direct copying, generator callbacks, Git
aliases, checkpoint verification and restoration. Original policy/archive names
and whole-byte hashes remain unchanged. Duplicate equivalent classifications
with the same identity are rejected; distinct historical whole-hash versions
remain separate. Positive classifications and provenance continue to require
their exact recorded spelling, root, bytes and proof.

The comparator uses Windows [CompareStringOrdinal](https://learn.microsoft.com/en-us/windows/win32/api/stringapiset/nf-stringapiset-comparestringordinal)
with the operating system case table, without linguistic normalization. Actual
owned Windows file tests compare its results with `Path.samefile`; Python
`casefold` and `str.lower` expansion examples remain distinct native paths.
This installed Python 3.12 `ntpath.normcase` uses Windows `LCMapStringEx`, rather
than its optional `str.lower` fallback; its observed behavior is retained in the
author evidence. A comparator failure closes the operation. Case-sensitive
Windows directories may be conservatively blocked by the denial comparison;
positive authority is never widened by it. Existing root authorization and
unsupported-path/proof refusals remain in force. No real external capture or
policy activation is performed by this author cut.

`preserve_ceta_complete.py` captures ordinary source bytes and independent Git
recovery data. It uses installed Python 3.12's standard library and installed Git.
It has no application-runtime dependency and never executes CETA.

The policy requires exact absolute `source_roots`, `git_roots`, `capture_targets`
and `restore_targets`. It accepts only those targets, including the common Git
directory of a linked worktree. The coordinator supplies the real policy after
source verification and Collaborative Review; the tool does not guess projects
from names or traverse adjacent repositories.

The CLI operations are `capture --source --output`, `verify --checkpoint`, and
`restore --checkpoint --destination`, each preceded by `--policy` and its JSON
file. `capture` inside the source additionally requires
`--active-output-exclusion` equal to that exact new output. Existing output paths,
indexed paths, historical paths, Git-metadata paths, and broader exclusions are
refused. Earlier evidence and ignored or unknown ordinary files are retained.

Successful capture seals `inventory.json`, `working-tree.zip`, the Git metadata
archives, binary staged/working differences and independent `git-objects.pack`.
Ordinary-byte copying requires native Windows: a read-only source handle denies
write/delete sharing across a full bounded hash/identity admission and the copy.
No output member is created until that admitted identity/hash matches. An already
open writer refuses capture; failed destinations remain evidence, and recovery
uses a new explicitly authorized target after the writer releases its handle.
The pack contains every observed Git object, including ref- and reflog-only
history, staged blobs and unreferenced objects. Ref names, HEAD, reflog records,
original index bytes and original object-storage hashes are recorded. No source
ref is created or changed. Private observation copies prevent Git's split-index
refreshes from modifying source indexes or shared-index timestamps.
All source Git metadata is classified and hashed before any observation copy is
created. Pending metadata refuses capture before creating the checkpoint or a
private read view. Admitted observation and metadata-archive bytes are checked
against their exact hash and identity before they are written; a changed source
does not become an approved copy merely because its path is unchanged.

Restore validates all artifact and ZIP-member hashes before extraction. It uses
a new destination-owned stage, reconstructs an independent Git object database,
retains original refs and reflog commits, restores the source index and binary
differences, checks object identities and Git connectivity, then publishes using
Windows' atomic no-overwrite rename. Failed stages remain evidence; an incomplete
stage is never published over a source or an existing owner destination. Original
Git configuration and worktree pointers remain inert metadata.

Reparse entries retain their exact native Windows descriptor and readable target
without traversal. They are never recreated. Restore requires explicit
`--allow-inert-reparse` when such entries exist and reports
`usable_links_restored: false`. This is ordinary-byte and Git recovery, not a
usable-link restoration or application qualification.

Sensitive suffixes, candidate live locations, credentials and private-key markers
are classified explicitly. Missing provenance produces an incomplete checkpoint
and exit status 2; restore refuses it. Exact `fixture_database` and
`public_certificate` classifications require the source root, relative path,
SHA-256 and provenance evidence. SQLite fixtures must have actual SQLite bytes;
public certificates are parsed as certificates, accepting standard '#' comments
and whitespace while preserving the original bundle bytes. Actual private-key markers,
live profiles and credential URLs remain pending and are not transferred. A
`fixture_secret_marker` classification requires exact producer-owned bytes and
rejects encoded private material. It permits invalid negative-test text rather
than incorrectly declaring that text to be a live key. A
historical blob with different bytes requires its own root/path/SHA-256
classification; multiple exact versions at one path can coexist. A historical
version cannot inherit a current-file claim. Unread sensitive content stability
is not claimed. Pending protected working paths are withheld from status/diff
inspection, and incomplete checkpoints withhold patch payloads and their Base64
inventory representations as well as the independent Git pack.
Git path provenance includes every retained commit root, tagged tree, orphan
tree and staged index entry. Blobs without a verified path remain pending; they
are retained in the full object inventory and are not silently dropped. Every
object type, including commit messages, annotated tags and tree payloads, passes
the protection scan before the all-object pack is admitted. An exact invalid
fixture-marker classification must cover every known alias of its blob. Protected
tree names are refused without exposing their bytes in diagnostics.

Credential URL detection scans entire files and object payloads in bounded
chunks, retaining only parser state across boundaries. It covers an unchecked
tail after four MiB, a split :// token, and an arbitrarily long authority token.
No credential URL exception is supplied by a fixture classification. Public URLs
with ports remain permitted. This conservative detector protects URL userinfo;
colon-free tokens are included. Path, query and fragment at-signs end the
authority scope and do not become userinfo merely because a public URL has a port.
it is not a universal detector for every possible secret format.

Exit status 0 means the stated operation passed; 1 means failure; 2 means capture
remains incomplete due to sensitive inputs. The SHA-256 seal detects changed
artifacts; it is not a signature or an authority credential.

Windows extended-length I/O supports paths beyond 260 characters. The tool stores
ordinary file mode, attributes, mtime and identity in its inventory and restores
bytes, mode and mtime. It does not claim NTFS ACL, alternate-stream or arbitrary
extended-attribute restoration. Source directories and assets remain in place.
External Git includes, filters, object alternates, grafts, shallow history and
partial-clone declarations require separate review and are refused. No network
fetch, system configuration change, source hook or application test is admitted.

The native suite is `python -B -m unittest -v test_preserve_ceta_complete` from this
cut. `run_preservation_tests.py` runs it and writes exact output and SHA-256-bound
receipts only to this cut's assigned sibling runtime directory. Tests retain
their generated disposable Windows/Git fixtures in the exact sibling runtime's
`native-review-fixtures` directory when run through the receipt runner. Native sources and
actual CETA data are not test fixtures and have not been captured by these tests.

For a read-only Collaborative Review re-run, `CETA_PRESERVATION_TEST_FIXTURE_ROOT`
may name only the exact sibling runtime directory's `native-review-fixtures`
child. Every other override is refused. This preserves the frozen code cut and
all prior Q fixtures; it does not relocate earlier evidence or alter LOC counts.


## HP3 lineage: exact frozen content provenance

Authoritative repository: `T:/00-Active/Project-AI-CETA`. This successor extends
frozen P4 in its own author cut. The historical P4 sections above retain their
original provenance. P4, HP1, and HP2 were read without changing their bytes.

The optional `content_provenance` policy field has four required keys:
`proof_bundle`, `snapshot_inventory`, `report_sha256`, and `entries`. The report
anchor is exactly `59d6b4fe06d0baf9b43199b7c7c9ff7a5825d71227ef217b9732076c3c96a65c`,
which Root personally inspected. A caller cannot add trust with a reviewed label,
a supplied replacement hash, a filename, or an installed RECORD match. Proof
members are resolved by safe basename beneath the explicit bundle directory;
historical absolute evidence locators remain historical and are not rewritten.
Every proof input hash is checked again during capture, copy, and verification.

Each entry requires `entry_id`, `kind`, `source_root`, and `sha256`, plus either
`path` or both `git_oid` and `aliases`. The exact root, whole bytes, and complete
canonical alias set must match frozen proof. All private-marker and userinfo
positions are recomputed. A changed byte, new protected position, missing proof,
changed alias, malformed binding, or unsupported format keeps the gate closed.
An explicit blocked-location classification takes precedence.

Three typed kinds are supported:

- `public_wheel_member`: exact member equality and complete archive SHA256 from
  HP2's primary PyPI comparison, plus Python literal/comment/template or bounded
  PE format constraints. Publication establishes publication provenance.
- `owned_test_literal`: exact reviewed source or historical Git blob, with each
  flagged literal inside its bound test function. Private constants must be
  marker-only; encoded private-key material is refused.
- `generated_cache`: exact source generator, interpreter version and magic,
  valid header, entire marshal consumption, and equality of code fields and
  constants. Filename and marshal reference encoding are excluded from structural
  equality; protected filenames are refused. Frozensets are compared unordered.
  Private constants remain marker-only. Compilation and decoding never execute
  source, cached code, installers, or package imports.

A complete capture retains exact generator bytes in `provenance-generators.zip`
so restoration can validate a historical cache after the original generator has
changed. These generator bytes require their own fixed digest and appropriate
literal proof. Checkpoint verification rechecks protected archive content and
proof bindings. Restoration independently inventories every imported Git object,
rebuilds aliases, scans the actual restored pack, and refuses unknown protected
content before publishing the new target. Configuration remains inert.

The original P4 streaming scanner, no-reparse checks, native immutable-copy
sharing rules, and unknown-entry behavior remain active. W043, W044, and W045
are unsupported held entries. HP3 performs no actual external capture or
admission. The candidate policy in the assigned runtime directory has zero
capture targets and zero restore targets and requires separate review.

Run `run_preservation_tests.py --report-directory <this cut's runtime directory>
--run-label <fresh label> --suite p4|provenance|all` with Python 3.12 from
`T:/00-Active`. All fixtures and raw receipts stay in the assigned runtime scope.
Synthetic positive proof tests patch the trust anchor only inside the test
process; those results establish parser behavior, not public provenance.
The actual HP2 proof parsing test reads sanitized frozen evidence without
reading/admitting external source bytes. Separate review remains required.

Format references: [Microsoft PE/COFF](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format),
[Python marshal](https://docs.python.org/3.12/library/marshal.html), and
[PEP 552 cache headers](https://peps.python.org/pep-0552/).
Marshal is version dependent; unknown/unbound data is never decoded. These
checks make no universal claim about secret formats, producer authentication,
privileged host mutation, or full CETA product completion.

## HP4 repair: current blocked classifications

This distinct successor repairs independently reproduced HP3-F01 and HP3-F02.
It checks the current blocked classifications for direct provenance locations
and every producer alias before reading generator bytes. Historical generators
also require a fresh complete tree and private-index alias observation before
their first content read. Unsupported, missing, changed, or blocked producers
keep their derived cache out of the working archive.

Restoration applies the current blocked classifications to every ordinary
working and metadata location before protected-content validation and target
publication. Preserved generator providers use the same current policy check.
Seven exact independent hostile regression methods accompany the unchanged
110 original cases. The earlier failures and frozen HP3 remain preserved.
Actual external capture and policy activation require the distinct successor
review and exact current source evidence.

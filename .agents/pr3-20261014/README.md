# Project-AI: CETA preservation implementation

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

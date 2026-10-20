# Receipt integrity check only: does not invoke compiler, tests, or worker.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$reviewRoot='T:\00-Active\Project-AI-CETA\.agents\runtime\ac7-native-artifact-review-20261020'
$buildRoot='T:\00-Active\Project-AI-CETA\.agents\runtime\ac7-token-contract-20261020\build-r1'
$receiptPath=Join-Path $buildRoot 'BUILD.json'
$receipt=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
function Digest([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$logs=@($receipt.commands | ForEach-Object {
    $label=$_.label
    $stdout=Join-Path $buildRoot ($label+'.stdout')
    $stderr=Join-Path $buildRoot ($label+'.stderr')
    $actualOut=Digest $stdout
    $actualErr=Digest $stderr
    [pscustomobject]@{
        label=$label;recorded_exit_status=$_.exit_status
        stdout_path=$stdout;stdout_sha256=$actualOut;stdout_matches_receipt=($actualOut -eq $_.stdout_sha256)
        stderr_path=$stderr;stderr_sha256=$actualErr;stderr_matches_receipt=($actualErr -eq $_.stderr_sha256)
    }
})
$actualImage=Digest $receipt.native_image.path
$actualSource=Digest $receipt.source.path
$actualCompiler=Digest $receipt.actual_rustc.path
$audit=[ordered]@{
    kind='receipt-integrity-observation-not-build-reexecution';at_utc=[DateTime]::UtcNow.ToString('o')
    repository='T:\00-Active\Project-AI-CETA'
    branch=(& git -c safe.directory=T:/00-Active/Project-AI-CETA branch --show-current)
    head=(& git -c safe.directory=T:/00-Active/Project-AI-CETA rev-parse HEAD)
    receipt_path=$receiptPath;receipt_sha256=(Digest $receiptPath)
    receipt_build_at=$receipt.at;source=$receipt.source;observed_source_sha256=$actualSource;source_hash_matches=($actualSource -eq $receipt.source.sha256)
    compiler=$receipt.actual_rustc;observed_compiler_sha256=$actualCompiler;compiler_hash_matches=($actualCompiler -eq $receipt.actual_rustc.sha256)
    recorded_compiler_version=$receipt.version_output;recorded_sysroot=$receipt.sysroot
    image=$receipt.native_image;observed_image_sha256=$actualImage;image_hash_matches=($actualImage -eq $receipt.native_image.sha256)
    byte_count_matches=((Get-Item -LiteralPath $receipt.native_image.path).Length -eq $receipt.native_image.bytes)
    command_log_integrity=$logs
    recorded_pure_test_count=$receipt.pure_tests
    recorded_worker_executed=$receipt.actual_restricted_worker_execution
    recorded_host_profile_operations=$receipt.host_profile_operations
    reviewer_executed_worker=$false;reviewer_executed_tests=$false;reviewer_executed_compiler=$false
    limitations=@(
        'Hash agreement and stored stdout establish present-file consistency with this receipt, not authenticated build provenance or reproducibility.',
        'Recorded success is build-context evidence; this review did not rerun compilation or the five pure tests.',
        'The separate test executable is outside the inspection target and was not opened, analyzed or executed.'
    )
}
if (-not $audit.source_hash_matches -or -not $audit.compiler_hash_matches -or -not $audit.image_hash_matches -or -not $audit.byte_count_matches) { throw 'Receipt identity mismatch' }
if (@($logs | Where-Object { -not $_.stdout_matches_receipt -or -not $_.stderr_matches_receipt }).Count -ne 0) { throw 'Recorded log integrity mismatch' }
$output=Join-Path $reviewRoot 'receipt-integrity.json'
$encoded=[Text.UTF8Encoding]::new($false).GetBytes(($audit | ConvertTo-Json -Depth 16))
$stream=[IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $stream.Write($encoded,0,$encoded.Length) } finally { $stream.Dispose() }
[pscustomobject]@{receipt_sha256=$audit.receipt_sha256;source_matches=$audit.source_hash_matches;compiler_matches=$audit.compiler_hash_matches;image_matches=$audit.image_hash_matches;bytes_match=$audit.byte_count_matches;log_pairs=$logs.Count;log_pairs_match=$true;reviewer_executed_worker=$false;reviewer_executed_tests=$false} | ConvertTo-Json


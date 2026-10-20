$ErrorActionPreference='Stop'
$proof=Get-Content -LiteralPath 'T:\00-Active\Project-AI-CETA\.agents\runtime\ac3-20261014\native-r2\RESULT.json' -Raw | ConvertFrom-Json
$known=@{};foreach($row in $proof.native_process_lifetimes){if($row.creation_time -gt 0){$known[([string]$row.pid+':'+[string]$row.creation_time)]=$true}}
$rows=@(Get-CimInstance Win32_Process | Where-Object { $known.ContainsKey(([string]$_.ProcessId+':'+[string]$_.CreationDate.ToUniversalTime().ToFileTimeUtc())) } | Select-Object ProcessId,ParentProcessId,CreationDate)
$scope=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -and $_.Name -like 'python*.exe' -and $_.CommandLine.Contains('T:\00-Active\Project-AI-CETA\.agents\runtime\ac3-20261014\') -and $_.CommandLine.Contains('job-fixtures') } | Select-Object ProcessId,ParentProcessId,CreationDate)
[pscustomobject]@{clear=($rows.Count -eq 0 -and $scope.Count -eq 0);known_lifetimes_remaining=$rows;owned_fixture_processes_remaining=$scope;observed_at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 8 -Compress

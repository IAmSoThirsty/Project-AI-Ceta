$ErrorActionPreference = 'Stop'
$taskProject = 'T:\00-Active\Project-AI-CETA'
$taskOutput = Join-Path $taskProject '.agents\runtime\ac7-loader-diagnostic-preparation-20261020'
$taskInventoryPath = Join-Path $taskOutput 'INSTALLED-INVENTORY.json'
$taskProviderPath = Join-Path $taskOutput 'PROVIDER-METADATA.json'
if ((Test-Path -LiteralPath $taskInventoryPath) -or (Test-Path -LiteralPath $taskProviderPath)) { throw 'Refuse to overwrite inventory' }

$taskNames = @('cdb.exe','windbg.exe','windbgx.exe','ntsd.exe','gflags.exe','dbgeng.dll','dbghelp.dll','procdump.exe','vsjitdebugger.exe','kd.exe')
$taskCommands = foreach ($taskName in $taskNames) {
    $taskMatches = @(Get-Command $taskName -ErrorAction SilentlyContinue)
    [ordered]@{ name=$taskName; matches=@($taskMatches | ForEach-Object { [ordered]@{name=$_.Name; source=$_.Source; version=[string]$_.Version} }) }
}
$taskKnownPaths = @(
    'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe',
    'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\dbgeng.dll',
    'C:\Program Files (x86)\Windows Kits\10\Debuggers\sdk\inc\dbgeng.h',
    'C:\Program Files\Windows Kits\10\Debuggers\x64\cdb.exe',
    'C:\Windows\System32\dbgeng.dll', 'C:\Windows\System32\dbghelp.dll',
    'C:\Windows\System32\dbgcore.dll', 'C:\Windows\System32\dbgmodel.dll',
    'C:\Windows\System32\exts.dll', 'C:\Windows\System32\vsjitdebugger.exe',
    'C:\Windows\System32\kernel32.dll')
$taskFileRows = foreach ($taskPath in $taskKnownPaths) {
    if (Test-Path -LiteralPath $taskPath) {
        $taskItem = Get-Item -LiteralPath $taskPath -Force
        [ordered]@{path=$taskPath; exists=$true; bytes=$taskItem.Length; file_version=$taskItem.VersionInfo.FileVersion;
            sha256=(Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant()}
    } else { [ordered]@{path=$taskPath; exists=$false} }
}
$taskSearchRoots = @('C:\Program Files (x86)\Windows Kits', 'C:\Program Files\Microsoft Visual Studio',
    'C:\Program Files (x86)\Microsoft Visual Studio', 'T:\03-Toolchains\Codex-AI-Toolkit')
$taskSearches = foreach ($taskRoot in $taskSearchRoots) {
    if (!(Test-Path -LiteralPath $taskRoot)) { [ordered]@{root=$taskRoot; exists=$false}; continue }
    $taskSearchOutput = @(& rg --files --hidden -g 'cdb.exe' -g 'windbg.exe' -g 'windbgx.exe' -g 'ntsd.exe' -g 'gflags.exe' -g 'dbgeng.dll' -g 'dbgmodel.dll' -g 'exts.dll' -g 'dbgeng.h' -g 'msvsmon.exe' -g 'ntdll.pdb' $taskRoot 2>&1 | ForEach-Object { [string]$_ })
    $taskSearchExit = $LASTEXITCODE
    [ordered]@{root=$taskRoot; exists=$true; command='rg --files --hidden with exact debugger/header filename globs';
        exit_status=$taskSearchExit; output=$taskSearchOutput}
}
$taskAppxError = $null
try { $taskAppx = @(Get-AppxPackage -Name '*WinDbg*' -ErrorAction Stop | Select-Object Name,Version,InstallLocation) }
catch { $taskAppx=@(); $taskAppxError=[ordered]@{id=$_.FullyQualifiedErrorId; message=$_.Exception.Message} }
$taskAppDirError = $null
try { $taskAppDirectories = @(Get-ChildItem -LiteralPath 'C:\Program Files\WindowsApps' -Force -Directory -Filter '*WinDbg*' -ErrorAction Stop | ForEach-Object { $_.FullName }) }
catch { $taskAppDirectories=@(); $taskAppDirError=[ordered]@{id=$_.FullyQualifiedErrorId; message=$_.Exception.Message} }
$taskProviders = foreach ($taskProviderName in @('Microsoft-Windows-Loader','Microsoft-Windows-Kernel-Process')) {
    try {
        $taskProvider = Get-WinEvent -ListProvider $taskProviderName -ErrorAction Stop
        [ordered]@{query=$taskProviderName; status='FOUND'; name=$taskProvider.Name; id=[string]$taskProvider.Id;
            message_path=$taskProvider.MessageFilePath; resource_path=$taskProvider.ResourceFilePath;
            events=@($taskProvider.Events | ForEach-Object { [ordered]@{id=$_.Id; version=$_.Version;
                task_name=$_.Task.Name; task_value=$_.Task.Value; opcode_name=$_.Opcode.Name;
                template=$_.Template} })}
    } catch { [ordered]@{query=$taskProviderName; status='QUERY_ERROR'; error_id=$_.FullyQualifiedErrorId; error=$_.Exception.Message} }
}
$taskInventory = [ordered]@{at_utc=[DateTime]::UtcNow.ToString('o'); project=$taskProject;
    method='Read-only command/path/package/file/provider metadata inventory; no debugger/DLL/worker launched';
    command_resolution=$taskCommands; explicit_files=$taskFileRows; bounded_filename_searches=$taskSearches;
    windbg_appx=$taskAppx; windbg_appx_query_error=$taskAppxError; windbg_app_directories=$taskAppDirectories;
    windbg_app_directory_error=$taskAppDirError; symbol_path_present=[bool]$env:_NT_SYMBOL_PATH;
    alternate_symbol_path_present=[bool]$env:_NT_ALT_SYMBOL_PATH;
    limitations=@('Not an exhaustive machine-wide search','File presence is not successful engine loading or API capability validation',
        'Provider metadata is not a trace recording','No external/native engine startup or target attachment')}
[IO.File]::WriteAllText($taskInventoryPath,($taskInventory | ConvertTo-Json -Depth 9)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($taskProviderPath,([ordered]@{at_utc=[DateTime]::UtcNow.ToString('o'); providers=$taskProviders;
    trace_started=$false; flags_or_provider_state_changed=$false} | ConvertTo-Json -Depth 9)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
[pscustomobject]@{inventory=$taskInventoryPath; provider_metadata=$taskProviderPath; file_rows=@($taskFileRows).Count;
    found_files=@($taskFileRows | Where-Object {$_.exists}).Count; appx_packages=$taskAppx.Count;
    search_roots=@($taskSearches).Count} | ConvertTo-Json -Compress

# Read existing, bounded Windows events for the exact owned AC7 attempt.
# No tracing session, configuration change, process launch or profile operation.
$ErrorActionPreference = 'Stop'
$cetaEvidenceRoot = 'T:\00-Active\Project-AI-CETA\.agents\runtime\ac7-token-contract-20261020'
$cetaOutput = Join-Path $cetaEvidenceRoot 'startup-diagnostics-r1'
if (Test-Path -LiteralPath $cetaOutput) { throw 'FRESH_DIAGNOSTIC_OUTPUT_REQUIRED' }
$null = New-Item -ItemType Directory -Path $cetaOutput
$cetaStart = [DateTimeOffset]::Parse('2026-10-20T09:34:50+00:00').LocalDateTime
$cetaEnd = [DateTimeOffset]::Parse('2026-10-20T09:35:10+00:00').LocalDateTime
$cetaUuid = 'q-6be3c32cb832461093c6d15dc9c538f8'
$cetaRows = [System.Collections.Generic.List[object]]::new()
foreach ($cetaLog in @('Application', 'System', 'Microsoft-Windows-CodeIntegrity/Operational',
        'Microsoft-Windows-AppLocker/EXE and DLL', 'Microsoft-Windows-Windows Defender/Operational')) {
    $cetaObserved = [System.Collections.Generic.List[object]]::new()
    $cetaCount = 0
    try {
        $cetaEvents = @(Get-WinEvent -FilterHashtable @{ LogName = $cetaLog; StartTime = $cetaStart; EndTime = $cetaEnd } -MaxEvents 200 -ErrorAction Stop)
        $cetaCount = $cetaEvents.Count
        foreach ($cetaEvent in $cetaEvents) {
            $cetaXml = $cetaEvent.ToXml()
            $cetaOwnMatch = $cetaXml.Contains($cetaUuid)
            if (-not $cetaOwnMatch -and $cetaXml.Contains('isolated_worker.exe')) {
                [xml]$cetaDocument = $cetaXml
                foreach ($cetaField in @($cetaDocument.Event.EventData.Data)) {
                    if ($cetaField.Name -in @('ProcessId', 'ProcessID', 'FaultingProcessId')) {
                        $cetaText = [string]$cetaField.'#text'
                        try {
                            $cetaNumber = if ($cetaText.StartsWith('0x')) { [Convert]::ToUInt32($cetaText.Substring(2), 16) } else { [uint32]$cetaText }
                            if ($cetaNumber -in @(26536, 21160)) { $cetaOwnMatch = $true }
                        } catch { }
                    }
                }
            }
            if ($cetaOwnMatch) {
                if ($cetaXml.Length -gt 1048576) { throw 'OWN_EVENT_XML_SIZE_BOUND' }
                $cetaName = 'event-' + $cetaRows.Count + '-' + $cetaEvent.RecordId + '.xml'
                [IO.File]::WriteAllText((Join-Path $cetaOutput $cetaName), $cetaXml, [Text.UTF8Encoding]::new($false))
                $cetaObserved.Add([ordered]@{ provider = $cetaEvent.ProviderName; id = $cetaEvent.Id;
                    record_id = $cetaEvent.RecordId; timestamp_utc = $cetaEvent.TimeCreated.ToUniversalTime().ToString('o');
                    xml = $cetaName; match = 'exact_attempt_UUID_or_image_and_process_ID' })
            }
        }
        $cetaRows.Add([ordered]@{ log = $cetaLog; status = 'READ'; bounded_events_examined = $cetaCount;
            max_events = 200; at_limit = ($cetaCount -eq 200); matching = @($cetaObserved.ToArray()) })
    } catch {
        $cetaRows.Add([ordered]@{ log = $cetaLog; status = 'NO_RESULT_OR_INACCESSIBLE';
            error_id = $_.FullyQualifiedErrorId; error = $_.Exception.Message;
            bounded_events_examined = $cetaCount; matching = @($cetaObserved.ToArray()) })
    }
}
$cetaResult = [ordered]@{ at_utc = [DateTime]::UtcNow.ToString('o');
    interval_start_utc = $cetaStart.ToUniversalTime().ToString('o'); interval_end_utc = $cetaEnd.ToUniversalTime().ToString('o');
    worker_pid = 26536; ordinary_control_pid = 21160; attempt = $cetaUuid;
    operation = 'READ_EXISTING_TARGETED_EVENTS_ONLY'; logs = @($cetaRows.ToArray());
    profile_operations = @(); worker_launches = @(); system_configuration_changes = @();
    failed_DLL_identified = $false }
$cetaJson = $cetaResult | ConvertTo-Json -Depth 20
[IO.File]::WriteAllText((Join-Path $cetaOutput 'EVENT-OBSERVATIONS.json'), $cetaJson, [Text.UTF8Encoding]::new($false))
$cetaRows | ForEach-Object { [pscustomobject]@{ log = $_.log; status = $_.status; matched = @($_.matching).Count } } | ConvertTo-Json

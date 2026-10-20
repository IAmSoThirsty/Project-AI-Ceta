# Read-only PE/header/import inspection for one explicitly selected AC7 artifact.
# Supplemental local evidence: this is not a REA native-provider result.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$reviewRoot = 'T:\00-Active\Project-AI-CETA\.agents\runtime\ac7-native-artifact-review-20261020\R2'
$target = 'T:\00-Active\Project-AI-CETA\.agents\runtime\ac7-token-contract-20261020\build-r2\isolated_worker.exe'
$expected = '3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc'
$bytes = [IO.File]::ReadAllBytes($target)
$hashBefore = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hashBefore -ne $expected) { throw 'Artifact identity changed' }
if (-not [BitConverter]::IsLittleEndian) { throw 'Reader requires little endian host' }
function NeedRange([long]$offset,[long]$length) {
    if ($offset -lt 0 -or $length -lt 0 -or $offset -gt $bytes.LongLength - $length) { throw "Unmapped file range $offset + $length" }
}
function U16([long]$offset) { NeedRange $offset 2; [BitConverter]::ToUInt16($bytes,$offset) }
function U32([long]$offset) { NeedRange $offset 4; [BitConverter]::ToUInt32($bytes,$offset) }
function U64([long]$offset) { NeedRange $offset 8; [BitConverter]::ToUInt64($bytes,$offset) }
function AsciiZ([long]$offset) {
    NeedRange $offset 1
    $end = $offset
    while ($end -lt $bytes.LongLength -and $bytes[$end] -ne 0 -and $end - $offset -le 1024) { $end++ }
    if ($end -ge $bytes.LongLength -or $end - $offset -gt 1024) { throw "Unterminated/oversize ASCII string at $offset" }
    [Text.Encoding]::ASCII.GetString($bytes,$offset,$end-$offset)
}
function WriteNewJson([string]$name,$value) {
    $output = Join-Path $reviewRoot $name
    $jsonBytes = [Text.UTF8Encoding]::new($false).GetBytes(($value | ConvertTo-Json -Depth 24))
    $stream = [IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($jsonBytes,0,$jsonBytes.Length) } finally { $stream.Dispose() }
}
if ((U16 0) -ne 0x5a4d) { throw 'Missing MZ signature' }
$pe = [long](U32 0x3c)
NeedRange $pe 24
if ((U32 $pe) -ne 0x4550) { throw 'Missing PE signature' }
$coff = $pe + 4
$machine = U16 $coff
$sectionCount = U16 ($coff + 2)
$optionalSize = U16 ($coff + 16)
$characteristics = U16 ($coff + 18)
$optional = $pe + 24
NeedRange $optional $optionalSize
$magic = U16 $optional
if ($magic -ne 0x20b) { throw 'This bounded reader expects PE32+' }
$sizeOfHeaders = U32 ($optional + 60)
$directoryCount = U32 ($optional + 108)
if ($directoryCount -gt 16 -or 112 + $directoryCount * 8 -gt $optionalSize) { throw 'Unsupported/invalid directory count' }
$sections = [Collections.Generic.List[object]]::new()
for ($i=0; $i -lt $sectionCount; $i++) {
    $p = $optional + $optionalSize + 40 * $i
    NeedRange $p 40
    $rawName = [Text.Encoding]::ASCII.GetString($bytes,$p,8)
    $name = $rawName.TrimEnd([char]0)
    $rawOffset = U32 ($p + 20)
    $rawSize = U32 ($p + 16)
    if ($rawSize -gt 0) { NeedRange $rawOffset $rawSize }
    $flags = U32 ($p + 36)
    [void]$sections.Add([ordered]@{
        index=$i; header_file_offset=$p; name=$name; virtual_size=(U32 ($p+8))
        rva=(U32 ($p+12)); raw_file_offset=$rawOffset; raw_size=$rawSize
        characteristics=('0x{0:x8}' -f $flags)
        readable=(($flags -band 0x40000000) -ne 0)
        writable=(($flags -band 0x80000000L) -ne 0)
        executable=(($flags -band 0x20000000) -ne 0)
    })
}
function RvaOffset([uint64]$rva,[long]$length) {
    if ($rva -lt $sizeOfHeaders) { NeedRange ([long]$rva) $length; return [long]$rva }
    $matches = @($sections | Where-Object { $rva -ge $_.rva -and $rva -lt ([uint64]$_.rva + [uint64]$_.raw_size) })
    if ($matches.Count -ne 1) { throw "RVA has no unique file-backed section: $rva" }
    $section = $matches[0]
    $delta = $rva - [uint64]$section.rva
    if ($delta + [uint64]$length -gt [uint64]$section.raw_size) { throw "RVA range exceeds source section: $rva" }
    $offset = [long]([uint64]$section.raw_file_offset + $delta)
    NeedRange $offset $length
    return $offset
}
$directoryNames = @('export','import','resource','exception','certificate_file_table','base_relocation','debug','architecture','global_pointer','tls','load_config','bound_import','iat','delay_import','clr','reserved')
$directories = [Collections.Generic.List[object]]::new()
for ($i=0; $i -lt $directoryCount; $i++) {
    $p = $optional + 112 + $i*8
    [void]$directories.Add([ordered]@{index=$i;name=$directoryNames[$i];header_file_offset=$p;address=(U32 $p);size=(U32 ($p+4));address_kind=$(if($i -eq 4){'file-offset'}else{'RVA'})})
}
$imports = [Collections.Generic.List[object]]::new()
$importDirectory = $directories[1]
$descriptorTerminated = $false
$ordinalMask = [Convert]::ToUInt64('8000000000000000',16)
if ($importDirectory.address -ne 0) {
    $maxDescriptors = [Math]::Min(1024,[Math]::Floor($importDirectory.size/20))
    for ($i=0; $i -lt $maxDescriptors; $i++) {
        $descriptorRva = [uint64]$importDirectory.address + 20*$i
        $p = RvaOffset $descriptorRva 20
        $originalThunk = U32 $p
        $nameRva = U32 ($p+12)
        $firstThunk = U32 ($p+16)
        if ($originalThunk -eq 0 -and (U32 ($p+4)) -eq 0 -and (U32 ($p+8)) -eq 0 -and $nameRva -eq 0 -and $firstThunk -eq 0) { $descriptorTerminated=$true; break }
        $moduleOffset = RvaOffset $nameRva 1
        $module = AsciiZ $moduleOffset
        $thunkRva = $(if($originalThunk -ne 0){$originalThunk}else{$firstThunk})
        if ($thunkRva -eq 0) { throw "Missing thunk table for $module" }
        $entries = [Collections.Generic.List[object]]::new()
        $terminated = $false
        for ($j=0; $j -lt 8192; $j++) {
            $thunkOffset = RvaOffset ([uint64]$thunkRva + 8*$j) 8
            $value = U64 $thunkOffset
            if ($value -eq 0) { $terminated=$true; break }
            $row = [ordered]@{index=$j;thunk_file_offset=$thunkOffset;iat_rva=([uint64]$firstThunk+8*$j);raw_value=('0x{0:x16}' -f $value)}
            if (($value -band $ordinalMask) -ne 0) {
                $row.ordinal = ($value -band 0xffff); $row.name=$null; $row.hint=$null; $row.name_file_offset=$null
            } else {
                if ($value -gt 0xffffffffL) { throw 'Import name RVA exceeds 32 bits' }
                $nameOffset = RvaOffset $value 3
                $row.ordinal=$null; $row.hint=(U16 $nameOffset)
                $row.name=(AsciiZ ($nameOffset+2)); $row.name_file_offset=$nameOffset+2
            }
            [void]$entries.Add($row)
        }
        if (-not $terminated) { throw "Unterminated thunk table for $module" }
        [void]$imports.Add([ordered]@{module=$module;module_name_file_offset=$moduleOffset;descriptor_file_offset=$p;descriptor_rva=$descriptorRva;original_first_thunk_rva=$originalThunk;first_thunk_rva=$firstThunk;thunks_terminated=$terminated;functions=@($entries.ToArray())})
    }
    if (-not $descriptorTerminated) { throw 'Import descriptors lack a terminator within the declared directory' }
} else { $descriptorTerminated=$true }
$dllCharacteristics = U16 ($optional+70)
$hashAfter = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hashAfter -ne $hashBefore) { throw 'Artifact changed during inspection' }
$result = [ordered]@{
    kind='supplemental-local-read-only-pe-byte-inspection'; at_utc=[DateTime]::UtcNow.ToString('o')
    target=$target; sha256_before=$hashBefore; sha256_after=$hashAfter; bytes=$bytes.LongLength
    reader_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    pe_header_file_offset=$pe; machine=('0x{0:x4}' -f $machine); optional_magic=('0x{0:x4}' -f $magic)
    section_count=$sectionCount; coff_timestamp=(U32 ($coff+4)); symbol_table_file_offset=(U32 ($coff+8)); symbol_count=(U32 ($coff+12))
    characteristics=('0x{0:x4}' -f $characteristics); image_base=('0x{0:x16}' -f (U64 ($optional+24)))
    entry_point_rva=('0x{0:x8}' -f (U32 ($optional+16))); subsystem=(U16 ($optional+68))
    section_alignment=(U32 ($optional+32)); file_alignment=(U32 ($optional+36)); size_of_image=(U32 ($optional+56)); size_of_headers=$sizeOfHeaders
    dll_characteristics=('0x{0:x4}' -f $dllCharacteristics)
    static_header_flags=[ordered]@{
        high_entropy_va=(($dllCharacteristics -band 0x20) -ne 0); dynamic_base=(($dllCharacteristics -band 0x40) -ne 0)
        nx_compat=(($dllCharacteristics -band 0x100) -ne 0); guard_cf=(($dllCharacteristics -band 0x4000) -ne 0)
        appcontainer=(($dllCharacteristics -band 0x1000) -ne 0); relocations_stripped=(($characteristics -band 1) -ne 0)
    }
    sections=@($sections.ToArray()); data_directories=@($directories.ToArray()); import_descriptors_terminated=$descriptorTerminated
    imports=@($imports.ToArray()); coverage=[ordered]@{
        header='PE32+ optional header and declared section/directory tables'; normal_imports='All declared descriptors and terminated 64-bit name/ordinal thunk tables'
        delay_imports='Directory presence only; no delayed thunk decode'; load_config='Directory presence only; no load-config decode'
        signatures='Certificate directory presence only; no trust verification'; code='Not disassembled or executed'
    }
    limitations=@(
        'This local parser output is supplemental evidence, not a REA Evidence record.',
        'Static imports identify names in the normal import table, not executed calls or API ordering.',
        'Runtime dynamic library loading and indirect API resolution are not covered.',
        'Header flags record linker declarations, not runtime enforcement or security guarantees.',
        'No native isolation or authority-to-effect claim is established.',
        'COFF timestamp is unauthenticated file content; it does not prove build time.'
    )
}
WriteNewJson 'pe-byte-inspection.json' $result
[pscustomobject]@{sha256=$hashAfter;machine=$result.machine;magic=$result.optional_magic;sections=$sectionCount;modules=@($imports|ForEach-Object{$_.module});normal_import_count=(@($imports|ForEach-Object{$_.functions}).Count);flags=$result.static_header_flags} | ConvertTo-Json -Depth 5


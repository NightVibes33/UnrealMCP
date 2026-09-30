param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$EngineRoot = $env:UNREAL_ENGINE_ROOT,
    [string]$ExpectedVersion = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-EngineCandidates {
    $items = @()
    if ($EngineRoot) {
        $items += $EngineRoot
    }
    foreach ($base in @(
        "C:\Program Files\Epic Games",
        "D:\Epic Games",
        "E:\Epic Games",
        "D:\Program Files\Epic Games",
        "E:\Program Files\Epic Games"
    )) {
        if (Test-Path $base) {
            $items += Get-ChildItem $base -Directory -Filter "UE_*" -ErrorAction SilentlyContinue |
                ForEach-Object { $_.FullName }
        }
    }
    return $items | Select-Object -Unique
}

function Get-EngineVersionFromRoot([string]$Path) {
    $name = Split-Path $Path -Leaf
    if ($name -match 'UE_(\d+)\.(\d+)(?:\.(\d+))?') {
        $patch = if ($Matches[3]) { $Matches[3] } else { "0" }
        return [version]("$($Matches[1]).$($Matches[2]).$patch")
    }
    return [version]"0.0.0"
}

if (-not $EngineRoot) {
    $candidate = Get-EngineCandidates |
        Where-Object { Test-Path (Join-Path $_ "Engine\Binaries\Win64\UnrealEditor-Cmd.exe") } |
        Sort-Object { Get-EngineVersionFromRoot $_ } -Descending |
        Select-Object -First 1
    if (-not $candidate) {
        throw "No Unreal Engine installation found. Set UNREAL_ENGINE_ROOT or install UE on this self-hosted runner."
    }
    $EngineRoot = $candidate
}

$EngineRoot = (Resolve-Path $EngineRoot).Path
$RunUAT = Join-Path $EngineRoot "Engine\Build\BatchFiles\RunUAT.bat"
$Editor = Join-Path $EngineRoot "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

if (-not (Test-Path $RunUAT)) { throw "RunUAT not found: $RunUAT" }
if (-not (Test-Path $Editor)) { throw "UnrealEditor-Cmd not found: $Editor" }

$workBase = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$work = Join-Path $workBase ("UnrealMCPValidation-" + [guid]::NewGuid().ToString("N"))
$packageDir = Join-Path $work "Package"
$projectDir = Join-Path $work "Harness"
$pluginDir = Join-Path $projectDir "Plugins\UnrealMCP"
New-Item -ItemType Directory -Force -Path $packageDir, $pluginDir | Out-Null

Write-Host "Building UnrealMCP with: $EngineRoot"
& $RunUAT BuildPlugin "-Plugin=$RepoRoot\UnrealMCP.uplugin" "-Package=$packageDir" -TargetPlatforms=Win64
if ($LASTEXITCODE -ne 0) { throw "BuildPlugin failed with exit code $LASTEXITCODE" }

Copy-Item -Path (Join-Path $packageDir "*") -Destination $pluginDir -Recurse -Force

$projectFile = Join-Path $projectDir "UnrealMCPHarness.uproject"
$project = @{
    FileVersion = 3
    Category = ""
    Description = "Disposable UnrealMCP compatibility harness"
    Plugins = @(
        @{ Name = "UnrealMCP"; Enabled = $true },
        @{ Name = "PythonScriptPlugin"; Enabled = $true }
    )
}
$project | ConvertTo-Json -Depth 8 | Set-Content -Path $projectFile -Encoding UTF8

$compatApiDir = Join-Path $RepoRoot "compat\api"
$compatReportDir = Join-Path $RepoRoot "compat\reports"
New-Item -ItemType Directory -Force -Path $compatApiDir, $compatReportDir | Out-Null

$runtimeSnapshot = Join-Path $work "api-snapshot.json"
$smokeResult = Join-Path $work "smoke-result.json"
$env:UNREAL_MCP_API_SNAPSHOT = $runtimeSnapshot

$snapshotScript = Join-Path $RepoRoot "Automation\snapshot_unreal_api.py"
& $Editor $projectFile -unattended -nop4 -nosplash -nullrhi -NoSound "-ExecutePythonScript=$snapshotScript"
if ($LASTEXITCODE -ne 0) { throw "Unreal API snapshot failed with exit code $LASTEXITCODE" }
if (-not (Test-Path $runtimeSnapshot)) { throw "Unreal API snapshot was not produced" }

$snapshot = Get-Content $runtimeSnapshot -Raw | ConvertFrom-Json
$engineVersionString = [string]$snapshot.engine_version
if ($engineVersionString -notmatch '(\d+\.\d+(?:\.\d+)?)') {
    throw "Could not parse engine version: $engineVersionString"
}
$version = $Matches[1]
$parts = $version -split '\.'
$majorMinor = "$($parts[0]).$($parts[1])"

if ($ExpectedVersion -and -not ($majorMinor -eq $ExpectedVersion -or $version -eq $ExpectedVersion)) {
    throw "Runner Unreal version $version does not match expected docs version $ExpectedVersion. Update the self-hosted runner first."
}

$snapshotDest = Join-Path $compatApiDir ("ue-" + $version + ".json")
Copy-Item $runtimeSnapshot $snapshotDest -Force

$env:UNREAL_MCP_SMOKE_RESULT = $smokeResult
$smokeScript = Join-Path $RepoRoot "Automation\unreal_smoke_test.py"
& $Editor $projectFile -unattended -nop4 -nosplash -nullrhi -NoSound "-ExecutePythonScript=$smokeScript"
if ($LASTEXITCODE -ne 0) { throw "Unreal smoke test failed with exit code $LASTEXITCODE" }
if (-not (Test-Path $smokeResult)) { throw "Unreal smoke result was not produced" }

$smokeDest = Join-Path $compatReportDir ("ue-" + $version + "-smoke.json")
Copy-Item $smokeResult $smokeDest -Force

$previous = Get-ChildItem $compatApiDir -Filter "ue-*.json" -File |
    Where-Object { $_.FullName -ne $snapshotDest } |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1

$diffSafe = $true
$diffJson = Join-Path $compatReportDir ("ue-" + $version + "-api-diff.json")
$diffMd = Join-Path $compatReportDir ("ue-" + $version + "-api-diff.md")

if ($previous) {
    $diffScript = Join-Path $RepoRoot "Automation\diff_unreal_api.py"
    $diffArgs = @(
        $previous.FullName,
        $snapshotDest,
        "--json-out", $diffJson,
        "--markdown-out", $diffMd,
        "--repo-root", $RepoRoot
    )
    & python $diffScript @diffArgs
    if ($LASTEXITCODE -ne 0) { throw "API diff script failed" }
    $diff = Get-Content $diffJson -Raw | ConvertFrom-Json
    $diffSafe = [bool]$diff.safe_for_automatic_compatibility_merge
} else {
    @{
        schema = 1
        from_engine = $null
        to_engine = $engineVersionString
        baseline = $true
        breaking_count = 0
        referenced_breaking = @()
        safe_for_automatic_compatibility_merge = $true
    } | ConvertTo-Json -Depth 8 | Set-Content $diffJson -Encoding UTF8
    $nl = [Environment]::NewLine
    ("# Unreal Python API baseline" + $nl + $nl + "No previous API snapshot exists; this run establishes the baseline for UE $version." + $nl) |
        Set-Content $diffMd -Encoding UTF8
}

$smoke = Get-Content $smokeDest -Raw | ConvertFrom-Json
if (-not [bool]$smoke.passed) {
    throw "Live Unreal smoke test did not pass"
}

if ($env:GITHUB_OUTPUT) {
    "engine_version=$version" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "major_minor=$majorMinor" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "snapshot_path=$snapshotDest" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "smoke_path=$smokeDest" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "diff_safe=$($diffSafe.ToString().ToLowerInvariant())" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
}

Write-Host "UnrealMCP validation passed for Unreal $version"
Write-Host "API diff safe for automatic compatibility merge: $diffSafe"

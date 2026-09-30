param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$EngineRoot = $env:UNREAL_ENGINE_ROOT,
    [string]$ExpectedVersion = "",
    [int]$Port = 13377
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-VersionFromText([string]$Text) {
    $match = [regex]::Match($Text, '(\d+)\.(\d+)(?:\.(\d+))?')
    if (-not $match.Success) {
        return [version]"0.0.0"
    }
    $patch = if ($match.Groups[3].Success) { [int]$match.Groups[3].Value } else { 0 }
    return [version]::new(
        [int]$match.Groups[1].Value,
        [int]$match.Groups[2].Value,
        $patch
    )
}

function Add-EngineCandidate(
    [System.Collections.ArrayList]$List,
    [string]$Path,
    [string]$VersionHint
) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    try {
        $resolved = (Resolve-Path $Path -ErrorAction Stop).Path
    } catch {
        return
    }

    $editor = Join-Path $resolved "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
    $interactiveEditor = Join-Path $resolved "Engine\Binaries\Win64\UnrealEditor.exe"
    $uat = Join-Path $resolved "Engine\Build\BatchFiles\RunUAT.bat"
    if ((Test-Path $editor) -and (Test-Path $interactiveEditor) -and (Test-Path $uat)) {
        [void]$List.Add([pscustomobject]@{
            Root = $resolved
            Editor = $editor
            InteractiveEditor = $interactiveEditor
            RunUAT = $uat
            Version = Get-VersionFromText ($VersionHint + " " + $resolved)
        })
    }
}

function Get-EngineCandidates {
    $items = [System.Collections.ArrayList]::new()

    if ($EngineRoot) {
        Add-EngineCandidate $items $EngineRoot $ExpectedVersion
    }

    $launcherManifest = "C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat"
    if (Test-Path $launcherManifest) {
        try {
            $launcher = Get-Content $launcherManifest -Raw | ConvertFrom-Json
            foreach ($entry in $launcher.InstallationList) {
                if ([string]$entry.AppName -like "UE_*") {
                    Add-EngineCandidate $items ([string]$entry.InstallLocation) ([string]$entry.AppName)
                }
            }
        } catch {
            Write-Warning "Unable to parse Epic Launcher manifest: $_"
        }
    }

    foreach ($base in @(
        "C:\Program Files\Epic Games",
        "D:\Epic Games",
        "E:\Epic Games",
        "D:\Program Files\Epic Games",
        "E:\Program Files\Epic Games"
    )) {
        if (Test-Path $base) {
            Get-ChildItem $base -Directory -Filter "UE_*" -ErrorAction SilentlyContinue | ForEach-Object {
                Add-EngineCandidate $items $_.FullName $_.Name
            }
        }
    }

    return $items | Sort-Object Root -Unique
}

function Select-Engine {
    $candidates = @(Get-EngineCandidates)
    if (-not $candidates) {
        throw "No Unreal Engine installation found. Set UNREAL_ENGINE_ROOT or install Unreal on this self-hosted runner."
    }

    if ($EngineRoot) {
        $explicit = $candidates | Where-Object { $_.Root -eq (Resolve-Path $EngineRoot).Path } | Select-Object -First 1
        if ($explicit) {
            return $explicit
        }
    }

    if ($ExpectedVersion) {
        $expected = Get-VersionFromText $ExpectedVersion
        $matching = @(
            $candidates | Where-Object {
                $_.Version.Major -eq $expected.Major -and
                $_.Version.Minor -eq $expected.Minor
            } | Sort-Object Version -Descending
        )
        if ($matching.Count -gt 0) {
            return $matching[0]
        }

        $unknownVersion = @($candidates | Where-Object { $_.Version -eq [version]"0.0.0" })
        if ($unknownVersion.Count -eq 1) {
            return $unknownVersion[0]
        }

        throw "No installed Unreal Engine matches expected version $ExpectedVersion. Installed candidates: $($candidates.Version -join ', ')"
    }

    return ($candidates | Sort-Object Version -Descending | Select-Object -First 1)
}

function Get-SnapshotVersion([System.IO.FileInfo]$File) {
    try {
        $payload = Get-Content $File.FullName -Raw | ConvertFrom-Json
        return Get-VersionFromText ([string]$payload.engine_version)
    } catch {
        return [version]"0.0.0"
    }
}

$engine = Select-Engine
$EngineRoot = $engine.Root
$RunUAT = $engine.RunUAT
$Editor = $engine.Editor
$InteractiveEditor = $engine.InteractiveEditor

Write-Host "Using Unreal Engine: $EngineRoot"
Write-Host "Install version hint: $($engine.Version)"

$workBase = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$work = Join-Path $workBase ("UnrealMCPValidation-" + [guid]::NewGuid().ToString("N"))
$packageDir = Join-Path $work "Package"
$projectDir = Join-Path $work "Harness"
$pluginDir = Join-Path $projectDir "Plugins\UnrealMCP"
New-Item -ItemType Directory -Force -Path $packageDir, $pluginDir | Out-Null

Write-Host "Building UnrealMCP with RunUAT BuildPlugin..."
& $RunUAT BuildPlugin "-Plugin=$RepoRoot\UnrealMCP.uplugin" "-Package=$packageDir" -TargetPlatforms=Win64
if ($LASTEXITCODE -ne 0) {
    throw "BuildPlugin failed with exit code $LASTEXITCODE"
}

Copy-Item -Path (Join-Path $packageDir "*") -Destination $pluginDir -Recurse -Force

$projectFile = Join-Path $projectDir "UnrealMCPHarness.uproject"
$project = @{
    FileVersion = 3
    Category = ""
    Description = "Disposable UnrealMCP compatibility harness"
    Plugins = @(
        @{ Name = "UnrealMCP"; Enabled = $true },
        @{ Name = "PythonScriptPlugin"; Enabled = $true },
        @{ Name = "EditorScriptingUtilities"; Enabled = $true }
    )
}
$project | ConvertTo-Json -Depth 8 | Set-Content -Path $projectFile -Encoding UTF8

$compatApiDir = Join-Path $RepoRoot "compat\api"
$compatReportDir = Join-Path $RepoRoot "compat\reports"
New-Item -ItemType Directory -Force -Path $compatApiDir, $compatReportDir | Out-Null

$runtimeSnapshot = Join-Path $work "api-snapshot.json"
$directSmokeResult = Join-Path $work "unreal-api-smoke.json"
$nativeSmokeResult = Join-Path $work "native-mcp-smoke.json"

$env:UNREAL_MCP_API_SNAPSHOT = $runtimeSnapshot
$snapshotScript = Join-Path $RepoRoot "Automation\snapshot_unreal_api.py"

Write-Host "Capturing reflected Unreal Python API..."
& $Editor $projectFile -unattended -nop4 -nosplash -nullrhi -NoSound "-ExecutePythonScript=$snapshotScript"
if ($LASTEXITCODE -ne 0) {
    throw "Unreal API snapshot failed with exit code $LASTEXITCODE"
}
if (-not (Test-Path $runtimeSnapshot)) {
    throw "Unreal API snapshot was not produced"
}

$snapshot = Get-Content $runtimeSnapshot -Raw | ConvertFrom-Json
$engineVersionString = [string]$snapshot.engine_version
if ($engineVersionString -notmatch '(\d+\.\d+(?:\.\d+)?)') {
    throw "Could not parse engine version: $engineVersionString"
}
$version = $Matches[1]
$parts = $version -split '\.'
$majorMinor = "$($parts[0]).$($parts[1])"

if ($ExpectedVersion -and -not ($majorMinor -eq $ExpectedVersion -or $version -eq $ExpectedVersion)) {
    throw "Runner Unreal version $version does not match expected docs version $ExpectedVersion. Install the expected engine version on this runner."
}

$env:UNREAL_MCP_SMOKE_RESULT = $directSmokeResult
$directSmokeScript = Join-Path $RepoRoot "Automation\unreal_smoke_test.py"

Write-Host "Running direct Unreal editor API smoke test..."
& $Editor $projectFile -unattended -nop4 -nosplash -nullrhi -NoSound "-ExecutePythonScript=$directSmokeScript"
if ($LASTEXITCODE -ne 0) {
    throw "Unreal API smoke test failed with exit code $LASTEXITCODE"
}
if (-not (Test-Path $directSmokeResult)) {
    throw "Unreal API smoke result was not produced"
}

$directSmoke = Get-Content $directSmokeResult -Raw | ConvertFrom-Json
if (-not [bool]$directSmoke.passed) {
    throw "Direct Unreal API smoke test did not pass"
}

Write-Host "Running native UnrealMCP TCP bridge smoke test..."
$projectArg = '"' + $projectFile + '"'
$editorArgs = @(
    $projectArg,
    "-UnrealMCPServer",
    "-UnrealMCPPort=$Port",
    "-unattended",
    "-nop4",
    "-nosplash",
    "-nullrhi",
    "-NoSound",
    "-log"
)

$editorProcess = Start-Process -FilePath $InteractiveEditor -ArgumentList $editorArgs -PassThru
try {
    $bridgeSmokeScript = Join-Path $RepoRoot "Automation\mcp_bridge_smoke_test.py"
    $bridgeArgs = @(
        $bridgeSmokeScript,
        "--port", [string]$Port,
        "--wait-seconds", "240",
        "--json-out", $nativeSmokeResult
    )
    & python @bridgeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Native UnrealMCP bridge smoke test failed with exit code $LASTEXITCODE"
    }
}
finally {
    if ($editorProcess -and -not $editorProcess.HasExited) {
        Stop-Process -Id $editorProcess.Id -Force -ErrorAction SilentlyContinue
        try {
            $editorProcess.WaitForExit(30000)
        } catch {
        }
    }
}

if (-not (Test-Path $nativeSmokeResult)) {
    throw "Native UnrealMCP bridge smoke result was not produced"
}

$snapshotDest = Join-Path $compatApiDir ("ue-" + $version + ".json")
$previousSnapshot = Join-Path $work "previous-api-snapshot.json"
$hasPrevious = $false

if (Test-Path $snapshotDest) {
    Copy-Item $snapshotDest $previousSnapshot -Force
    $hasPrevious = $true
} else {
    $currentVersion = Get-VersionFromText $version
    $candidateSnapshots = @(
        Get-ChildItem $compatApiDir -Filter "ue-*.json" -File -ErrorAction SilentlyContinue |
            Where-Object { (Get-SnapshotVersion $_) -lt $currentVersion } |
            Sort-Object { Get-SnapshotVersion $_ } -Descending
    )
    if ($candidateSnapshots.Count -gt 0) {
        Copy-Item $candidateSnapshots[0].FullName $previousSnapshot -Force
        $hasPrevious = $true
    }
}

Copy-Item $runtimeSnapshot $snapshotDest -Force

$directSmokeDest = Join-Path $compatReportDir ("ue-" + $version + "-smoke.json")
$nativeSmokeDest = Join-Path $compatReportDir ("ue-" + $version + "-native-mcp-smoke.json")
Copy-Item $directSmokeResult $directSmokeDest -Force
Copy-Item $nativeSmokeResult $nativeSmokeDest -Force

$diffSafe = $true
$diffJson = Join-Path $compatReportDir ("ue-" + $version + "-api-diff.json")
$diffMd = Join-Path $compatReportDir ("ue-" + $version + "-api-diff.md")

if ($hasPrevious) {
    $diffScript = Join-Path $RepoRoot "Automation\diff_unreal_api.py"
    $diffArgs = @(
        $previousSnapshot,
        $snapshotDest,
        "--json-out", $diffJson,
        "--markdown-out", $diffMd,
        "--repo-root", $RepoRoot
    )
    & python $diffScript @diffArgs
    if ($LASTEXITCODE -ne 0) {
        throw "API diff script failed"
    }
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

if ($env:GITHUB_OUTPUT) {
    "engine_version=$version" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "major_minor=$majorMinor" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "snapshot_path=$snapshotDest" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "smoke_path=$directSmokeDest" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "native_smoke_path=$nativeSmokeDest" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "diff_safe=$($diffSafe.ToString().ToLowerInvariant())" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
}

Write-Host "UnrealMCP validation passed for Unreal $version"
Write-Host "Plugin build: PASS"
Write-Host "Direct Unreal API smoke: PASS"
Write-Host "Native MCP TCP bridge smoke: PASS"
Write-Host "API diff safe for automatic compatibility merge: $diffSafe"

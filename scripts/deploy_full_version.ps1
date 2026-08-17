[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDir,

    [Parameter(Mandatory = $true)]
    [string]$DestinationDir,

    [Parameter(Mandatory = $true)]
    [string]$DesktopDir
)

$ErrorActionPreference = "Stop"

function Test-HasUserData {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }
    return $null -ne (Get-ChildItem -LiteralPath $Path -Recurse -File |
        Select-Object -First 1)
}

if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    throw "Build output directory does not exist: $SourceDir"
}

$stageRoot = Join-Path $env:TEMP ("PaperAssistant-user-data-" + [guid]::NewGuid().ToString("N"))
$stageData = Join-Path $stageRoot "paper_project"
$sources = New-Object System.Collections.Generic.List[string]
$success = $false

try {
    New-Item -ItemType Directory -Path $stageData -Force | Out-Null

    $legacyDesktopData = Join-Path $DesktopDir "paper_project"
    if (Test-HasUserData $legacyDesktopData) {
        $sources.Add($legacyDesktopData)
    }

    $previousPackages = Get-ChildItem -LiteralPath $DesktopDir -Directory |
        Where-Object {
            $_.FullName -ne $DestinationDir -and
            $_.Name -like "*_v*" -and
            (Test-Path -LiteralPath (Join-Path $_.FullName "_internal") -PathType Container) -and
            (Test-HasUserData (Join-Path $_.FullName "paper_project"))
        } |
        Sort-Object LastWriteTime
    foreach ($package in $previousPackages) {
        $sources.Add((Join-Path $package.FullName "paper_project"))
    }

    $currentData = Join-Path $DestinationDir "paper_project"
    if (Test-HasUserData $currentData) {
        $sources.Add($currentData)
    }

    foreach ($source in $sources) {
        Get-ChildItem -LiteralPath $source -Force |
            Copy-Item -Destination $stageData -Recurse -Force
    }

    if (Test-Path -LiteralPath $DestinationDir) {
        Remove-Item -LiteralPath $DestinationDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $DestinationDir -Force | Out-Null
    Get-ChildItem -LiteralPath $SourceDir -Force |
        Copy-Item -Destination $DestinationDir -Recurse -Force

    if (Test-HasUserData $stageData) {
        $destinationData = Join-Path $DestinationDir "paper_project"
        New-Item -ItemType Directory -Path $destinationData -Force | Out-Null
        Get-ChildItem -LiteralPath $stageData -Force |
            Copy-Item -Destination $destinationData -Recurse -Force
    }

    $success = $true
    "DEPLOYED=$DestinationDir"
    "USER_DATA_SOURCES=" + ($sources -join "|")
}
finally {
    if ($success -and (Test-Path -LiteralPath $stageRoot)) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
    elseif (-not $success) {
        Write-Warning "Deployment failed. User data staging was retained at: $stageRoot"
    }
}

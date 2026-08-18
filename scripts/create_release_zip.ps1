[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
$pattern = "_v$([regex]::Escape($Version))$"
$source = Get-ChildItem -LiteralPath $dist -Directory |
    Where-Object { $_.Name -match $pattern } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $source) {
    throw "Built directory not found for v$Version"
}
$destination = Join-Path $root "paperassistant-v${Version}-full.zip"
Compress-Archive -LiteralPath $source.FullName -DestinationPath $destination -Force
if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
    throw "ZIP creation failed: $destination"
}
"CREATED=$destination"

# Version: v2.3.0 (2026-08-19) Update: encoding-safe release ZIP creation

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [ValidateSet("exe", "zip")]
    [string]$Kind
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $root "release_assets"
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

if ($Kind -eq "exe") {
    $source = Get-ChildItem -LiteralPath (Join-Path $root "dist") -File |
        Where-Object { $_.Name -match "_v$([regex]::Escape($Version))\.exe$" } |
        Select-Object -First 1
    $destination = Join-Path $releaseDir "论文助手_v${Version}_单文件版.exe"
}
else {
    $source = Get-Item -LiteralPath (Join-Path $root "论文助手_v${Version}.zip")
    $destination = Join-Path $releaseDir "论文助手_v${Version}_完整版.zip"
}

if (-not $source -or -not (Test-Path -LiteralPath $source.FullName -PathType Leaf)) {
    throw "Release source asset not found for v$Version ($Kind)"
}
Copy-Item -LiteralPath $source.FullName -Destination $destination -Force
if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
    throw "Release asset copy failed: $destination"
}
"COPIED=$destination"

# 版本: v2.2.0 (2026-08-18) 更新: 中文发布资产复制

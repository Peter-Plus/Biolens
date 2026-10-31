$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:BIOLENS_DATA = Join-Path $projectRoot '.local\app-data'
$version = (Get-Content -LiteralPath (Join-Path $projectRoot 'package.json') -Raw | ConvertFrom-Json).version
$appExe = Join-Path $projectRoot "release\$version\win-unpacked\BioLens.exe"
if (Test-Path -LiteralPath $appExe) {
    Start-Process -FilePath $appExe -WorkingDirectory $projectRoot -WindowStyle Hidden
} else {
    Set-Location -LiteralPath $projectRoot
    npm.cmd start
}

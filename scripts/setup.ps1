param([string]$Python = "python")
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.venv')) { & $Python -m venv .venv }
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ required.' }
$bioPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $bioPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $bioPython scripts/bootstrap.py
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $projectRoot '.local\browsers'
& $bioPython -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed.' }
npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'Node dependency installation failed.' }
Write-Output 'Ready. Run npm run desktop.'

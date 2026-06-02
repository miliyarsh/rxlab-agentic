# Build a Lambda deployment zip: service/ package + pydantic (boto3 is in the runtime).
param(
  [Parameter(Mandatory = $true)]
  [string]$OutputZip
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Staging = Join-Path $Root ".build\lambda-package\staging"

if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

python -m pip install --quiet --disable-pip-version-check `
  --target $Staging `
  "pydantic>=2.6,<3"

Copy-Item -Recurse (Join-Path $Root "service") (Join-Path $Staging "service")
$testsPath = Join-Path $Staging "service\tests"
if (Test-Path $testsPath) { Remove-Item -Recurse -Force $testsPath }

$outDir = Split-Path -Parent $OutputZip
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
if (Test-Path $OutputZip) { Remove-Item -Force $OutputZip }

python -c @"
import pathlib, zipfile
out = pathlib.Path(r'$OutputZip')
staging = pathlib.Path(r'$Staging')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for path in staging.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and not path.name.endswith('.pyc'):
            zf.write(path, path.relative_to(staging).as_posix())
"@

Write-Host "Packaged $OutputZip"

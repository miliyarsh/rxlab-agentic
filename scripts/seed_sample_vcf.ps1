# Upload the demo VCF fixture to the environment reports bucket.
param(
    [string]$EnvDir = "infra/envs/dev",
    [string]$Fixture = "service/agents/intake/fixtures/sample.vcf",
    [string]$Key = "samples/sample.vcf"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$envDirPath = if ([System.IO.Path]::IsPathRooted($EnvDir)) { $EnvDir } else { Join-Path $Root $EnvDir }
$fixturePath = if ([System.IO.Path]::IsPathRooted($Fixture)) { $Fixture } else { Join-Path $Root $Fixture }
if (-not (Test-Path $fixturePath)) {
    Write-Error "Fixture not found: $fixturePath"
}

$bucket = terraform -chdir="$envDirPath" output -raw reports_bucket_name
aws s3 cp $fixturePath "s3://$bucket/$Key"
Write-Host "Uploaded s3://$bucket/$Key"

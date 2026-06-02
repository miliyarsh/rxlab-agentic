# End-to-end demo against the deployed dev API (PowerShell).
param(
    [string]$EnvDir = "infra/envs/dev",
    [string]$ApiUrl = $env:API_URL,
    [string]$VcfUrl = $env:VCF_URL,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$envDirPath = if ([System.IO.Path]::IsPathRooted($EnvDir)) { $EnvDir } else { Join-Path $Root $EnvDir }

if (-not $ApiUrl) {
    $ApiUrl = terraform -chdir="$envDirPath" output -raw api_url
}
$ApiUrl = $ApiUrl.TrimEnd("/")

if (-not $VcfUrl) {
    & "$PSScriptRoot/seed_sample_vcf.ps1" -EnvDir $envDirPath | Out-Null
    $bucket = terraform -chdir="$envDirPath" output -raw reports_bucket_name
    $VcfUrl = "s3://$bucket/samples/sample.vcf"
}

Write-Host "API: $ApiUrl"
Write-Host "VCF: $VcfUrl"
Write-Host "Healthz:"
(Invoke-RestMethod -Uri "$ApiUrl/healthz") | ConvertTo-Json

Write-Host "Submitting job..."
$body = @{
    sample_id = "demo-$(Get-Date -Format 'yyyyMMddHHmmss')"
    vcf_url   = $VcfUrl
} | ConvertTo-Json
$job = Invoke-RestMethod -Uri "$ApiUrl/jobs" -Method POST -ContentType "application/json" -Body $body
Write-Host "job_id=$($job.job_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$status = "pending"
do {
    Start-Sleep -Seconds 5
    $j = Invoke-RestMethod -Uri "$ApiUrl/jobs/$($job.job_id)"
    $status = $j.status
    Write-Host "status=$status"
} while ((Get-Date) -lt $deadline -and $status -notin @("succeeded", "failed"))

if ($status -ne "succeeded") {
    Write-Error "Job did not succeed (status=$status)."
}

Write-Host "Report URL:"
(Invoke-RestMethod -Uri "$ApiUrl/jobs/$($job.job_id)/report") | ConvertTo-Json

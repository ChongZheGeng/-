param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "[dev-init] script start"
if (-not $env:DEV_ADMIN_PASSWORD) {
    $env:DEV_ADMIN_PASSWORD = "hedgehog123"
    Write-Host "[dev-init] DEV_ADMIN_PASSWORD not set, use default development password"
}

Write-Host "[dev-init] invoke manage.py init_dev_data"
& $PythonExe manage.py init_dev_data
if ($LASTEXITCODE -ne 0) {
    throw "[dev-init] init_dev_data failed with exit code $LASTEXITCODE"
}

Write-Host "[dev-init] script done"

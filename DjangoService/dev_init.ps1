param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptRoot) {
    $scriptRoot = Get-Location
}

Push-Location $scriptRoot
try {
    Write-Host "[dev-init] script start cwd=$((Get-Location).Path)"
    if (-not $env:DEV_ADMIN_PASSWORD) {
        $env:DEV_ADMIN_PASSWORD = "hedgehog123"
        Write-Host "[dev-init] DEV_ADMIN_PASSWORD not set, use default development password"
    }

    Write-Host "[dev-init] invoke manage.py init_dev_data"
    & $PythonExe manage.py init_dev_data
    if ($LASTEXITCODE -ne 0) {
        throw "[dev-init] init_dev_data failed with exit code $LASTEXITCODE"
    }

    Write-Host "[dev-init] initialization success"
}
finally {
    Pop-Location
}

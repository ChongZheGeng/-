$healthUrl = "http://127.0.0.1:8000/api/health/"

try {
    $result = Invoke-RestMethod -Uri $healthUrl -Method GET -TimeoutSec 5
    Write-Host "健康检查成功:" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "健康检查失败：后端未启动/端口不对/路由不存在" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    exit 1
}

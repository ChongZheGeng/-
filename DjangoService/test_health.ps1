$uri = "http://127.0.0.1:8000/api/health/"

try {
    $response = Invoke-RestMethod -Uri $uri -Method GET -TimeoutSec 5
    Write-Host "健康检查成功：$($response.status) $($response.time)" -ForegroundColor Green
}
catch {
    Write-Host "健康检查失败：无法访问 $uri" -ForegroundColor Red
    Write-Host "请确认 Django 后端已启动，命令：python manage.py runserver 127.0.0.1:8000" -ForegroundColor Yellow
    exit 1
}

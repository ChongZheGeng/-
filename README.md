# -
前端&后端

## 启动顺序（Windows）
1. 先启动 Django 后端（在 `DjangoService` 目录）：
   ```powershell
   python manage.py runserver 127.0.0.1:8000
   ```
2. 再启动 PyQt 客户端（在仓库根目录）：
   ```powershell
   python pyQTClient/demo.py
   ```

## 后端健康检查
推荐优先用以下命令检查后端是否可用：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/health/ -Method GET
```

或运行脚本：

```powershell
./DjangoService/test_health.ps1
```

## 关于 PowerShell 的 `curl`
PowerShell 中 `curl` 往往是 `Invoke-WebRequest` 的别名，不是 `curl.exe`。
如需使用真正的 curl，请明确写：

```powershell
curl.exe http://127.0.0.1:8000/api/health/
```

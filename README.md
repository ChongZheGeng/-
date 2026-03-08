# -
前端&后端

## 开发环境快速启动（SQLite）

```bash
cd DjangoService
python manage.py init_dev_data
python manage.py runserver 127.0.0.1:8000
```

前端：

```bash
cd pyQTClient
python demo.py
```

默认开发管理员账号：`hedgehog`，密码来自 `DEV_ADMIN_PASSWORD`（默认 `hedgehog123`）。


Windows PowerShell 初始化（可直接复制）：

```powershell
Set-Location "F:\python\dachuang\DjangoService"
powershell -ExecutionPolicy Bypass -File .\dev_init.ps1
```


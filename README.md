# 复合材料加工数据管理系统

包含：
- `DjangoService/`：后端（Django + DRF）
- `pyQTClient/`：桌面客户端（PyQt）

## WebDAV 配置说明

在客户端设置页面可配置以下项：
- WebDAV URL
- 用户名
- 密码
- 启用开关

## 传感器数据上传策略

系统支持两种上传路径：

1. **WebDAV 已配置并启用**
   - 客户端先上传到 WebDAV
   - 然后创建传感器数据记录

2. **WebDAV 未配置（fallback）**
   - 客户端直接调用后端 HTTP 上传接口
   - 后端保存文件到 `MEDIA_ROOT/sensor_data/`
   - 后端返回 `file_url` 并写入数据库

接口路径：
- `POST /api/sensor-data/upload/`

## Windows 测试示例

### curl.exe

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/sensor-data/upload/" ^
  -F "file=@C:/temp/demo.csv" ^
  -F "processing_task=1" ^
  -F "sensor_type=temperature" ^
  -F "sensor_id=T-01" ^
  -F "description=fallback upload"
```

### Invoke-RestMethod

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/sensor-data/upload/" -Form @{
  file = Get-Item "C:/temp/demo.csv"
  processing_task = 1
  sensor_type = "temperature"
  sensor_id = "T-01"
  description = "fallback upload"
}
```

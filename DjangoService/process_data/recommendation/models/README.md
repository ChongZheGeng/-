# 模型文件说明

`process_data/recommendation/models/` 目录用于存放推荐服务加载的模型与配置文件。

如果该目录缺少以下文件，`service.py` 在启动或调用推荐接口时会因为找不到模型资源而报错：

- `model_config.json`
- `*.joblib`（一个或多个模型文件，文件名需与 `model_config.json` 中配置一致）

请将训练产出的 `joblib` 模型文件和对应的 `model_config.json` 一并放入本目录。

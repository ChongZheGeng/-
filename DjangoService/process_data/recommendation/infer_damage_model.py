from __future__ import annotations

import json
from pathlib import Path

from .serialization import load_object


def _load_artifacts():
    base = Path(__file__).resolve().parent
    model_path = base / "model.pkl"
    config_path = base / "level_config.json"
    if not model_path.exists() or not config_path.exists():
        raise FileNotFoundError("模型文件不存在，请先调用训练接口生成 model.pkl 和 level_config.json。")
    model_bundle = load_object(model_path)
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    return model_bundle, cfg


def _resolve_level(value: float, ranges: dict) -> str:
    if value <= ranges["low"][1]:
        return "low"
    if value <= ranges["medium"][1]:
        return "medium"
    return "high"


def predict_damage(speed: float, feed: float):
    model_bundle, cfg = _load_artifacts()
    model = model_bundle["model"]
    try:
        import numpy as np
    except Exception as exc:
        raise RuntimeError("缺少 numpy 依赖，无法执行预测") from exc
    pred = float(model.predict(np.array([[speed, feed]], dtype=float))[0])
    level = _resolve_level(pred, cfg["level_ranges"])
    return {
        "predicted_damage_A": pred,
        "level": level,
    }

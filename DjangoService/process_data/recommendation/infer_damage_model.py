"""单点 A_damage 预测。"""

from __future__ import annotations

import json
import pickle
from typing import Dict

from .generate_damage_dataset import LEVEL_CONFIG_PATH
from .train_damage_model import MODEL_PATH, _features_linear, _features_poly2, _predict_custom


def _map_level(value: float, config: Dict[str, object]) -> str:
    t = config.get("thresholds", {})
    low_max = float(t.get("low_max", 0))
    medium_max = float(t.get("medium_max", 0))
    if value <= low_max:
        return "low"
    if value <= medium_max:
        return "medium"
    return "high"


def _predict_by_payload(payload: Dict[str, object], speed: float, fz: float) -> float:
    backend = payload.get("backend")
    if backend == "sklearn":
        model = payload["model"]
        return float(model.predict([[speed, fz]])[0])

    model_name = payload.get("model_name")
    if model_name == "LinearRegression":
        return _predict_custom(payload["coef_linear"], _features_linear(speed, fz))
    return _predict_custom(payload["coef_poly2"], _features_poly2(speed, fz))


def predict_damage(speed: float, fz: float) -> Dict[str, object]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"模型文件不存在: {MODEL_PATH}")
    if not LEVEL_CONFIG_PATH.exists():
        raise FileNotFoundError(f"等级配置不存在: {LEVEL_CONFIG_PATH}")

    with MODEL_PATH.open("rb") as f:
        model_payload = pickle.load(f)
    level_config = json.loads(LEVEL_CONFIG_PATH.read_text(encoding="utf-8"))

    pred = max(0.001, _predict_by_payload(model_payload, speed, fz))
    level = _map_level(pred, level_config)
    return {"speed": speed, "fz": fz, "predicted_A_damage": pred, "damage_level": level}


if __name__ == "__main__":
    print(predict_damage(5000, 0.05))

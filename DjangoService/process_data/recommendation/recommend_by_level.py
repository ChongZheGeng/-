"""按目标损伤等级推荐 speed/fz 参数组合。"""

from __future__ import annotations

import json
import pickle
import random
from typing import Dict, List

from .generate_damage_dataset import LEVEL_CONFIG_PATH, SPEED_MAX, SPEED_MIN, FZ_MAX, FZ_MIN
from .infer_damage_model import _map_level, _predict_by_payload
from .train_damage_model import MODEL_PATH


def recommend_parameters_by_level(damage_level: str, top_k: int = 5, random_state: int = 42) -> List[Dict[str, object]]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"模型文件不存在: {MODEL_PATH}")
    if not LEVEL_CONFIG_PATH.exists():
        raise FileNotFoundError(f"等级配置不存在: {LEVEL_CONFIG_PATH}")

    damage_level = (damage_level or "").strip().lower()
    if damage_level not in {"low", "medium", "high"}:
        raise ValueError("damage_level 必须是 low / medium / high")

    with MODEL_PATH.open("rb") as f:
        model_payload = pickle.load(f)
    level_config = json.loads(LEVEL_CONFIG_PATH.read_text(encoding="utf-8"))

    random.seed(random_state)
    candidates = []
    for i in range(45):
        for j in range(45):
            base_speed = SPEED_MIN + (SPEED_MAX - SPEED_MIN) * i / 44
            base_fz = FZ_MIN + (FZ_MAX - FZ_MIN) * j / 44
            speed = min(SPEED_MAX, max(SPEED_MIN, base_speed + random.gauss(0, 80)))
            fz = min(FZ_MAX, max(FZ_MIN, base_fz + random.gauss(0, 0.001)))
            candidates.append((speed, fz))

    results = []
    for speed, fz in candidates:
        pred = max(0.001, _predict_by_payload(model_payload, speed, fz))
        lv = _map_level(pred, level_config)
        if lv == damage_level:
            results.append({
                "speed": round(speed, 4),
                "fz": round(fz, 6),
                "predicted_A_damage": round(pred, 6),
                "damage_level": lv,
            })

    results.sort(key=lambda x: x["predicted_A_damage"])
    if damage_level == "high":
        results.reverse()

    if len(results) <= top_k:
        return results
    step = max(1, len(results) // top_k)
    return results[::step][:top_k]


if __name__ == "__main__":
    print(recommend_parameters_by_level("low"))

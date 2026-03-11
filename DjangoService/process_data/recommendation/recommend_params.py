from __future__ import annotations

import json
from pathlib import Path

from .serialization import load_object


VALID_LEVELS = {"low", "medium", "high"}


def _load_artifacts():
    base = Path(__file__).resolve().parent
    model_path = base / "model.pkl"
    config_path = base / "level_config.json"
    if not model_path.exists() or not config_path.exists():
        raise FileNotFoundError("模型文件不存在，请先训练模型。")
    return load_object(model_path), json.loads(config_path.read_text(encoding="utf-8"))


def recommend_by_level(level: str, top_k: int = 5):
    level = str(level).lower().strip()
    if level not in VALID_LEVELS:
        raise ValueError("level 必须是 low / medium / high")

    model_bundle, cfg = _load_artifacts()
    model = model_bundle["model"]
    bounds = model_bundle["training_bounds"]
    ranges = cfg["level_ranges"]

    speed_min, speed_max = bounds["speed"]
    feed_min, feed_max = bounds["feed"]

    try:
        import numpy as np
        import pandas as pd
    except Exception as exc:
        raise RuntimeError("缺少 numpy/pandas 依赖，无法执行推荐") from exc

    speed_grid = np.linspace(speed_min, speed_max, 60)
    feed_grid = np.linspace(feed_min, feed_max, 60)
    mesh_speed, mesh_feed = np.meshgrid(speed_grid, feed_grid)

    samples = np.column_stack([mesh_speed.ravel(), mesh_feed.ravel()])
    preds = model.predict(samples)
    df = pd.DataFrame(samples, columns=["speed", "feed"])
    df["predicted_damage_A"] = preds

    low_max = ranges["low"][1]
    medium_max = ranges["medium"][1]

    if level == "low":
        filtered = df[df["predicted_damage_A"] <= low_max].copy()
        center_speed = (speed_min + speed_max) / 2
        center_feed = (feed_min + feed_max) / 2
        filtered["score"] = (
            filtered["predicted_damage_A"]
            + 0.1 * ((filtered["speed"] - center_speed) ** 2 / max((speed_max - speed_min) ** 2, 1e-9))
            + 0.1 * ((filtered["feed"] - center_feed) ** 2 / max((feed_max - feed_min) ** 2, 1e-9))
        )
        filtered = filtered.sort_values("score", ascending=True)
    elif level == "medium":
        lower = ranges["medium"][0]
        filtered = df[(df["predicted_damage_A"] > lower) & (df["predicted_damage_A"] <= medium_max)].copy()
        center = (lower + medium_max) / 2
        filtered["score"] = (filtered["predicted_damage_A"] - center).abs()
        filtered = filtered.sort_values("score", ascending=True)
    else:
        lower = ranges["high"][0]
        filtered = df[df["predicted_damage_A"] > lower].copy()
        filtered["score"] = -filtered["predicted_damage_A"]
        filtered = filtered.sort_values("score", ascending=True)

    if filtered.empty:
        return []

    filtered = filtered.head(top_k).copy()
    filtered["level"] = level
    return filtered[["speed", "feed", "predicted_damage_A", "level"]].round(6).to_dict(orient="records")

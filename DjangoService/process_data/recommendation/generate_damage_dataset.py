"""基于论文 9 个种子点生成 A_damage 扩增数据集。"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from statistics import mean
from typing import Dict, List, Tuple

from .seed_damage_points import get_seed_damage_points

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "generated_damage_dataset.csv"
LEVEL_CONFIG_PATH = BASE_DIR / "level_config.json"

SPEED_MIN, SPEED_MAX = 2500.0, 10000.0
FZ_MIN, FZ_MAX = 0.01, 0.10


def _build_seed_grid(seed_points: List[Dict[str, float]]) -> Tuple[List[float], List[float], List[List[float]]]:
    speeds = sorted({p["speed"] for p in seed_points})
    fzs = sorted({p["fz"] for p in seed_points})
    grid = [[0.0 for _ in fzs] for _ in speeds]
    for i, speed in enumerate(speeds):
        for j, fz in enumerate(fzs):
            val = next(p["A_damage"] for p in seed_points if p["speed"] == speed and p["fz"] == fz)
            grid[i][j] = val
    return speeds, fzs, grid


def _lin_interp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    if x1 == x0:
        return y0
    t = (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)


def _interp_on_axis(x: float, xs: List[float], ys: List[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return _lin_interp(x, xs[i], xs[i + 1], ys[i], ys[i + 1])
    return ys[-1]


def _interp2d_from_grid(speed: float, fz: float, speeds: List[float], fzs: List[float], grid: List[List[float]]) -> float:
    speed = max(SPEED_MIN, min(SPEED_MAX, float(speed)))
    fz = max(FZ_MIN, min(FZ_MAX, float(fz)))
    row_values = [_interp_on_axis(fz, fzs, grid[i]) for i in range(len(speeds))]
    return _interp_on_axis(speed, speeds, row_values)


def _assign_levels(values: List[float]) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    q1 = sorted_vals[int((n - 1) / 3)]
    q2 = sorted_vals[int((n - 1) * 2 / 3)]

    levels = []
    for v in values:
        if v <= q1:
            levels.append("low")
        elif v <= q2:
            levels.append("medium")
        else:
            levels.append("high")

    config = {
        "method": "quantile_3_bins",
        "thresholds": {"low_max": q1, "medium_max": q2},
        "ranges": {
            "low": {"min": min(values), "max": q1},
            "medium": {"min": q1, "max": q2},
            "high": {"min": q2, "max": max(values)},
        },
    }
    return levels, config


def generate_damage_dataset(num_samples: int = 2000, random_state: int = 42) -> Dict[str, object]:
    random.seed(random_state)
    seed_points = get_seed_damage_points()
    seed_speeds, seed_fzs, seed_grid = _build_seed_grid(seed_points)

    random_count = max(0, num_samples - len(seed_points))
    rows: List[Dict[str, object]] = []

    for p in seed_points:
        rows.append({"speed": p["speed"], "fz": p["fz"], "A_damage": p["A_damage"]})

    for _ in range(random_count):
        speed = random.uniform(SPEED_MIN, SPEED_MAX)
        fz = random.uniform(FZ_MIN, FZ_MAX)
        interp_pred = _interp2d_from_grid(speed, fz, seed_speeds, seed_fzs, seed_grid)

        noise_std = max(0.2, 0.03 * abs(interp_pred))
        a_damage = max(0.001, interp_pred + random.gauss(0, noise_std))
        rows.append({"speed": speed, "fz": fz, "A_damage": a_damage})

    a_vals = [float(r["A_damage"]) for r in rows]
    levels, config = _assign_levels(a_vals)
    for i, lv in enumerate(levels):
        rows[i]["damage_level"] = lv

    with DATASET_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["speed", "fz", "A_damage", "damage_level"])
        writer.writeheader()
        writer.writerows(rows)

    with LEVEL_CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    stats = {
        "speed": {"min": min(r["speed"] for r in rows), "max": max(r["speed"] for r in rows), "mean": mean(r["speed"] for r in rows)},
        "fz": {"min": min(r["fz"] for r in rows), "max": max(r["fz"] for r in rows), "mean": mean(r["fz"] for r in rows)},
        "A_damage": {"min": min(a_vals), "max": max(a_vals), "mean": mean(a_vals)},
    }

    seed_set = {(p["speed"], p["fz"], p["A_damage"]) for p in seed_points}
    row_set = {(float(r["speed"]), float(r["fz"]), float(r["A_damage"])) for r in rows}
    contains_original = seed_set.issubset(row_set)

    return {
        "total_samples": len(rows),
        "head_10": rows[:10],
        "stats": stats,
        "contains_original_9": contains_original,
        "dataset_path": str(DATASET_PATH),
        "level_config_path": str(LEVEL_CONFIG_PATH),
    }


def main():
    result = generate_damage_dataset()
    print(f"总样本数: {result['total_samples']}")
    print("前10行:")
    for row in result["head_10"]:
        print(row)
    print("统计信息:")
    print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
    print(f"包含原始9个样本: {result['contains_original_9']}")


if __name__ == "__main__":
    main()

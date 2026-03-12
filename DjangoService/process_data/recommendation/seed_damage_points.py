"""论文表2中的 9 组 CFRP 铣削 A_damage 种子数据。"""

from __future__ import annotations

from typing import List, Dict

SEED_DAMAGE_POINTS: List[Dict[str, float]] = [
    {"speed": 2500.0, "fz": 0.01, "A_damage": 3.5834},
    {"speed": 2500.0, "fz": 0.05, "A_damage": 65.7846},
    {"speed": 2500.0, "fz": 0.10, "A_damage": 115.64538},
    {"speed": 5000.0, "fz": 0.01, "A_damage": 3.36352},
    {"speed": 5000.0, "fz": 0.05, "A_damage": 59.79448},
    {"speed": 5000.0, "fz": 0.10, "A_damage": 101.71934},
    {"speed": 10000.0, "fz": 0.01, "A_damage": 2.8},
    {"speed": 10000.0, "fz": 0.05, "A_damage": 51.24078},
    {"speed": 10000.0, "fz": 0.10, "A_damage": 109.14466},
]


def get_seed_damage_points() -> List[Dict[str, float]]:
    """返回深拷贝友好的种子数据列表。"""
    return [dict(item) for item in SEED_DAMAGE_POINTS]

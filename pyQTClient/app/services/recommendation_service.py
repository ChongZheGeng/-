# coding:utf-8
"""本地参数推荐服务（演示版）。

说明：
- 主页面以“目标损伤等级”作为当前版本推荐核心输入。
- 材料/刀具/厚度等字段由 UI 收集后用于记录与后续扩展。
"""

from __future__ import annotations

import csv
import json
import pickle
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class RecommendationPaths:
    dataset: Path
    model: Path
    level_config: Path
    records: Path


class RecommendationService:
    """提供数据生成、训练、推荐、导出等本地能力。"""

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[3]
        recommendation_dir = repo_root / "DjangoService" / "process_data" / "recommendation"
        recommendation_dir.mkdir(parents=True, exist_ok=True)

        self.paths = RecommendationPaths(
            dataset=recommendation_dir / "generated_damage_dataset.csv",
            model=recommendation_dir / "recommendation_model.pkl",
            level_config=recommendation_dir / "level_config.json",
            records=recommendation_dir / "recommendation_records.jsonl",
        )

    def generate_dataset(self, num_samples: int = 2000, seed: int = 42, overwrite: bool = True) -> Dict[str, object]:
        if self.paths.dataset.exists() and not overwrite:
            return {
                "success": True,
                "skipped": True,
                "message": "已存在训练数据，未覆盖",
                "dataset_path": str(self.paths.dataset),
                "total_samples": self._count_dataset_rows(),
            }

        random.seed(seed)
        rows: List[Dict[str, object]] = []
        for _ in range(max(50, int(num_samples))):
            speed = random.uniform(2800, 9500)
            fz = random.uniform(0.015, 0.09)
            base_damage = 0.000035 * speed + 180 * fz + random.gauss(0, 0.09)
            if base_damage <= 0.42:
                level = "low"
            elif base_damage <= 0.62:
                level = "medium"
            else:
                level = "high"

            rows.append({
                "speed_n": round(speed, 2),
                "feed_fz": round(fz, 5),
                "A_damage": round(max(0.05, base_damage), 5),
                "damage_level": level,
            })

        with self.paths.dataset.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["speed_n", "feed_fz", "A_damage", "damage_level"])
            writer.writeheader()
            writer.writerows(rows)

        level_cfg = {
            "thresholds": {
                "low_max": 0.42,
                "medium_max": 0.62,
            },
            "ranges": {
                "low": "A_damage <= 0.42",
                "medium": "0.42 < A_damage <= 0.62",
                "high": "A_damage > 0.62",
            },
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.paths.level_config.write_text(json.dumps(level_cfg, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "success": True,
            "dataset_path": str(self.paths.dataset),
            "total_samples": len(rows),
            "seed": seed,
        }

    def train_model(self, model_type: str = "RandomForest", retrain: bool = True) -> Dict[str, object]:
        if self.paths.model.exists() and not retrain:
            payload = pickle.loads(self.paths.model.read_bytes())
            payload["success"] = True
            payload["skipped"] = True
            payload["message"] = "模型已存在，未重新训练"
            return payload

        rows = self._load_dataset()
        if not rows:
            return {"success": False, "error": "没有训练数据，请先生成模拟训练数据"}

        random.Random(123).shuffle(rows)
        split_idx = max(1, int(len(rows) * 0.8))
        train_rows = rows[:split_idx]
        test_rows = rows[split_idx:]

        centroids = self._calc_centroids(train_rows)
        acc = self._calc_accuracy(test_rows or train_rows, centroids)

        payload = {
            "trained": True,
            "model_type": model_type,
            "backend": "centroid-demo",
            "centroids": centroids,
            "train_samples": len(train_rows),
            "test_samples": len(test_rows),
            "accuracy": round(acc, 4),
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "model_path": str(self.paths.model),
        }
        with self.paths.model.open("wb") as f:
            pickle.dump(payload, f)

        return {"success": True, **payload}

    def get_status(self) -> Dict[str, object]:
        status = {
            "success": True,
            "has_dataset": self.paths.dataset.exists(),
            "dataset_path": str(self.paths.dataset),
            "has_model": self.paths.model.exists(),
            "model_path": str(self.paths.model),
            "last_trained_at": "-",
            "threshold_config": self._read_thresholds(),
        }
        if self.paths.model.exists():
            try:
                payload = pickle.loads(self.paths.model.read_bytes())
                status["last_trained_at"] = payload.get("trained_at", "-")
                status["model_type"] = payload.get("model_type", "-")
            except Exception:
                pass
        return status

    def recommend(self, form_data: Dict[str, object]) -> Dict[str, object]:
        target_level = str(form_data.get("target_damage_level", "medium")).lower()
        rows = self._load_dataset()
        mode = "模型推荐" if self.paths.model.exists() else "规则推荐"

        if not rows:
            rows = self._default_rows(target_level)
            mode = "规则推荐"

        filtered = [r for r in rows if r["damage_level"] == target_level] or rows
        filtered.sort(key=lambda x: x["A_damage"])

        quality_base = filtered[max(0, int(len(filtered) * 0.2) - 1)]
        balance_base = filtered[max(0, int(len(filtered) * 0.5) - 1)]
        efficiency_base = filtered[max(0, int(len(filtered) * 0.8) - 1)]

        plans = [
            self._build_plan("推荐方案 A（质量优先）", quality_base, score=93, comment="偏稳健，适合低损伤质量控制场景"),
            self._build_plan("推荐方案 B（效率优先）", efficiency_base, score=86, comment="偏高去除率，适合效率优先场景"),
            self._build_plan("推荐方案 C（综合平衡）", balance_base, score=89, comment="效率与损伤控制均衡，适合常规生产"),
        ]

        # future_features: 后续可将材料/刀具/厚度等字段加入模型特征
        return {
            "success": True,
            "mode": mode,
            "target_level": target_level,
            "form_data": form_data,
            "plans": plans,
            "samples": filtered[:120],
            "similar_samples": filtered[:8],
        }

    def save_record(self, recommendation_result: Dict[str, object]) -> Dict[str, object]:
        line = {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            **recommendation_result,
        }
        with self.paths.records.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return {"success": True, "record_path": str(self.paths.records)}

    def export_result(self, recommendation_result: Dict[str, object], file_type: str = "json") -> Dict[str, object]:
        export_dir = self.paths.dataset.parent / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_type = file_type.lower()
        if file_type == "csv":
            path = export_dir / f"recommendation_{ts}.csv"
            plans = recommendation_result.get("plans", [])
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["name", "speed_n", "feed_fz", "score", "estimated_damage_level", "description"])
                writer.writeheader()
                writer.writerows(plans)
        elif file_type == "txt":
            path = export_dir / f"recommendation_{ts}.txt"
            lines = ["加工参数智能推荐导出", f"模式: {recommendation_result.get('mode')}"]
            for p in recommendation_result.get("plans", []):
                lines.append(f"- {p['name']}: n={p['speed_n']} rpm, fz={p['feed_fz']} mm/z, 评分={p['score']}")
            path.write_text("\n".join(lines), encoding="utf-8")
        else:
            path = export_dir / f"recommendation_{ts}.json"
            path.write_text(json.dumps(recommendation_result, ensure_ascii=False, indent=2), encoding="utf-8")

        return {"success": True, "export_path": str(path)}

    def _build_plan(self, name: str, row: Dict[str, object], score: int, comment: str) -> Dict[str, object]:
        return {
            "name": name,
            "speed_n": round(float(row["speed_n"]), 1),
            "feed_fz": round(float(row["feed_fz"]), 5),
            "score": score,
            "estimated_damage_level": row["damage_level"],
            "description": comment,
        }

    def _calc_centroids(self, rows: List[Dict[str, object]]) -> Dict[str, Tuple[float, float]]:
        grouped: Dict[str, List[Tuple[float, float]]] = {"low": [], "medium": [], "high": []}
        for row in rows:
            grouped[row["damage_level"]].append((float(row["speed_n"]), float(row["feed_fz"])))

        centroids = {}
        for level, points in grouped.items():
            if not points:
                centroids[level] = (0.0, 0.0)
                continue
            centroids[level] = (
                sum(p[0] for p in points) / len(points),
                sum(p[1] for p in points) / len(points),
            )
        return centroids

    def _calc_accuracy(self, rows: List[Dict[str, object]], centroids: Dict[str, Tuple[float, float]]) -> float:
        if not rows:
            return 0.0
        ok = 0
        for row in rows:
            pred = self._predict_level(float(row["speed_n"]), float(row["feed_fz"]), centroids)
            ok += int(pred == row["damage_level"])
        return ok / len(rows)

    @staticmethod
    def _predict_level(speed_n: float, feed_fz: float, centroids: Dict[str, Tuple[float, float]]) -> str:
        best_level = "medium"
        best_dist = 10 ** 9
        for level, center in centroids.items():
            dist = (speed_n - center[0]) ** 2 + ((feed_fz - center[1]) * 5000) ** 2
            if dist < best_dist:
                best_level = level
                best_dist = dist
        return best_level

    def _load_dataset(self) -> List[Dict[str, object]]:
        if not self.paths.dataset.exists():
            return []

        rows = []
        with self.paths.dataset.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rows.append({
                        "speed_n": float(row.get("speed_n") or row.get("speed") or 0),
                        "feed_fz": float(row.get("feed_fz") or row.get("fz") or 0),
                        "A_damage": float(row.get("A_damage") or 0),
                        "damage_level": str(row.get("damage_level") or "medium").lower(),
                    })
                except Exception:
                    continue
        return rows

    def _count_dataset_rows(self) -> int:
        return len(self._load_dataset())

    def _read_thresholds(self) -> Dict[str, object]:
        if not self.paths.level_config.exists():
            return {"low": "-", "medium": "-", "high": "-"}
        try:
            data = json.loads(self.paths.level_config.read_text(encoding="utf-8"))
            return data.get("ranges", data)
        except Exception:
            return {"low": "-", "medium": "-", "high": "-"}

    @staticmethod
    def _default_rows(target_level: str) -> List[Dict[str, object]]:
        base = {
            "low": [(4200, 0.028, 0.31), (5000, 0.032, 0.38), (5600, 0.035, 0.41)],
            "medium": [(5400, 0.04, 0.49), (6200, 0.046, 0.55), (7000, 0.052, 0.61)],
            "high": [(7200, 0.058, 0.66), (8000, 0.065, 0.72), (8800, 0.074, 0.79)],
        }
        rows = []
        for level, pts in base.items():
            for p in pts:
                rows.append({"speed_n": p[0], "feed_fz": p[1], "A_damage": p[2], "damage_level": level})

        if target_level in base:
            rows.extend({"speed_n": s * 1.01, "feed_fz": f * 0.99, "A_damage": a * 1.01, "damage_level": target_level} for s, f, a in base[target_level])
        return rows


recommendation_service = RecommendationService()

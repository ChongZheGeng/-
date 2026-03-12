# coding:utf-8
import csv
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class RecommendationService:
    """参数推荐演示服务：提供本地数据生成、筛选推荐与导出能力。"""

    def __init__(self):
        self.dataset: List[Dict] = []
        self.model_status = "未训练"
        self.model_type = "rule"
        self.last_train_time = "--"
        self.train_summary = "--"
        self.last_generate_status = "未生成"
        self.last_data_path = "--"
        self.last_recommendation = []
        self._dataset_counter = 0
        self.generate_dataset(2000)

    @staticmethod
    def classify_damage(a_damage: float) -> str:
        if a_damage < 1.0:
            return "low"
        if a_damage < 1.8:
            return "medium"
        return "high"

    @staticmethod
    def _predict_damage(n: float, fz: float) -> Dict:
        a_damage = max(0.05, 1.25e-4 * float(n) + 8.5 * float(fz))
        f_damage = max(0.05, 8.5e-5 * float(n) + 11.0 * float(fz))
        return {
            "A_damage": round(a_damage, 4),
            "F_damage": round(f_damage, 4),
            "damage_level": RecommendationService.classify_damage(a_damage),
        }

    def generate_dataset(self, sample_count: int = 2000) -> List[Dict]:
        sample_count = max(200, int(sample_count or 2000))
        random.seed(42 + self._dataset_counter)
        self._dataset_counter += 1

        dataset = []
        for i in range(sample_count):
            n = random.uniform(3500, 18000)
            fz = random.uniform(0.015, 0.15)
            damages = self._predict_damage(n, fz)
            a_damage = damages["A_damage"] + random.uniform(-0.08, 0.08)
            a_damage = round(max(0.05, a_damage), 4)
            level = self.classify_damage(a_damage)
            dataset.append({
                "sample_id": f"S{i + 1:04d}",
                "n": round(n, 2),
                "fz": round(fz, 4),
                "A_damage": a_damage,
                "damage_level": level,
                "tool_type": random.choice(["立铣刀", "麻花钻", "PCD刀具", "硬质合金刀具"]),
                "material": random.choice(["CFRP", "GFRP", "复合材料示例A", "复合材料示例B"]),
            })

        self.dataset = dataset
        self.last_generate_status = f"生成成功，共 {len(dataset)} 条样本"
        return dataset

    def recommend(self, payload: Dict, backend_result: Dict = None) -> Dict:
        if not self.dataset:
            self.generate_dataset(2000)

        target_level = payload.get("damage_target", "medium")
        objective = payload.get("machining_goal", "综合最优")
        input_n = payload.get("n")
        input_fz = payload.get("fz")

        level_samples = [d for d in self.dataset if d["damage_level"] == target_level] or self.dataset

        conservative = sorted(level_samples, key=lambda x: (x["A_damage"], x["fz"]))[0]
        aggressive = sorted(level_samples, key=lambda x: (x["n"] * x["fz"], -x["A_damage"]), reverse=True)[0]
        balanced = sorted(level_samples, key=lambda x: abs(x["A_damage"] - 1.2))[0]

        candidates = [
            ("方案 A：低损伤优先", conservative, "rule", "偏保守，优先压低估计损伤"),
            ("方案 B：效率优先", aggressive, "rule", "偏激进，优先提高加工效率"),
            ("方案 C：综合平衡", balanced, "rule", "兼顾损伤和效率，适合演示默认策略"),
        ]

        if backend_result and backend_result.get("success"):
            best = backend_result.get("best") or {}
            pred = backend_result.get("prediction") or {}
            backend_card = {
                "title": "方案 C：综合平衡",
                "n": round(float(best.get("n", balanced["n"])), 2),
                "fz": round(float(best.get("fz", balanced["fz"])), 4),
                "damage_target": target_level,
                "estimated_damage": round(float(pred.get("A_damage", balanced["A_damage"])), 4),
                "mode": backend_result.get("mode", "prediction"),
                "confidence": "后端接口返回成功，可信度中高",
                "reason": "该方案由后端预测接口提供，并用于替换综合平衡结果",
            }
        else:
            backend_card = None

        cards = []
        for title, sample, mode, reason in candidates:
            cards.append({
                "title": title,
                "n": sample["n"],
                "fz": sample["fz"],
                "damage_target": target_level,
                "estimated_damage": sample["A_damage"],
                "mode": mode,
                "confidence": "基于历史样本规则筛选，可信度中等",
                "reason": reason,
            })

        if backend_card:
            cards[2] = backend_card

        if objective == "低损伤":
            cards = [cards[0], cards[2], cards[1]]
        elif objective == "高效率":
            cards = [cards[1], cards[2], cards[0]]

        prediction = None
        if input_n is not None and input_fz is not None:
            prediction = self._predict_damage(float(input_n), float(input_fz))

        top_samples = self.find_similar_samples(input_n, input_fz, target_level, top_n=5)

        self.last_recommendation = cards
        return {
            "cards": cards,
            "current_prediction": prediction,
            "samples": top_samples,
            "mode": "prediction" if backend_card else "fallback",
        }

    def find_similar_samples(self, n, fz, target_level: str, top_n: int = 5) -> List[Dict]:
        samples = [d for d in self.dataset if d["damage_level"] == target_level] or self.dataset
        n = float(n) if n is not None else 10000.0
        fz = float(fz) if fz is not None else 0.06

        enriched = []
        for row in samples:
            distance = math.sqrt(((row["n"] - n) / 15000) ** 2 + ((row["fz"] - fz) / 0.2) ** 2)
            sim = max(0.0, 1.0 - distance)
            enriched.append({**row, "similarity": round(sim, 4)})

        enriched.sort(key=lambda x: x["similarity"], reverse=True)
        top_samples = enriched[: max(5, top_n)]
        for s in top_samples:
            s["reference"] = "同等级样本"
        return top_samples

    def train_model(self, model_type: str = "rule") -> Dict:
        self.model_type = model_type
        self.model_status = "已训练"
        self.last_train_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sample_count = len(self.dataset)
        pseudo_score = 0.78 if model_type == "rule" else (0.84 if model_type == "poly" else 0.89)
        self.train_summary = f"样本数={sample_count}, 评分={pseudo_score:.2f}, MAE={1 - pseudo_score:.2f}"
        return {
            "status": self.model_status,
            "model_type": self.model_type,
            "last_train_time": self.last_train_time,
            "summary": self.train_summary,
        }

    def reload_model(self):
        if self.model_status == "未训练":
            return "当前无已训练模型可加载"
        return f"已重新加载模型：{self.model_type}"

    def export_training_data(self) -> str:
        return self._export_rows(self.dataset, "recommendation_training_data")

    def export_recommendation(self) -> str:
        rows = self.last_recommendation or []
        return self._export_rows(rows, "recommendation_result")

    def persist_dataset(self) -> str:
        path = self._export_rows(self.dataset, "recommendation_dataset")
        self.last_data_path = path
        return path

    def _export_rows(self, rows: List[Dict], name_prefix: str) -> str:
        export_dir = Path("pyQTClient/exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = export_dir / f"{name_prefix}_{stamp}.csv"

        if not rows:
            file_path.write_text("", encoding="utf-8")
            return str(file_path)

        keys = list(rows[0].keys())
        with file_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        return str(file_path)

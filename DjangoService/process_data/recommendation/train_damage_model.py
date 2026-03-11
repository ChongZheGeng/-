"""训练 A_damage 回归模型并输出评估与报告。"""

from __future__ import annotations

import csv
import json
import math
import pickle
from pathlib import Path
from random import Random
from typing import Dict, List, Tuple

from .generate_damage_dataset import DATASET_PATH, LEVEL_CONFIG_PATH
from .seed_damage_points import SEED_DAMAGE_POINTS

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"
REPORT_PATH = BASE_DIR / "training_report.md"

try:
    from sklearn.ensemble import RandomForestRegressor  # type: ignore
    from sklearn.linear_model import LinearRegression  # type: ignore
    from sklearn.pipeline import Pipeline  # type: ignore
    from sklearn.preprocessing import PolynomialFeatures  # type: ignore
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


def _read_dataset() -> List[Tuple[float, float, float]]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"数据集不存在，请先生成: {DATASET_PATH}")
    rows = []
    with DATASET_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((float(r["speed"]), float(r["fz"]), float(r["A_damage"])))
    return rows


def _train_test_split(rows: List[Tuple[float, float, float]], test_ratio: float = 0.2, random_state: int = 42):
    rng = Random(random_state)
    shuffled = rows[:]
    rng.shuffle(shuffled)
    cut = int(len(shuffled) * (1 - test_ratio))
    return shuffled[:cut], shuffled[cut:]


def _features_linear(speed: float, fz: float) -> List[float]:
    return [1.0, speed, fz]


def _features_poly2(speed: float, fz: float) -> List[float]:
    return [1.0, speed, fz, speed * speed, speed * fz, fz * fz]


def _solve_linear_system(a: List[List[float]], b: List[float]) -> List[float]:
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_val = aug[col][col] or 1e-12
        for j in range(col, n + 1):
            aug[col][j] /= pivot_val
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            for j in range(col, n + 1):
                aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def _fit_custom_regression(data: List[Tuple[float, float, float]], feature_fn):
    x = [feature_fn(s, f) for s, f, _ in data]
    y = [v for _, _, v in data]
    dim = len(x[0])
    xtx = [[0.0] * dim for _ in range(dim)]
    xty = [0.0] * dim
    for row, target in zip(x, y):
        for i in range(dim):
            xty[i] += row[i] * target
            for j in range(dim):
                xtx[i][j] += row[i] * row[j]
    coef = _solve_linear_system(xtx, xty)
    return coef


def _predict_custom(coef: List[float], features: List[float]) -> float:
    return sum(c * f for c, f in zip(coef, features))


def _metrics(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    n = max(1, len(y_true))
    mae = sum(abs(a - b) for a, b in zip(y_true, y_pred)) / n
    mse = sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / n
    rmse = math.sqrt(mse)
    mean_y = sum(y_true) / n
    ss_tot = sum((a - mean_y) ** 2 for a in y_true) or 1e-12
    ss_res = sum((a - b) ** 2 for a, b in zip(y_true, y_pred))
    r2 = 1 - ss_res / ss_tot
    return {"R2": r2, "MAE": mae, "RMSE": rmse}


def _train_with_sklearn(train_rows, test_rows):
    x_train = [[s, f] for s, f, _ in train_rows]
    y_train = [v for _, _, v in train_rows]
    x_test = [[s, f] for s, f, _ in test_rows]
    y_test = [v for _, _, v in test_rows]

    models = {
        "LinearRegression": LinearRegression(),
        "Polynomial(2)+LinearRegression": Pipeline([
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("lr", LinearRegression()),
        ]),
        "RandomForestRegressor": RandomForestRegressor(n_estimators=300, random_state=42, min_samples_leaf=2),
    }

    results, best_name, best_model, best_r2 = {}, None, None, -1e9
    for name, model in models.items():
        model.fit(x_train, y_train)
        pred = [max(0.001, float(v)) for v in model.predict(x_test)]
        m = _metrics(y_test, pred)
        results[name] = m
        if m["R2"] > best_r2:
            best_r2, best_name, best_model = m["R2"], name, model

    payload = {"backend": "sklearn", "model_name": best_name, "model": best_model}
    return payload, results, best_name


def _train_without_sklearn(train_rows, test_rows):
    coef_linear = _fit_custom_regression(train_rows, _features_linear)
    coef_poly = _fit_custom_regression(train_rows, _features_poly2)

    y_test = [v for _, _, v in test_rows]
    pred_linear = [max(0.001, _predict_custom(coef_linear, _features_linear(s, f))) for s, f, _ in test_rows]
    pred_poly = [max(0.001, _predict_custom(coef_poly, _features_poly2(s, f))) for s, f, _ in test_rows]

    results = {
        "LinearRegression": _metrics(y_test, pred_linear),
        "Polynomial(2)+LinearRegression": _metrics(y_test, pred_poly),
        "RandomForestRegressor": {"R2": -1.0, "MAE": -1.0, "RMSE": -1.0},
    }

    best_name = "Polynomial(2)+LinearRegression" if results["Polynomial(2)+LinearRegression"]["R2"] >= results["LinearRegression"]["R2"] else "LinearRegression"
    payload = {
        "backend": "custom",
        "model_name": best_name,
        "coef_linear": coef_linear,
        "coef_poly2": coef_poly,
    }
    return payload, results, best_name


def train_damage_model(random_state: int = 42) -> Dict[str, object]:
    rows = _read_dataset()
    train_rows, test_rows = _train_test_split(rows, random_state=random_state)

    if SKLEARN_AVAILABLE:
        model_payload, results, best_name = _train_with_sklearn(train_rows, test_rows)
    else:
        model_payload, results, best_name = _train_without_sklearn(train_rows, test_rows)

    with MODEL_PATH.open("wb") as f:
        pickle.dump(model_payload, f)

    level_config = json.loads(LEVEL_CONFIG_PATH.read_text(encoding="utf-8")) if LEVEL_CONFIG_PATH.exists() else {}
    _write_training_report(results, best_name, level_config)

    return {"best_model": best_name, "metrics": results, "model_path": str(MODEL_PATH), "report_path": str(REPORT_PATH)}


def _write_training_report(metrics: Dict[str, Dict[str, float]], best_model: str, level_config: Dict[str, object]) -> None:
    seed_lines = "\n".join([f"- speed={p['speed']}, fz={p['fz']}, A_damage={p['A_damage']}" for p in SEED_DAMAGE_POINTS])
    metric_table_header = "| 模型 | R² | MAE | RMSE |\n|---|---:|---:|---:|"
    metric_rows = "\n".join([f"| {name} | {m['R2']:.4f} | {m['MAE']:.4f} | {m['RMSE']:.4f} |" for name, m in metrics.items()])
    level_ranges = level_config.get("ranges", {})

    notes = "- 环境缺少 scikit-learn 时，RandomForest 指标将显示为占位值。" if not SKLEARN_AVAILABLE else ""

    content = f"""# A_damage 模型训练报告

## 原始9组数据（论文表2）
{seed_lines}

## 扩增方法
- 以 9 个种子点构成 speed-fz 规则网格并进行二维插值。
- 在插值曲面上添加小幅高斯噪声（约 3%），并裁剪到正值。
- 生成 2000 条样本（保留原始 9 条）。

## 模型对比
{metric_table_header}
{metric_rows}

## 最终模型
- **{best_model}**

## 损伤等级区间（按三分位）
- low: {level_ranges.get('low', {})}
- medium: {level_ranges.get('medium', {})}
- high: {level_ranges.get('high', {})}

{notes}
"""
    REPORT_PATH.write_text(content, encoding="utf-8")


def main():
    print(json.dumps(train_damage_model(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np
import pandas as pd

from .serialization import dump_object, load_object
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures

matplotlib.use("Agg")
import matplotlib.pyplot as plt


FEATURE_ALIASES = {
    "speed": ["speed", "spindle_speed", "转速"],
    "feed": ["feed", "fz", "进给量"],
    "damage_A": ["damage_A", "A_damage", "A损伤"],
}


@dataclass
class TrainingResult:
    recognized_columns: Dict[str, str]
    row_count: int
    missing_values: Dict[str, int]
    best_model: str
    best_metrics: Dict[str, float]
    model_comparison: List[Dict[str, float]]
    level_ranges: Dict[str, List[float]]
    output_dir: str


def find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "DjangoService").exists() and (parent / "pyQTClient").exists():
            return parent
    return Path.cwd()


def resolve_training_excel_path(filename: str = "A.xlsx") -> Path:
    project_root = find_project_root()
    candidates = [
        project_root / filename,
        Path.cwd() / filename,
        Path(__file__).resolve().parents[3] / filename,
    ]
    tried = []
    for path in candidates:
        resolved = path.resolve()
        tried.append(str(resolved))
        if resolved.exists() and resolved.is_file():
            return resolved
    tried_text = "\n".join(f"- {p}" for p in tried)
    raise FileNotFoundError(
        f"未找到训练数据文件 {filename}。尝试路径:\n{tried_text}\n"
        "请把 A.xlsx 放在项目根目录。"
    )


def _normalize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    mapping = {}
    lower_map = {c.lower(): c for c in df.columns}
    for standard, aliases in FEATURE_ALIASES.items():
        found = None
        for alias in aliases:
            exact = alias if alias in df.columns else None
            insensitive = lower_map.get(alias.lower())
            found = exact or insensitive
            if found:
                break
        if not found:
            raise ValueError(f"缺少字段 {standard}，可兼容字段: {aliases}。实际字段: {list(df.columns)}")
        mapping[standard] = found
    cleaned = df[[mapping["speed"], mapping["feed"], mapping["damage_A"]]].copy()
    cleaned.columns = ["speed", "feed", "damage_A"]
    return cleaned, mapping


def _build_models(random_state: int = 42):
    models = {
        "linear_regression": LinearRegression(),
        "poly2_regression": Pipeline([
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("linear", LinearRegression()),
        ]),
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            random_state=random_state,
            min_samples_leaf=2,
        ),
    }

    try:
        from xgboost import XGBRegressor

        models["xgboost"] = XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=random_state,
            objective="reg:squarederror",
        )
    except Exception:
        pass

    try:
        from lightgbm import LGBMRegressor

        models["lightgbm"] = LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=-1,
            random_state=random_state,
        )
    except Exception:
        pass

    return models


def _calc_level_ranges(damage_series: pd.Series) -> Dict[str, List[float]]:
    q33, q66 = damage_series.quantile([0.33, 0.66]).tolist()
    dmin = float(damage_series.min())
    dmax = float(damage_series.max())
    return {
        "low": [dmin, float(q33)],
        "medium": [float(q33), float(q66)],
        "high": [float(q66), dmax],
    }


def _render_plots(df: pd.DataFrame, y_test: np.ndarray, y_pred: np.ndarray, level_ranges: Dict[str, List[float]], out_dir: Path):
    plt.figure(figsize=(7, 5))
    df["damage_A"].hist(bins=20)
    plt.title("damage_A Distribution")
    plt.xlabel("damage_A")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_dir / "damage_distribution.png", dpi=180)
    plt.close()

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(df["speed"], df["feed"], df["damage_A"], c=df["damage_A"], cmap="viridis", s=25)
    ax.set_xlabel("speed")
    ax.set_ylabel("feed")
    ax.set_zlabel("damage_A")
    ax.set_title("Speed-Feed-Damage Relationship")
    plt.tight_layout()
    plt.savefig(out_dir / "speed_feed_damage_3d.png", dpi=180)
    plt.close()

    plt.figure(figsize=(6, 6))
    plt.scatter(y_test, y_pred, alpha=0.75)
    low = min(y_test.min(), y_pred.min())
    high = max(y_test.max(), y_pred.max())
    plt.plot([low, high], [low, high], "r--")
    plt.xlabel("True damage_A")
    plt.ylabel("Predicted damage_A")
    plt.title("True vs Predicted")
    plt.tight_layout()
    plt.savefig(out_dir / "true_vs_pred.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 2.8))
    xmin, low_max = level_ranges["low"]
    _, med_max = level_ranges["medium"]
    _, xmax = level_ranges["high"]
    plt.axvspan(xmin, low_max, alpha=0.3, label="low")
    plt.axvspan(low_max, med_max, alpha=0.3, label="medium")
    plt.axvspan(med_max, xmax, alpha=0.3, label="high")
    plt.yticks([])
    plt.xlabel("damage_A")
    plt.title("Damage Level Ranges")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "level_ranges.png", dpi=180)
    plt.close()


def train_and_save(excel_name: str = "A.xlsx") -> TrainingResult:
    module_dir = Path(__file__).resolve().parent
    excel_path = resolve_training_excel_path(excel_name)

    raw_df = pd.read_excel(excel_path)
    normalized_df, mapping = _normalize_columns(raw_df)

    normalized_df = normalized_df.replace([np.inf, -np.inf], np.nan)
    missing = normalized_df.isna().sum().to_dict()
    normalized_df = normalized_df.dropna().copy()

    for col in ["speed", "feed", "damage_A"]:
        q1 = normalized_df[col].quantile(0.25)
        q3 = normalized_df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            lower = q1 - 3 * iqr
            upper = q3 + 3 * iqr
            normalized_df = normalized_df[(normalized_df[col] >= lower) & (normalized_df[col] <= upper)]

    X = normalized_df[["speed", "feed"]].values
    y = normalized_df["damage_A"].values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    comparison = []
    fitted = {}
    for name, model in _build_models().items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        metrics = {
            "model": name,
            "r2": float(r2_score(y_test, pred)),
            "mae": float(mean_absolute_error(y_test, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, pred))),
        }
        comparison.append(metrics)
        fitted[name] = model

    best = sorted(comparison, key=lambda x: (-x["r2"], x["rmse"], x["mae"]))[0]
    best_model_name = best["model"]
    best_model = fitted[best_model_name]

    level_ranges = _calc_level_ranges(normalized_df["damage_A"])

    model_bundle = {
        "model_name": best_model_name,
        "model": best_model,
        "feature_names": ["speed", "feed"],
        "training_bounds": {
            "speed": [float(normalized_df["speed"].min()), float(normalized_df["speed"].max())],
            "feed": [float(normalized_df["feed"].min()), float(normalized_df["feed"].max())],
        },
    }
    dump_object(model_bundle, module_dir / "model.pkl")
    dump_object(None, module_dir / "scaler.pkl")

    level_payload = {
        "level_ranges": level_ranges,
        "label_map": {"low": "低损伤", "medium": "中损伤", "high": "高损伤"},
    }
    (module_dir / "level_config.json").write_text(json.dumps(level_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    y_pred_best = best_model.predict(X_test)
    _render_plots(normalized_df, y_test, y_pred_best, level_ranges, module_dir)

    corr = normalized_df[["speed", "feed", "damage_A"]].corr().to_markdown()
    desc = normalized_df.describe().to_markdown()
    comp_df = pd.DataFrame(comparison).sort_values(by=["r2", "rmse"], ascending=[False, True])

    report = f"""# damage_A 训练报告

## 数据信息
- Excel 路径: `{excel_path}`
- 原始字段: {list(raw_df.columns)}
- 识别映射: {mapping}
- 清洗后样本数: {len(normalized_df)}
- 缺失值统计: {missing}

## 描述统计
{desc}

## 相关性分析
{corr}

## 模型对比
{comp_df.to_markdown(index=False)}

## 最终模型
- 选择模型: **{best_model_name}**
- R2: {best['r2']:.4f}
- MAE: {best['mae']:.4f}
- RMSE: {best['rmse']:.4f}
- 选择理由: 在测试集上综合指标最佳，同时使用 joblib 部署简单。

## 三级损伤区间（按分位数）
- low: [{level_ranges['low'][0]:.6f}, {level_ranges['low'][1]:.6f}]
- medium: ({level_ranges['medium'][0]:.6f}, {level_ranges['medium'][1]:.6f}]
- high: ({level_ranges['high'][0]:.6f}, {level_ranges['high'][1]:.6f}]

## 推荐逻辑
1. 在训练范围内生成 speed-feed 网格。
2. 用最终模型预测每个组合的 damage_A。
3. 按目标等级区间筛选可行组合。
4. 按等级策略排序后返回 Top-N。
"""
    (module_dir / "training_report.md").write_text(report, encoding="utf-8")

    return TrainingResult(
        recognized_columns=mapping,
        row_count=int(len(normalized_df)),
        missing_values={k: int(v) for k, v in missing.items()},
        best_model=best_model_name,
        best_metrics={k: float(v) for k, v in best.items() if k != "model"},
        model_comparison=comparison,
        level_ranges=level_ranges,
        output_dir=str(module_dir),
    )


if __name__ == "__main__":
    result = train_and_save("A.xlsx")
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

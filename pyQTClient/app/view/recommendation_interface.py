# coding:utf-8
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QSpinBox, QDoubleSpinBox
from qfluentwidgets import (
    SubtitleLabel,
    StrongBodyLabel,
    BodyLabel,
    ComboBox,
    PrimaryPushButton,
    CardWidget,
    InfoBar,
)

from .nav_interface import NavInterface
from ..api.api_client import api_client
from ..api.async_api import AsyncApiHelper

logger = logging.getLogger(__name__)


@dataclass
class ParsedResult:
    kind: str
    status_text: str
    message: str = ""
    input_n: Optional[float] = None
    input_fz: Optional[float] = None
    recommended_n: Optional[float] = None
    recommended_fz: Optional[float] = None
    objective: str = ""
    objective_value: Optional[Any] = None
    predicted_values: Dict[str, Any] = field(default_factory=dict)
    raw_success: Optional[bool] = None
    raw_message: str = ""
    recognized_fields: List[str] = field(default_factory=list)
    details: str = ""


def _pick_number(source: Dict[str, Any], key: str) -> Optional[float]:
    value = source.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_recommendation_response(data: Optional[Dict[str, Any]], payload: Dict[str, Any]) -> ParsedResult:
    if not data:
        return ParsedResult(
            kind="empty",
            status_text="未返回有效结果",
            message="接口未返回数据",
            input_n=payload.get("n"),
            input_fz=payload.get("fz"),
            objective=payload.get("objective", ""),
        )

    recognized_fields = [
        key
        for key in (
            "recommended_n", "recommended_fz", "best_point", "optimum", "recommended_params",
            "predicted_value", "predicted_A_damage", "predicted_F_damage", "objective_value", "result",
            "best", "prediction", "uncertainty", "n", "fz", "A_damage", "F_damage",
            "success", "message", "detail", "error",
        )
        if key in data
    ]

    raw_success = data.get("success") if isinstance(data.get("success"), bool) else None
    raw_message = str(data.get("message", ""))
    detail_text = str(data.get("detail") or data.get("error") or "")

    if raw_success is False:
        return ParsedResult(
            kind="error",
            status_text="请求失败",
            message=raw_message or "接口返回失败",
            details=detail_text,
            input_n=payload.get("n"),
            input_fz=payload.get("fz"),
            objective=payload.get("objective", ""),
            raw_success=raw_success,
            raw_message=raw_message,
            recognized_fields=recognized_fields,
        )

    recommended_n = _pick_number(data, "recommended_n")
    recommended_fz = _pick_number(data, "recommended_fz")
    if recommended_n is None:
        recommended_n = _pick_number(data, "n")
    if recommended_fz is None:
        recommended_fz = _pick_number(data, "fz")

    for nested_key in ("best_point", "optimum", "recommended_params"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            recommended_n = recommended_n if recommended_n is not None else _pick_number(nested, "n")
            recommended_fz = recommended_fz if recommended_fz is not None else _pick_number(nested, "fz")

    prediction_obj = data.get("prediction")
    if isinstance(prediction_obj, dict):
        for key in ("A_damage", "F_damage", "predicted_value", "objective_value"):
            if key in prediction_obj:
                predicted_key = f"predicted_{key}" if key in ("A_damage", "F_damage") else key
                data.setdefault(predicted_key, prediction_obj.get(key))

    best_obj = data.get("best")
    if isinstance(best_obj, dict):
        if recommended_n is None:
            recommended_n = _pick_number(best_obj, "n")
        if recommended_fz is None:
            recommended_fz = _pick_number(best_obj, "fz")

    predicted_values = {}
    for key in ("predicted_value", "predicted_A_damage", "predicted_F_damage", "objective_value", "result"):
        if key in data:
            predicted_values[key] = data.get(key)

    objective = str(data.get("objective") or payload.get("objective") or "")
    objective_value = data.get("objective_value")
    if objective_value is None and objective == "A_damage":
        objective_value = data.get("predicted_A_damage")
    if objective_value is None and objective == "F_damage":
        objective_value = data.get("predicted_F_damage")
    if objective_value is None:
        objective_value = data.get("predicted_value")

    if recommended_n is not None or recommended_fz is not None:
        return ParsedResult(
            kind="recommendation",
            status_text="推荐完成",
            message=raw_message or "已返回推荐参数",
            input_n=payload.get("n"),
            input_fz=payload.get("fz"),
            recommended_n=recommended_n,
            recommended_fz=recommended_fz,
            objective=objective,
            objective_value=objective_value,
            predicted_values=predicted_values,
            raw_success=raw_success,
            raw_message=raw_message,
            recognized_fields=recognized_fields,
        )

    if predicted_values:
        return ParsedResult(
            kind="prediction",
            status_text="预测完成",
            message="当前接口返回的是预测结果，未返回新的推荐参数",
            input_n=payload.get("n"),
            input_fz=payload.get("fz"),
            objective=objective,
            objective_value=objective_value,
            predicted_values=predicted_values,
            raw_success=raw_success,
            raw_message=raw_message,
            recognized_fields=recognized_fields,
        )

    return ParsedResult(
        kind="empty",
        status_text="未返回有效结果",
        message=raw_message or "接口未返回可识别的推荐/预测字段",
        input_n=payload.get("n"),
        input_fz=payload.get("fz"),
        objective=objective,
        raw_success=raw_success,
        raw_message=raw_message,
        recognized_fields=recognized_fields,
        details=detail_text,
    )


class RecommendationInterface(NavInterface):
    """参数推荐主页面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("RecommendationInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("参数推荐"))

        self.request_status_card = CardWidget(self)
        request_status_layout = QVBoxLayout(self.request_status_card)
        request_status_layout.setContentsMargins(20, 16, 20, 16)
        request_status_layout.setSpacing(8)
        request_status_layout.addWidget(StrongBodyLabel("请求状态"))
        self.status_label = BodyLabel("未开始")
        self.status_detail_label = BodyLabel("等待发起请求")
        self.status_detail_label.setWordWrap(True)
        request_status_layout.addWidget(self.status_label)
        request_status_layout.addWidget(self.status_detail_label)

        form_card = CardWidget(self)
        form_layout = QGridLayout(form_card)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(12)

        self.n_spin = QSpinBox(self)
        self.n_spin.setRange(1000, 50000)
        self.n_spin.setSingleStep(100)
        self.n_spin.setValue(10000)

        self.fz_spin = QDoubleSpinBox(self)
        self.fz_spin.setRange(0.001, 1.0)
        self.fz_spin.setSingleStep(0.001)
        self.fz_spin.setDecimals(4)
        self.fz_spin.setValue(0.05)

        self.objective_combo = ComboBox(self)
        self.objective_combo.addItems(["A_damage", "F_damage"])

        self.model_type_combo = ComboBox(self)
        self.model_type_combo.addItems(["quad", "gp"])

        form_layout.addWidget(StrongBodyLabel("转速 n"), 0, 0)
        form_layout.addWidget(self.n_spin, 0, 1)
        form_layout.addWidget(StrongBodyLabel("每齿进给 fz"), 0, 2)
        form_layout.addWidget(self.fz_spin, 0, 3)

        form_layout.addWidget(StrongBodyLabel("优化目标"), 1, 0)
        form_layout.addWidget(self.objective_combo, 1, 1)
        form_layout.addWidget(StrongBodyLabel("模型类型"), 1, 2)
        form_layout.addWidget(self.model_type_combo, 1, 3)

        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        self.recommend_button = PrimaryPushButton("获取推荐")
        self.recommend_button.clicked.connect(self.fetch_recommendation)
        action_layout.addWidget(self.recommend_button)

        result_card = CardWidget(self)
        result_layout = QGridLayout(result_card)
        result_layout.setContentsMargins(20, 16, 20, 16)
        result_layout.setHorizontalSpacing(16)
        result_layout.setVerticalSpacing(12)

        self.param_result_label = BodyLabel("参数结果将在此显示")
        self.param_result_label.setWordWrap(True)
        self.objective_result_label = BodyLabel("目标结果将在此显示")
        self.objective_result_label.setWordWrap(True)
        self.response_summary_label = BodyLabel("原始响应摘要将在此显示")
        self.response_summary_label.setWordWrap(True)

        result_layout.addWidget(StrongBodyLabel("参数结果卡片"), 0, 0)
        result_layout.addWidget(self.param_result_label, 1, 0)
        result_layout.addWidget(StrongBodyLabel("目标结果卡片"), 0, 1)
        result_layout.addWidget(self.objective_result_label, 1, 1)
        result_layout.addWidget(StrongBodyLabel("原始响应摘要卡片"), 2, 0, 1, 2)
        result_layout.addWidget(self.response_summary_label, 3, 0, 1, 2)

        self.main_layout.addWidget(form_card)
        self.main_layout.addLayout(action_layout)
        self.main_layout.addWidget(self.request_status_card)
        self.main_layout.addWidget(result_card)
        self.main_layout.addStretch(1)

    def on_activated(self):
        pass

    def on_deactivated(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker = None

    def _set_loading(self, loading, text=""):
        self.recommend_button.setEnabled(not loading)
        self.status_label.setText(text or ("请求中" if loading else "未开始"))

    def fetch_recommendation(self):
        n = self.n_spin.value()
        fz = self.fz_spin.value()
        if n <= 0:
            InfoBar.warning("输入错误", "转速 n 必须为正整数", parent=self)
            return
        if not (0.001 <= fz <= 1.0):
            InfoBar.warning("输入错误", "每齿进给 fz 必须在 0.001 ~ 1.0 范围内", parent=self)
            return
        if not (3000 <= n <= 30000):
            InfoBar.warning("参数提示", "当前 n 超出常见训练域（3000 ~ 30000），结果仅供参考", parent=self)
        if not (0.005 <= fz <= 0.2):
            InfoBar.warning("参数提示", "当前 fz 超出常见训练域（0.005 ~ 0.2），结果仅供参考", parent=self)

        payload = {
            "n": n,
            "fz": fz,
            "objective": self.objective_combo.currentText(),
            "model_type": self.model_type_combo.currentText(),
        }

        logger.info("[recommend] request_start url=http://127.0.0.1:8000/api/recommend/ payload=%s", payload)
        self._set_loading(True, "请求中")
        self.status_detail_label.setText("正在检查服务状态...")

        def call_recommend():
            self._set_loading(True, "请求中")
            self.status_detail_label.setText("正在请求参数推荐...")
            self.worker = AsyncApiHelper.call_async(
                api_client.recommend_parameters,
                self.on_recommend_success,
                self.on_recommend_error,
                payload,
                timeout=10,
            )

        def on_health(_):
            call_recommend()

        def on_health_error(_):
            # health接口不可用不阻断推荐，直接尝试推荐
            call_recommend()

        self.worker = AsyncApiHelper.call_async(
            api_client.health_check,
            on_health,
            on_health_error,
            timeout=3,
        )

    def on_recommend_success(self, response):
        logger.info("[recommend] response_status=success")
        logger.info("[recommend] response_body=%s", response)
        payload = {
            "n": self.n_spin.value(),
            "fz": self.fz_spin.value(),
            "objective": self.objective_combo.currentText(),
            "model_type": self.model_type_combo.currentText(),
        }
        parsed = parse_recommendation_response(response, payload)
        logger.info("[recommend] parsed_result kind=%s", parsed.kind)
        logger.info("[recommend] parsed_fields=%s", parsed.recognized_fields)
        self.render_parsed_result(parsed)

    def on_recommend_error(self, error):
        logger.error("[recommend] request_error=%s", error)
        self._set_loading(False, "请求失败")
        InfoBar.error("请求失败", "无法连接后端推荐服务，请检查后端是否启动", parent=self)
        self.status_detail_label.setText(f"请求失败: {error}")
        self.param_result_label.setText("参数结果不可用")
        self.objective_result_label.setText("目标结果不可用")
        self.response_summary_label.setText(f"error={error}")
        logger.info("[recommend_ui] render_result status=请求失败 has_n=False has_fz=False has_predicted=False")

    def render_parsed_result(self, parsed: ParsedResult):
        self._set_loading(False, parsed.status_text)
        self.status_detail_label.setText(parsed.message or parsed.details or "请求完成")

        if parsed.kind == "recommendation":
            self.param_result_label.setText(
                f"推荐转速 n: {parsed.recommended_n if parsed.recommended_n is not None else '-'}\n"
                f"推荐每齿进给 fz: {parsed.recommended_fz if parsed.recommended_fz is not None else '-'}"
            )
        else:
            tip = "当前接口返回的是预测结果而非推荐参数" if parsed.kind == "prediction" else "未返回推荐参数"
            self.param_result_label.setText(
                f"当前输入 n: {parsed.input_n}\n"
                f"当前输入 fz: {parsed.input_fz}\n"
                f"说明: {tip}"
            )

        objective_lines = [f"优化目标 objective: {parsed.objective or self.objective_combo.currentText()}"]
        if parsed.objective_value is not None:
            objective_lines.append(f"目标值: {parsed.objective_value}")
        for key, value in parsed.predicted_values.items():
            objective_lines.append(f"{key}: {value}")
        if len(objective_lines) == 1:
            objective_lines.append("未识别到目标相关结果")
        self.objective_result_label.setText("\n".join(objective_lines))

        summary_lines = [
            f"success: {parsed.raw_success}",
            f"message: {parsed.raw_message or parsed.message}",
            f"fields: {', '.join(parsed.recognized_fields) if parsed.recognized_fields else 'none'}",
        ]
        if parsed.details:
            summary_lines.append(f"detail: {parsed.details}")
        self.response_summary_label.setText("\n".join(summary_lines))

        logger.info(
            "[recommend_ui] render_result status=%s has_n=%s has_fz=%s has_predicted=%s",
            parsed.status_text,
            parsed.recommended_n is not None,
            parsed.recommended_fz is not None,
            bool(parsed.predicted_values),
        )

# coding:utf-8
import logging

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout
from qfluentwidgets import (
    SubtitleLabel,
    StrongBodyLabel,
    BodyLabel,
    LineEdit,
    ComboBox,
    PrimaryPushButton,
    CardWidget,
    InfoBar,
)

from .nav_interface import NavInterface
from ..api.api_client import api_client
from ..api.async_api import AsyncApiHelper

logger = logging.getLogger(__name__)


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

        form_card = CardWidget(self)
        form_layout = QGridLayout(form_card)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(12)

        self.n_edit = LineEdit(self)
        self.n_edit.setPlaceholderText("请输入转速 n")
        self.fz_edit = LineEdit(self)
        self.fz_edit.setPlaceholderText("请输入每齿进给 fz")

        self.objective_combo = ComboBox(self)
        self.objective_combo.addItems(["A_damage", "F_damage"])

        self.model_type_combo = ComboBox(self)
        self.model_type_combo.addItems(["quad", "gp"])

        form_layout.addWidget(StrongBodyLabel("转速 n"), 0, 0)
        form_layout.addWidget(self.n_edit, 0, 1)
        form_layout.addWidget(StrongBodyLabel("每齿进给 fz"), 0, 2)
        form_layout.addWidget(self.fz_edit, 0, 3)

        form_layout.addWidget(StrongBodyLabel("优化目标"), 1, 0)
        form_layout.addWidget(self.objective_combo, 1, 1)
        form_layout.addWidget(StrongBodyLabel("模型类型"), 1, 2)
        form_layout.addWidget(self.model_type_combo, 1, 3)

        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        self.recommend_button = PrimaryPushButton("获取推荐")
        self.recommend_button.clicked.connect(self.fetch_recommendation)
        action_layout.addWidget(self.recommend_button)

        self.status_label = BodyLabel("等待请求")

        self.result_label = BodyLabel("推荐结果将在此显示")
        self.result_label.setWordWrap(True)

        self.main_layout.addWidget(form_card)
        self.main_layout.addLayout(action_layout)
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addWidget(self.result_label)
        self.main_layout.addStretch(1)

    def on_activated(self):
        pass

    def on_deactivated(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker = None

    def _set_loading(self, loading, text=""):
        self.recommend_button.setEnabled(not loading)
        self.status_label.setText(text or ("请求中..." if loading else "等待请求"))

    def fetch_recommendation(self):
        try:
            n = float(self.n_edit.text().strip())
            fz = float(self.fz_edit.text().strip())
        except ValueError:
            InfoBar.warning("输入错误", "请输入合法的 n 和 fz 数值", parent=self)
            return

        payload = {
            "n": n,
            "fz": fz,
            "objective": self.objective_combo.currentText(),
            "model_type": self.model_type_combo.currentText(),
        }

        self._set_loading(True, "正在检查服务状态...")

        def call_recommend():
            self._set_loading(True, "正在请求参数推荐...")
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
        self._set_loading(False, "推荐完成")
        if not response:
            self.result_label.setText("未获取到推荐结果")
            return

        best = response.get("best") or {}
        prediction = response.get("prediction") or {}
        uncertainty = response.get("uncertainty")

        best_n = best.get("n", response.get("n", "-"))
        best_fz = best.get("fz", response.get("fz", "-"))
        a_damage = prediction.get("A_damage", response.get("A_damage", "-"))
        f_damage = prediction.get("F_damage", response.get("F_damage", "-"))

        lines = [
            f"推荐参数: n={best_n}, fz={best_fz}",
            f"预测 A_damage: {a_damage}",
            f"预测 F_damage: {f_damage}",
        ]
        if uncertainty is not None:
            lines.append(f"不确定性: {uncertainty}")

        self.result_label.setText("\n".join(lines))

    def on_recommend_error(self, error):
        logger.error(f"recommend error: {error}")
        self._set_loading(False, "请求失败")
        InfoBar.error("请求失败", "无法连接后端推荐服务，请检查后端是否启动", parent=self)
        self.result_label.setText(f"请求失败: {error}")

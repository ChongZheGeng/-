# coding:utf-8
import logging

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView
from qfluentwidgets import (
    SubtitleLabel,
    StrongBodyLabel,
    BodyLabel,
    LineEdit,
    ComboBox,
    PrimaryPushButton,
    PushButton,
    CardWidget,
    InfoBar,
)

from .nav_interface import NavInterface
from ..api.api_client import api_client
from ..api.async_api import AsyncApiHelper

logger = logging.getLogger(__name__)


class RecommendationInterface(NavInterface):
    """参数推荐主页面（单点预测 + 按等级推荐）"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("RecommendationInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(18)

        self.main_layout.addWidget(SubtitleLabel("参数推荐"))

        self._build_dev_card()
        self._build_predict_card()
        self._build_recommend_card()
        self.main_layout.addStretch(1)

    def _build_dev_card(self):
        card = CardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel("开发工具"))
        self.btn_generate = PushButton("生成训练数据")
        self.btn_train = PushButton("训练模型")
        self.btn_generate.clicked.connect(self.generate_dataset)
        self.btn_train.clicked.connect(self.train_model)
        layout.addWidget(self.btn_generate)
        layout.addWidget(self.btn_train)
        layout.addStretch(1)

        self.main_layout.addWidget(card)

    def _build_predict_card(self):
        card = CardWidget(self)
        layout = QGridLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)

        layout.addWidget(StrongBodyLabel("单点预测"), 0, 0, 1, 4)

        self.speed_edit = LineEdit(self)
        self.speed_edit.setPlaceholderText("输入转速 speed，例如 5000")
        self.fz_edit = LineEdit(self)
        self.fz_edit.setPlaceholderText("输入每齿进给 fz，例如 0.05")

        self.btn_predict = PrimaryPushButton("预测 A损伤")
        self.btn_predict.clicked.connect(self.predict_damage)

        self.predict_result = BodyLabel("预测结果将在此显示")
        self.predict_result.setWordWrap(True)

        layout.addWidget(StrongBodyLabel("转速 speed"), 1, 0)
        layout.addWidget(self.speed_edit, 1, 1)
        layout.addWidget(StrongBodyLabel("每齿进给 fz"), 1, 2)
        layout.addWidget(self.fz_edit, 1, 3)
        layout.addWidget(self.btn_predict, 2, 3)
        layout.addWidget(self.predict_result, 3, 0, 1, 4)

        self.main_layout.addWidget(card)

    def _build_recommend_card(self):
        card = CardWidget(self)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        outer.addWidget(StrongBodyLabel("按等级推荐"))

        top = QHBoxLayout()
        self.level_combo = ComboBox(self)
        self.level_combo.addItems(["low（低损伤）", "medium（中损伤）", "high（高损伤）"])
        self.btn_recommend = PrimaryPushButton("获取推荐参数")
        self.btn_recommend.clicked.connect(self.fetch_recommendation)

        top.addWidget(StrongBodyLabel("目标等级"))
        top.addWidget(self.level_combo)
        top.addStretch(1)
        top.addWidget(self.btn_recommend)

        self.status_label = BodyLabel("等待请求")

        self.result_table = QTableWidget(self)
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["转速", "每齿进给", "预测A损伤", "损伤等级"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setAlternatingRowColors(True)

        outer.addLayout(top)
        outer.addWidget(self.status_label)
        outer.addWidget(self.result_table)

        self.main_layout.addWidget(card)

    def on_activated(self):
        pass

    def on_deactivated(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker = None

    def _set_loading(self, loading, text=""):
        self.btn_generate.setEnabled(not loading)
        self.btn_train.setEnabled(not loading)
        self.btn_predict.setEnabled(not loading)
        self.btn_recommend.setEnabled(not loading)
        self.status_label.setText(text or ("请求中..." if loading else "等待请求"))

    def _level_en(self):
        raw = self.level_combo.currentText()
        if raw.startswith("low"):
            return "low"
        if raw.startswith("medium"):
            return "medium"
        return "high"

    def generate_dataset(self):
        self._set_loading(True, "正在生成训练数据...")
        self.worker = AsyncApiHelper.call_async(
            api_client.generate_damage_dataset,
            self._on_generate_success,
            self._on_error,
            2000,
            timeout=30,
        )

    def train_model(self):
        self._set_loading(True, "正在训练模型...")
        self.worker = AsyncApiHelper.call_async(
            api_client.train_damage_model,
            self._on_train_success,
            self._on_error,
            timeout=90,
        )

    def predict_damage(self):
        try:
            speed = float(self.speed_edit.text().strip())
            fz = float(self.fz_edit.text().strip())
        except ValueError:
            InfoBar.warning("输入错误", "请输入合法的 speed 和 fz 数值", parent=self)
            return

        self._set_loading(True, "正在预测 A损伤...")
        self.worker = AsyncApiHelper.call_async(
            api_client.predict_damage,
            self._on_predict_success,
            self._on_error,
            speed,
            fz,
            timeout=20,
        )

    def fetch_recommendation(self):
        self._set_loading(True, "正在请求等级推荐...")
        self.worker = AsyncApiHelper.call_async(
            api_client.recommend_by_level,
            self._on_recommend_success,
            self._on_error,
            self._level_en(),
            5,
            timeout=20,
        )

    def _on_generate_success(self, response):
        self._set_loading(False, "训练数据生成完成")
        if response and response.get("success"):
            InfoBar.success("成功", f"已生成 {response.get('total_samples')} 条样本", parent=self)
        else:
            InfoBar.error("失败", (response or {}).get("error", "生成失败"), parent=self)

    def _on_train_success(self, response):
        self._set_loading(False, "模型训练完成")
        if response and response.get("success"):
            InfoBar.success("成功", f"最佳模型: {response.get('best_model')}", parent=self)
        else:
            InfoBar.error("失败", (response or {}).get("error", "训练失败"), parent=self)

    def _on_predict_success(self, response):
        self._set_loading(False, "预测完成")
        if not response or not response.get("success"):
            self.predict_result.setText(f"预测失败: {(response or {}).get('error', '未知错误')}")
            return

        self.predict_result.setText(
            f"预测A损伤: {response.get('predicted_A_damage'):.6f}\n"
            f"损伤等级: {response.get('damage_level')}"
        )

    def _on_recommend_success(self, response):
        self._set_loading(False, "推荐完成")
        results = (response or {}).get("results", []) if response and response.get("success") else []

        self.result_table.setRowCount(len(results))
        for row_idx, item in enumerate(results):
            self.result_table.setItem(row_idx, 0, QTableWidgetItem(str(item.get("speed"))))
            self.result_table.setItem(row_idx, 1, QTableWidgetItem(str(item.get("fz"))))
            self.result_table.setItem(row_idx, 2, QTableWidgetItem(str(item.get("predicted_A_damage"))))
            self.result_table.setItem(row_idx, 3, QTableWidgetItem(str(item.get("damage_level"))))

        if results:
            InfoBar.success("成功", f"已返回 {len(results)} 组推荐参数", parent=self)
        else:
            InfoBar.warning("提示", (response or {}).get("error", "未找到符合等级的参数"), parent=self)

    def _on_error(self, error):
        logger.error(f"recommendation error: {error}")
        self._set_loading(False, "请求失败")
        InfoBar.error("请求失败", str(error), parent=self)

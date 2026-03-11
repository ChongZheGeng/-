# coding:utf-8
import logging

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidgetItem
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
    TableWidget,
)

from .nav_interface import NavInterface
from ..api.api_client import api_client
from ..api.async_api import AsyncApiHelper

logger = logging.getLogger(__name__)


class RecommendationInterface(NavInterface):
    """A损伤预测推荐页面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DamageRecommendationInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("损伤预测与参数推荐"))

        self._init_predict_card()
        self._init_recommend_card()

        self.status_label = BodyLabel("等待请求")
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addStretch(1)

    def _init_predict_card(self):
        card = CardWidget(self)
        layout = QGridLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)

        layout.addWidget(StrongBodyLabel("区域1：单点预测"), 0, 0, 1, 4)

        self.speed_edit = LineEdit(self)
        self.speed_edit.setPlaceholderText("请输入转速 speed")
        self.feed_edit = LineEdit(self)
        self.feed_edit.setPlaceholderText("请输入进给量 feed")

        layout.addWidget(StrongBodyLabel("转速 speed"), 1, 0)
        layout.addWidget(self.speed_edit, 1, 1)
        layout.addWidget(StrongBodyLabel("进给量 feed"), 1, 2)
        layout.addWidget(self.feed_edit, 1, 3)

        self.predict_button = PrimaryPushButton("预测 A 损伤")
        self.predict_button.clicked.connect(self.fetch_prediction)
        self.train_button = PushButton("训练/刷新模型")
        self.train_button.clicked.connect(self.train_model)

        btn_line = QHBoxLayout()
        btn_line.addWidget(self.predict_button)
        btn_line.addWidget(self.train_button)
        btn_line.addStretch(1)
        layout.addLayout(btn_line, 2, 0, 1, 4)

        self.predict_result = BodyLabel("预测结果：-")
        self.predict_result.setWordWrap(True)
        layout.addWidget(self.predict_result, 3, 0, 1, 4)

        self.main_layout.addWidget(card)

    def _init_recommend_card(self):
        card = CardWidget(self)
        layout = QGridLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)

        layout.addWidget(StrongBodyLabel("区域2：按等级推荐"), 0, 0, 1, 4)

        self.level_combo = ComboBox(self)
        self.level_combo.addItems(["low", "medium", "high"])
        layout.addWidget(StrongBodyLabel("目标等级"), 1, 0)
        layout.addWidget(self.level_combo, 1, 1)

        self.recommend_button = PrimaryPushButton("获取推荐参数")
        self.recommend_button.clicked.connect(self.fetch_recommendation)
        layout.addWidget(self.recommend_button, 1, 2)

        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["序号", "speed", "feed", "predicted_damage_A", "level"])
        self.table.setRowCount(0)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 2, 0, 1, 4)

        self.main_layout.addWidget(card)

    def on_activated(self):
        pass

    def on_deactivated(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker = None

    def _set_loading(self, loading, text=""):
        self.predict_button.setEnabled(not loading)
        self.recommend_button.setEnabled(not loading)
        self.train_button.setEnabled(not loading)
        self.status_label.setText(text or ("请求中..." if loading else "等待请求"))

    def train_model(self):
        self._set_loading(True, "正在训练模型...")
        self.worker = AsyncApiHelper.call_async(
            api_client.train_damage_model,
            self.on_train_success,
            self.on_error,
            timeout=120,
        )

    def on_train_success(self, response):
        self._set_loading(False, "模型训练完成")
        if not response or not response.get("success"):
            InfoBar.error("训练失败", "训练接口返回失败", parent=self)
            return
        InfoBar.success("训练完成", f"最佳模型: {response.get('best_model')}", parent=self)

    def fetch_prediction(self):
        try:
            speed = float(self.speed_edit.text().strip())
            feed = float(self.feed_edit.text().strip())
        except ValueError:
            InfoBar.warning("输入错误", "请输入合法的 speed 和 feed 数值", parent=self)
            return

        self._set_loading(True, "正在预测损伤...")
        self.worker = AsyncApiHelper.call_async(
            api_client.predict_damage,
            self.on_predict_success,
            self.on_error,
            {"speed": speed, "feed": feed},
            timeout=15,
        )

    def on_predict_success(self, response):
        self._set_loading(False, "预测完成")
        if not response or not response.get("success"):
            self.predict_result.setText("预测结果：失败")
            return
        pred = response.get("predicted_damage_A")
        level = response.get("level")
        self.predict_result.setText(f"预测结果：predicted_damage_A={pred:.6f}，level={level}")

    def fetch_recommendation(self):
        level = self.level_combo.currentText()
        self._set_loading(True, "正在获取推荐参数...")
        self.worker = AsyncApiHelper.call_async(
            api_client.recommend_by_level,
            self.on_recommend_success,
            self.on_error,
            {"level": level},
            timeout=20,
        )

    def on_recommend_success(self, response):
        self._set_loading(False, "推荐完成")
        if not response or not response.get("success"):
            InfoBar.warning("提示", "未获取到推荐结果", parent=self)
            self.table.setRowCount(0)
            return

        recs = response.get("recommendations", [])
        self.table.setRowCount(len(recs))
        for i, rec in enumerate(recs):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(str(rec.get("speed"))))
            self.table.setItem(i, 2, QTableWidgetItem(str(rec.get("feed"))))
            self.table.setItem(i, 3, QTableWidgetItem(str(rec.get("predicted_damage_A"))))
            self.table.setItem(i, 4, QTableWidgetItem(str(rec.get("level"))))

    def on_error(self, error):
        logger.error(f"damage recommendation error: {error}")
        self._set_loading(False, "请求失败")
        InfoBar.error("请求失败", str(error), parent=self)

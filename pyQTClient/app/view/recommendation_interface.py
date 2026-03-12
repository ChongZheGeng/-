# coding:utf-8
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QDoubleSpinBox,
    QSpinBox,
    QWidget,
    QGroupBox,
)
from qfluentwidgets import (
    SubtitleLabel,
    StrongBodyLabel,
    BodyLabel,
    ComboBox,
    PrimaryPushButton,
    PushButton,
    CardWidget,
    InfoBar,
)

from .nav_interface import NavInterface
from ..api.async_api import AsyncApiHelper
from ..services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)


class SampleScatterWidget(QWidget):
    """简易散点图：展示样本分布与推荐点。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(260)
        self.samples = []
        self.recommend_points = []

    def update_data(self, samples, recommend_points):
        self.samples = samples or []
        self.recommend_points = recommend_points or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(40, 20, -20, -40)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setPen(QPen(QColor("#909090"), 1))
        painter.drawRect(rect)

        if not self.samples:
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无样本数据，请先生成数据或执行推荐")
            return

        min_speed = min(s["speed_n"] for s in self.samples)
        max_speed = max(s["speed_n"] for s in self.samples)
        min_fz = min(s["feed_fz"] for s in self.samples)
        max_fz = max(s["feed_fz"] for s in self.samples)

        def map_point(speed_n, feed_fz):
            x = rect.left() + (speed_n - min_speed) / max(1e-9, max_speed - min_speed) * rect.width()
            y = rect.bottom() - (feed_fz - min_fz) / max(1e-9, max_fz - min_fz) * rect.height()
            return int(x), int(y)

        color_map = {"low": QColor("#3A8EE6"), "medium": QColor("#F0A202"), "high": QColor("#D7263D")}
        for s in self.samples[:120]:
            painter.setPen(Qt.NoPen)
            painter.setBrush(color_map.get(s["damage_level"], QColor("#8A8A8A")))
            x, y = map_point(float(s["speed_n"]), float(s["feed_fz"]))
            painter.drawEllipse(x - 3, y - 3, 6, 6)

        for rp in self.recommend_points:
            painter.setBrush(QColor("#2ECC71"))
            painter.setPen(QPen(QColor("#1B8F52"), 2))
            x, y = map_point(float(rp["speed_n"]), float(rp["feed_fz"]))
            painter.drawEllipse(x - 6, y - 6, 12, 12)

        painter.setPen(QColor("#707070"))
        painter.drawText(rect.left(), rect.bottom() + 20, "转速 n")
        painter.save()
        painter.translate(14, rect.center().y())
        painter.rotate(-90)
        painter.drawText(0, 0, "每齿进给 fz")
        painter.restore()


class RecommendationInterface(NavInterface):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("RecommendationInterface")
        self.worker = None
        self.latest_result = None

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(36, 28, 36, 28)
        self.main_layout.setSpacing(16)

        self._build_header()
        self._build_input_card()
        self._build_result_card()
        self._build_visual_card()
        self._build_dev_card()
        self.main_layout.addStretch(1)

        self.refresh_status()

    def _build_header(self):
        self.main_layout.addWidget(SubtitleLabel("加工参数智能推荐"))
        self.main_layout.addWidget(BodyLabel("基于历史工况与规则生成样本，辅助给出复材加工推荐参数；当前版本支持模型推荐与规则推荐双模式。"))

    def _build_input_card(self):
        card = CardWidget(self)
        layout = QGridLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)
        layout.addWidget(StrongBodyLabel("工况输入区"), 0, 0, 1, 4)

        self.process_type = ComboBox(self); self.process_type.addItems(["铣削", "钻削"])
        self.material_type = ComboBox(self); self.material_type.addItems(["CFRP", "GFRP", "AFRP", "其他"])
        self.fiber_type = ComboBox(self); self.fiber_type.addItems(["碳纤维", "玻璃纤维", "其他"])
        self.resin_type = ComboBox(self); self.resin_type.addItems(["环氧", "BMI", "PEEK", "其他"])
        self.layup = ComboBox(self); self.layup.addItems(["0/90", "±45", "准各向同性", "其他"])
        self.tool_type = ComboBox(self); self.tool_type.addItems(["立铣刀", "麻花钻", "金刚石刀具", "其他"])
        self.tool_coating = ComboBox(self); self.tool_coating.addItems(["无涂层", "DLC", "金刚石", "TiAlN", "其他"])
        self.tool_wear = ComboBox(self); self.tool_wear.addItems(["新刀", "轻度磨损", "中度磨损", "重度磨损"])
        self.goal = ComboBox(self); self.goal.addItems(["低损伤", "高效率", "综合平衡"])
        self.target_damage_level = ComboBox(self); self.target_damage_level.addItems(["low（低）", "medium（中）", "high（高）"])

        self.thickness = QDoubleSpinBox(self); self.thickness.setRange(0.1, 200.0); self.thickness.setValue(8.0); self.thickness.setSuffix(" mm")
        self.tool_diameter = QDoubleSpinBox(self); self.tool_diameter.setRange(0.1, 50.0); self.tool_diameter.setValue(6.0); self.tool_diameter.setSuffix(" mm")
        self.remark = QTextEdit(self); self.remark.setPlaceholderText("可填写工况说明、边界条件或工艺备注")
        self.remark.setMaximumHeight(80)

        fields = [
            ("加工类型", self.process_type), ("材料类型", self.material_type),
            ("纤维类型", self.fiber_type), ("树脂类型", self.resin_type),
            ("铺层方向", self.layup), ("厚度(mm)", self.thickness),
            ("刀具类型", self.tool_type), ("刀具直径(mm)", self.tool_diameter),
            ("刀具涂层", self.tool_coating), ("刀具磨损状态", self.tool_wear),
            ("加工目标", self.goal), ("目标损伤等级", self.target_damage_level),
        ]

        row = 1
        for idx in range(0, len(fields), 2):
            l1, w1 = fields[idx]
            l2, w2 = fields[idx + 1]
            layout.addWidget(BodyLabel(l1), row, 0)
            layout.addWidget(w1, row, 1)
            layout.addWidget(BodyLabel(l2), row, 2)
            layout.addWidget(w2, row, 3)
            row += 1

        layout.addWidget(BodyLabel("备注"), row, 0)
        layout.addWidget(self.remark, row, 1, 1, 3)
        row += 1

        self.mode_label = BodyLabel("当前模式：规则推荐")
        self.recommend_btn = PrimaryPushButton("生成推荐方案")
        self.recommend_btn.clicked.connect(self.handle_recommend)
        layout.addWidget(self.mode_label, row, 0, 1, 2)
        layout.addWidget(self.recommend_btn, row, 3)

        self.main_layout.addWidget(card)

    def _build_result_card(self):
        card = CardWidget(self)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(10)
        outer.addWidget(StrongBodyLabel("推荐结果区"))

        self.result_hint = BodyLabel("请先输入目标工况并点击“生成推荐方案”")
        outer.addWidget(self.result_hint)

        self.plan_cards = []
        row = QHBoxLayout()
        for _ in range(3):
            plan_card = CardWidget(self)
            plan_layout = QVBoxLayout(plan_card)
            plan_layout.setContentsMargins(14, 12, 14, 12)
            plan_layout.setSpacing(6)
            title = StrongBodyLabel("-" )
            speed = BodyLabel("n: -")
            fz = BodyLabel("fz: -")
            score = BodyLabel("评分: -")
            level = BodyLabel("预计损伤: -")
            desc = BodyLabel("说明: -")
            desc.setWordWrap(True)
            for w in (title, speed, fz, score, level, desc):
                plan_layout.addWidget(w)
            self.plan_cards.append((title, speed, fz, score, level, desc))
            row.addWidget(plan_card)
        outer.addLayout(row)

        action_row = QHBoxLayout()
        self.btn_apply_task = PushButton("一键带入任务参数（预留）")
        self.btn_save = PushButton("保存推荐记录")
        self.btn_export = PushButton("导出推荐结果")
        self.btn_apply_task.clicked.connect(lambda: InfoBar.info("提示", "已预留任务参数带入接口", parent=self))
        self.btn_save.clicked.connect(self.save_record)
        self.btn_export.clicked.connect(self.export_result)
        action_row.addWidget(self.btn_apply_task)
        action_row.addWidget(self.btn_save)
        action_row.addWidget(self.btn_export)
        action_row.addStretch(1)
        outer.addLayout(action_row)

        self.main_layout.addWidget(card)

    def _build_visual_card(self):
        card = CardWidget(self)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(10)
        outer.addWidget(StrongBodyLabel("推荐依据 / 可视化"))

        self.sample_table = QTableWidget(self)
        self.sample_table.setColumnCount(4)
        self.sample_table.setHorizontalHeaderLabels(["speed_n", "feed_fz", "A_damage", "damage_level"])
        self.sample_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sample_table.setMinimumHeight(190)

        self.chart_widget = SampleScatterWidget(self)
        outer.addWidget(BodyLabel("相似样本（参考）"))
        outer.addWidget(self.sample_table)
        outer.addWidget(BodyLabel("参数分布图（推荐点位置）"))
        outer.addWidget(self.chart_widget)

        self.main_layout.addWidget(card)

    def _build_dev_card(self):
        card = CardWidget(self)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(8)

        self.dev_group = QGroupBox("数据生成与模型训练（开发者区域）")
        self.dev_group.setCheckable(True)
        self.dev_group.setChecked(False)
        group_layout = QVBoxLayout(self.dev_group)

        cfg_row = QHBoxLayout()
        self.num_samples = QSpinBox(self); self.num_samples.setRange(100, 100000); self.num_samples.setValue(2000)
        self.random_seed = QSpinBox(self); self.random_seed.setRange(0, 999999); self.random_seed.setValue(42)
        self.overwrite = ComboBox(self); self.overwrite.addItems(["覆盖旧数据", "保留旧数据"])
        cfg_row.addWidget(BodyLabel("生成条数")); cfg_row.addWidget(self.num_samples)
        cfg_row.addWidget(BodyLabel("随机种子")); cfg_row.addWidget(self.random_seed)
        cfg_row.addWidget(BodyLabel("数据策略")); cfg_row.addWidget(self.overwrite)
        cfg_row.addStretch(1)

        train_row = QHBoxLayout()
        self.model_type = ComboBox(self); self.model_type.addItems(["RandomForest", "KNN", "LogisticRegression", "XGBoost(占位)"])
        self.retrain = ComboBox(self); self.retrain.addItems(["重新训练", "若存在则跳过"])
        self.btn_generate = PushButton("生成模拟训练数据")
        self.btn_train = PushButton("训练推荐模型")
        self.btn_refresh = PushButton("查看训练状态")
        self.btn_generate.clicked.connect(self.generate_dataset)
        self.btn_train.clicked.connect(self.train_model)
        self.btn_refresh.clicked.connect(self.refresh_status)
        for w in (BodyLabel("模型类型"), self.model_type, BodyLabel("训练策略"), self.retrain, self.btn_generate, self.btn_train, self.btn_refresh):
            train_row.addWidget(w)
        train_row.addStretch(1)

        self.status_text = BodyLabel("状态加载中...")
        self.log_box = QTextEdit(self)
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(120)

        group_layout.addLayout(cfg_row)
        group_layout.addLayout(train_row)
        group_layout.addWidget(self.status_text)
        group_layout.addWidget(self.log_box)

        outer.addWidget(self.dev_group)
        self.main_layout.addWidget(card)

    def _collect_form_data(self):
        return {
            "process_type": self.process_type.currentText(),
            "material_type": self.material_type.currentText(),
            "fiber_type": self.fiber_type.currentText(),
            "resin_type": self.resin_type.currentText(),
            "layup": self.layup.currentText(),
            "thickness_mm": self.thickness.value(),
            "tool_type": self.tool_type.currentText(),
            "tool_diameter_mm": self.tool_diameter.value(),
            "tool_coating": self.tool_coating.currentText(),
            "tool_wear": self.tool_wear.currentText(),
            "goal": self.goal.currentText(),
            "target_damage_level": self._target_level_en(),
            "remark": self.remark.toPlainText().strip(),
        }

    def _target_level_en(self):
        text = self.target_damage_level.currentText()
        if text.startswith("low"):
            return "low"
        if text.startswith("high"):
            return "high"
        return "medium"


    def open_task_from_dashboard(self, task_code):
        """从系统概览跳转时，打开对应任务上下文（当前版本为页面内定位）。"""
        if not task_code:
            return

        self.result_hint.setText(f"已从系统概览定位到任务 {task_code}，请确认工况后生成或复核推荐参数。")
        existing = self.remark.toPlainText().strip()
        prefix = f"[任务上下文] {task_code}"
        if prefix not in existing:
            self.remark.setPlainText(f"{prefix}\n{existing}".strip())

        InfoBar.success(
            title="已打开任务",
            content=f"任务 {task_code} 已带入参数推荐页",
            parent=self,
            duration=2000,
        )

    def _set_loading(self, loading, hint=""):
        self.recommend_btn.setEnabled(not loading)
        self.btn_generate.setEnabled(not loading)
        self.btn_train.setEnabled(not loading)
        if hint:
            self.result_hint.setText(hint)

    def handle_recommend(self):
        self._set_loading(True, "正在分析并生成候选方案...")
        self.worker = AsyncApiHelper.call_async(
            recommendation_service.recommend,
            self._on_recommend_success,
            self._on_error,
            self._collect_form_data(),
        )

    def generate_dataset(self):
        self._set_loading(True, "正在生成模拟训练数据...")
        self.worker = AsyncApiHelper.call_async(
            recommendation_service.generate_dataset,
            self._on_generate_success,
            self._on_error,
            self.num_samples.value(),
            self.random_seed.value(),
            self.overwrite.currentText().startswith("覆盖"),
        )

    def train_model(self):
        self._set_loading(True, "正在训练推荐模型...")
        self.worker = AsyncApiHelper.call_async(
            recommendation_service.train_model,
            self._on_train_success,
            self._on_error,
            self.model_type.currentText(),
            self.retrain.currentText().startswith("重新"),
        )

    def refresh_status(self):
        status = recommendation_service.get_status()
        self.mode_label.setText(f"当前模式：{'模型推荐' if status.get('has_model') else '规则推荐'}")
        self.status_text.setText(
            f"数据集: {'已生成' if status.get('has_dataset') else '未生成'} | 模型: {'已训练' if status.get('has_model') else '未训练'} | "
            f"最近训练时间: {status.get('last_trained_at', '-') }\n阈值配置: {status.get('threshold_config')}"
        )

    def save_record(self):
        if not self.latest_result:
            InfoBar.warning("提示", "暂无可保存的推荐结果", parent=self)
            return
        result = recommendation_service.save_record(self.latest_result)
        InfoBar.success("已保存", result.get("record_path", ""), parent=self)

    def export_result(self):
        if not self.latest_result:
            InfoBar.warning("提示", "暂无可导出的推荐结果", parent=self)
            return
        result = recommendation_service.export_result(self.latest_result, "json")
        InfoBar.success("导出成功", result.get("export_path", ""), parent=self)

    def _on_generate_success(self, result):
        self._set_loading(False)
        if result.get("success"):
            self.log_box.append(f"[数据生成] {result}")
            InfoBar.success("成功", f"训练数据已准备：{result.get('total_samples')} 条", parent=self)
        else:
            InfoBar.error("失败", result.get("error", "生成失败"), parent=self)
        self.refresh_status()

    def _on_train_success(self, result):
        self._set_loading(False)
        if result.get("success"):
            self.log_box.append(f"[模型训练] {result}")
            InfoBar.success("训练完成", f"准确率: {result.get('accuracy', '-')}", parent=self)
        else:
            InfoBar.error("失败", result.get("error", "训练失败"), parent=self)
        self.refresh_status()

    def _on_recommend_success(self, result):
        self._set_loading(False)
        if not result.get("success"):
            self.result_hint.setText(result.get("error", "推荐失败"))
            return

        self.latest_result = result
        self.mode_label.setText(f"当前模式：{result.get('mode', '规则推荐')}")
        self.result_hint.setText(f"推荐完成：目标损伤等级 {result.get('target_level')}，输出 3 组候选方案")

        plans = result.get("plans", [])
        for idx, (t, s, fz, score, lv, desc) in enumerate(self.plan_cards):
            if idx < len(plans):
                p = plans[idx]
                t.setText(p["name"])
                s.setText(f"推荐转速 n: {p['speed_n']} rpm")
                fz.setText(f"推荐每齿进给 fz: {p['feed_fz']} mm/z")
                score.setText(f"推荐评分: {p['score']}/100")
                lv.setText(f"预计损伤等级: {p['estimated_damage_level']}")
                desc.setText(f"说明: {p['description']}")

        similar = result.get("similar_samples", [])
        self.sample_table.setRowCount(len(similar))
        for i, row in enumerate(similar):
            self.sample_table.setItem(i, 0, QTableWidgetItem(str(row["speed_n"])))
            self.sample_table.setItem(i, 1, QTableWidgetItem(str(row["feed_fz"])))
            self.sample_table.setItem(i, 2, QTableWidgetItem(str(row["A_damage"])))
            self.sample_table.setItem(i, 3, QTableWidgetItem(str(row["damage_level"])))

        self.chart_widget.update_data(result.get("samples", []), plans)

    def _on_error(self, error):
        logger.error("recommendation error: %s", error)
        self._set_loading(False)
        InfoBar.error("请求失败", str(error), parent=self)

    def on_deactivated(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker = None

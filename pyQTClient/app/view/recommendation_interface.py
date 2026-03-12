# coding:utf-8
import logging

from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QDoubleSpinBox, QSpinBox
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    InfoBar,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    StrongBodyLabel,
)

from ..api.api_client import api_client
from ..api.async_api import AsyncApiHelper
from ..services.recommendation_service import RecommendationService
from .components.recommendation_chart_card import RecommendationChartCard
from .components.recommendation_result_card import RecommendationResultCard
from .components.recommendation_sample_table import RecommendationSampleTable
from .nav_interface import NavInterface

logger = logging.getLogger(__name__)


class RecommendationInterface(NavInterface):
    """参数推荐工作台页面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("RecommendationInterface")

        self.worker = None
        self.recommendation_service = RecommendationService()
        self.last_backend_response = None

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(18)

        self.main_layout.addWidget(SubtitleLabel("参数推荐"))
        self.main_layout.addWidget(BodyLabel("加工参数智能推荐工作台"))

        self._build_input_section()
        self._build_result_section()
        self._build_sample_section()
        self._build_visualization_section()
        self._build_data_train_section()

        self.main_layout.addStretch(1)
        self._refresh_all_views()

    def _build_input_section(self):
        self.input_card = CardWidget(self)
        layout = QVBoxLayout(self.input_card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(StrongBodyLabel("1. 工况输入"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        self.process_type_combo = ComboBox(self)
        self.process_type_combo.addItems(["铣削", "钻削"])

        self.material_combo = ComboBox(self)
        self.material_combo.addItems(["CFRP", "GFRP", "复合材料示例A", "复合材料示例B"])

        self.component_combo = ComboBox(self)
        self.component_combo.addItems(["机翼蒙皮#A01", "框梁接头#B12", "腹板构件#C03", "演示构件#D99"])

        self.tool_type_combo = ComboBox(self)
        self.tool_type_combo.addItems(["立铣刀", "麻花钻", "PCD刀具", "硬质合金刀具"])

        self.tool_diameter_combo = ComboBox(self)
        self.tool_diameter_combo.addItems(["4", "6", "8", "10", "12"])

        self.tool_coating_combo = ComboBox(self)
        self.tool_coating_combo.addItems(["无涂层", "TiAlN", "DLC", "PCD"])

        self.goal_combo = ComboBox(self)
        self.goal_combo.addItems(["低损伤", "高效率", "综合最优"])

        self.damage_target_combo = ComboBox(self)
        self.damage_target_combo.addItems(["low", "medium", "high"])
        self.damage_target_combo.setCurrentText("medium")

        self.n_input = QDoubleSpinBox(self)
        self.n_input.setRange(1000, 50000)
        self.n_input.setValue(12000)
        self.n_input.setDecimals(1)

        self.fz_input = QDoubleSpinBox(self)
        self.fz_input.setRange(0.005, 0.5)
        self.fz_input.setSingleStep(0.005)
        self.fz_input.setDecimals(4)
        self.fz_input.setValue(0.06)

        self.model_combo = ComboBox(self)
        self.model_combo.addItems(["rule", "poly", "rf"])

        self.remark_edit = LineEdit(self)
        self.remark_edit.setPlaceholderText("可选备注：例如刀具磨损偏高，保守推荐")

        fields = [
            ("加工方式", self.process_type_combo),
            ("材料类型", self.material_combo),
            ("构件名称", self.component_combo),
            ("刀具类型", self.tool_type_combo),
            ("刀具直径(mm)", self.tool_diameter_combo),
            ("刀具涂层", self.tool_coating_combo),
            ("加工目标", self.goal_combo),
            ("损伤等级目标", self.damage_target_combo),
            ("转速 n", self.n_input),
            ("每齿进给 fz", self.fz_input),
            ("模型类型", self.model_combo),
            ("备注", self.remark_edit),
        ]

        for i, (title, widget) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2
            grid.addWidget(BodyLabel(title), row, col)
            grid.addWidget(widget, row, col + 1)

        layout.addLayout(grid)

        action_layout = QHBoxLayout()
        self.recommend_btn = PrimaryPushButton("获取推荐")
        self.clear_btn = PushButton("清空输入")
        self.fill_demo_btn = PushButton("填充示例工况")
        self.status_label = BodyLabel("状态：等待输入")

        action_layout.addWidget(self.recommend_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addWidget(self.fill_demo_btn)
        action_layout.addStretch(1)
        action_layout.addWidget(self.status_label)

        self.recommend_btn.clicked.connect(self.fetch_recommendation)
        self.clear_btn.clicked.connect(self.clear_input)
        self.fill_demo_btn.clicked.connect(self.fill_demo_input)

        layout.addLayout(action_layout)
        self.main_layout.addWidget(self.input_card)

    def _build_result_section(self):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel("2. 推荐结果"))
        self.current_predict_label = BodyLabel("当前工况预测值：--")
        layout.addWidget(self.current_predict_label)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.result_cards = [
            RecommendationResultCard("方案 A：低损伤优先", self),
            RecommendationResultCard("方案 B：效率优先", self),
            RecommendationResultCard("方案 C：综合平衡", self),
        ]
        for item in self.result_cards:
            row.addWidget(item, 1)

        layout.addLayout(row)
        self.main_layout.addWidget(card)

    def _build_sample_section(self):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel("3. 推荐依据 / 相似样本"))
        self.sample_table = RecommendationSampleTable(self)
        layout.addWidget(self.sample_table)
        self.main_layout.addWidget(card)

    def _build_visualization_section(self):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel("4. 可视化分析"))
        self.chart_card = RecommendationChartCard(self)
        layout.addWidget(self.chart_card)
        self.main_layout.addWidget(card)

    def _build_data_train_section(self):
        self.bottom_card = CardWidget(self)
        layout = QVBoxLayout(self.bottom_card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel("5. 数据生成与模型训练"))
        layout.addWidget(BodyLabel("此区域为开发与答辩备用，位于页面最底部。"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        self.sample_count_spin = QSpinBox(self)
        self.sample_count_spin.setRange(200, 20000)
        self.sample_count_spin.setValue(2000)

        self.generate_status_label = BodyLabel("最近一次生成状态：未生成")
        self.data_path_label = BodyLabel("数据保存路径：--")

        self.model_status_label = BodyLabel("当前模型状态：未训练")
        self.model_type_label = BodyLabel("模型类型：rule")
        self.model_time_label = BodyLabel("最近训练时间：--")
        self.model_summary_label = BodyLabel("训练结果摘要：--")

        grid.addWidget(BodyLabel("生成样本数"), 0, 0)
        grid.addWidget(self.sample_count_spin, 0, 1)
        grid.addWidget(self.generate_status_label, 1, 0, 1, 4)
        grid.addWidget(self.data_path_label, 2, 0, 1, 4)

        grid.addWidget(self.model_status_label, 3, 0, 1, 4)
        grid.addWidget(self.model_type_label, 4, 0, 1, 4)
        grid.addWidget(self.model_time_label, 5, 0, 1, 4)
        grid.addWidget(self.model_summary_label, 6, 0, 1, 4)

        layout.addLayout(grid)

        action = QHBoxLayout()
        self.generate_btn = PushButton("生成数据")
        self.train_btn = PrimaryPushButton("训练模型")
        self.reload_btn = PushButton("重新加载模型")
        self.export_data_btn = PushButton("导出训练数据")
        self.export_result_btn = PushButton("导出推荐结果")

        self.generate_btn.clicked.connect(self.generate_data)
        self.train_btn.clicked.connect(self.train_model)
        self.reload_btn.clicked.connect(self.reload_model)
        self.export_data_btn.clicked.connect(self.export_training_data)
        self.export_result_btn.clicked.connect(self.export_recommendation)

        action.addWidget(self.generate_btn)
        action.addWidget(self.train_btn)
        action.addWidget(self.reload_btn)
        action.addWidget(self.export_data_btn)
        action.addWidget(self.export_result_btn)
        action.addStretch(1)

        layout.addLayout(action)
        self.main_layout.addWidget(self.bottom_card)

    def _collect_payload(self):
        return {
            "process_type": self.process_type_combo.currentText(),
            "material_type": self.material_combo.currentText(),
            "component_name": self.component_combo.currentText(),
            "tool_type": self.tool_type_combo.currentText(),
            "tool_diameter": self.tool_diameter_combo.currentText(),
            "tool_coating": self.tool_coating_combo.currentText(),
            "machining_goal": self.goal_combo.currentText(),
            "damage_target": self.damage_target_combo.currentText(),
            "n": float(self.n_input.value()),
            "fz": float(self.fz_input.value()),
            "model_type": self.model_combo.currentText(),
            "remark": self.remark_edit.text().strip(),
        }

    def _refresh_all_views(self):
        payload = self._collect_payload()
        result = self.recommendation_service.recommend(payload)
        self._update_result_ui(result)
        self._update_train_status()

    def _set_loading(self, loading: bool, text: str):
        self.recommend_btn.setEnabled(not loading)
        self.status_label.setText(f"状态：{text}")

    def fetch_recommendation(self):
        payload = self._collect_payload()
        backend_payload = {
            "n": payload["n"],
            "fz": payload["fz"],
            "objective": "A_damage",
            "model_type": payload["model_type"],
            "damage_target": payload["damage_target"],
            "machining_goal": payload["machining_goal"],
        }
        self._set_loading(True, "加载中：正在请求后端推荐")

        self.worker = AsyncApiHelper.call_async(
            api_client.recommend_parameters,
            lambda resp: self.on_recommend_success(resp, payload),
            lambda err: self.on_recommend_error(err, payload),
            backend_payload,
            timeout=8,
        )

    def on_recommend_success(self, response, payload):
        self._set_loading(False, "成功：已返回推荐结果")
        self.last_backend_response = response if isinstance(response, dict) else None
        result = self.recommendation_service.recommend(payload, backend_result=self.last_backend_response)
        self._update_result_ui(result)
        mode_text = "后端推荐+前端补全" if result.get("mode") == "prediction" else "本地fallback"
        InfoBar.success("推荐完成", f"模式：{mode_text}", parent=self)

    def on_recommend_error(self, error, payload):
        logger.error("recommend error: %s", error)
        self._set_loading(False, "失败：后端不可用，已使用本地fallback")
        result = self.recommendation_service.recommend(payload, backend_result=None)
        self._update_result_ui(result)
        InfoBar.warning("后端不可用", "已切换为本地推荐 fallback，演示可继续", parent=self)

    def _update_result_ui(self, result: dict):
        cards = result.get("cards") or []
        for idx, card in enumerate(self.result_cards):
            card_data = cards[idx] if idx < len(cards) else {}
            card.update_data(card_data)

        prediction = result.get("current_prediction")
        if prediction:
            self.current_predict_label.setText(
                f"当前工况预测值：A_damage={prediction.get('A_damage')}，"
                f"F_damage={prediction.get('F_damage')}，等级={prediction.get('damage_level')}"
            )
        else:
            self.current_predict_label.setText("当前工况预测值：--")

        samples = result.get("samples") or []
        self.sample_table.update_samples(samples)
        recommend_point = cards[0] if cards else None
        self.chart_card.update_data(self.recommendation_service.dataset, recommend_point)

    def clear_input(self):
        self.process_type_combo.setCurrentIndex(0)
        self.material_combo.setCurrentIndex(0)
        self.component_combo.setCurrentIndex(0)
        self.tool_type_combo.setCurrentIndex(0)
        self.tool_diameter_combo.setCurrentIndex(0)
        self.tool_coating_combo.setCurrentIndex(0)
        self.goal_combo.setCurrentText("综合最优")
        self.damage_target_combo.setCurrentText("medium")
        self.n_input.setValue(12000)
        self.fz_input.setValue(0.06)
        self.model_combo.setCurrentText("rule")
        self.remark_edit.clear()
        self.status_label.setText("状态：输入已清空")

    def fill_demo_input(self):
        self.process_type_combo.setCurrentText("铣削")
        self.material_combo.setCurrentText("CFRP")
        self.component_combo.setCurrentText("机翼蒙皮#A01")
        self.tool_type_combo.setCurrentText("PCD刀具")
        self.tool_diameter_combo.setCurrentText("8")
        self.tool_coating_combo.setCurrentText("DLC")
        self.goal_combo.setCurrentText("低损伤")
        self.damage_target_combo.setCurrentText("low")
        self.n_input.setValue(9800)
        self.fz_input.setValue(0.042)
        self.model_combo.setCurrentText("rf")
        self.remark_edit.setText("答辩演示工况：保守策略")
        self.status_label.setText("状态：已填充示例工况")

    def generate_data(self):
        samples = self.recommendation_service.generate_dataset(self.sample_count_spin.value())
        path = self.recommendation_service.persist_dataset()
        self.generate_status_label.setText(f"最近一次生成状态：生成成功，共 {len(samples)} 条")
        self.data_path_label.setText(f"数据保存路径：{path}")
        InfoBar.success("数据生成完成", f"已生成并保存至 {path}", parent=self)
        self._refresh_all_views()

    def train_model(self):
        result = self.recommendation_service.train_model(self.model_combo.currentText())
        self._update_train_status(result)
        InfoBar.success("训练完成", result.get("summary", "训练成功"), parent=self)

    def _update_train_status(self, result: dict = None):
        if result is None:
            result = {
                "status": self.recommendation_service.model_status,
                "model_type": self.recommendation_service.model_type,
                "last_train_time": self.recommendation_service.last_train_time,
                "summary": self.recommendation_service.train_summary,
            }
        self.model_status_label.setText(f"当前模型状态：{result.get('status', '--')}")
        self.model_type_label.setText(f"模型类型：{result.get('model_type', '--')}")
        self.model_time_label.setText(f"最近训练时间：{result.get('last_train_time', '--')}")
        self.model_summary_label.setText(f"训练结果摘要：{result.get('summary', '--')}")

    def reload_model(self):
        message = self.recommendation_service.reload_model()
        InfoBar.info("模型加载", message, parent=self)

    def export_training_data(self):
        path = self.recommendation_service.export_training_data()
        InfoBar.success("导出成功", f"训练数据已导出：{path}", parent=self)

    def export_recommendation(self):
        path = self.recommendation_service.export_recommendation()
        InfoBar.success("导出成功", f"推荐结果已导出：{path}", parent=self)

    def on_activated(self):
        pass

    def on_deactivated(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker = None

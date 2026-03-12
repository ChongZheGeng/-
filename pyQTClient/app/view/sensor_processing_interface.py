# coding:utf-8
import logging
from typing import Dict, Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    CaptionLabel,
    CheckBox,
    ComboBox,
    InfoBar,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)

from ..services.signal_processing_service import SignalData, SignalProcessingService
from .components.signal_plot_widget import SignalPlotWidget
from .nav_interface import NavInterface

logger = logging.getLogger(__name__)


class _LoadSignalWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, service: SignalProcessingService, source_text: str):
        super().__init__()
        self._service = service
        self._source_text = source_text

    def run(self):
        try:
            data = self._service.load_signal(self._source_text if self._source_text != "" else None)
            self.finished.emit(data)
        except Exception as exc:
            self.failed.emit(str(exc))


class _ProcessSignalWorker(QObject):
    finished = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, service: SignalProcessingService, signal_data: SignalData, params: dict):
        super().__init__()
        self._service = service
        self._signal_data = signal_data
        self._params = params

    def run(self):
        try:
            x_data, y_data = self._service.preprocess_signal(self._signal_data, **self._params)
            self.finished.emit(x_data, y_data)
        except Exception as exc:
            self.failed.emit(str(exc))


class SensorProcessingInterface(NavInterface):
    """传感器处理页面（第三阶段：特征提取 + 导出 + 与数据管理联动）"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SensorProcessingInterface")

        self.signal_service = SignalProcessingService()
        self.loaded_signal_data = None
        self.current_record: Optional[Dict] = None
        self.current_processed_x = []
        self.current_processed_y = []
        self.current_features: Dict[str, float] = {}

        self.load_thread = None
        self.load_worker = None
        self.process_thread = None
        self.process_worker = None

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(20)

        self._build_header()
        self._build_content()
        self._build_bottom_actions()
        self._connect_signals()

    def _build_header(self):
        title_label = SubtitleLabel("传感器数据处理")
        self.main_layout.addWidget(title_label)

        info_card = CardWidget(self)
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(24)

        self.record_info_label = BodyLabel("当前数据记录：未选择")
        self.filename_info_label = BodyLabel("文件名：--")
        self.task_info_label = BodyLabel("任务编号：--")
        self.sample_info_label = BodyLabel("采样率：--")

        info_layout.addWidget(self.record_info_label)
        info_layout.addWidget(self.filename_info_label)
        info_layout.addWidget(self.task_info_label)
        info_layout.addWidget(self.sample_info_label)
        info_layout.addStretch(1)

        self.main_layout.addWidget(info_card)

    def _build_content(self):
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        control_card = CardWidget(self)
        control_card.setMinimumWidth(320)
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.setSpacing(12)

        control_layout.addWidget(BodyLabel("数据选择"))
        self.data_selector = ComboBox(control_card)
        self.data_selector.addItems(["", "示例数据 A", "示例数据 B", "示例数据 C"])
        self.data_selector.setCurrentIndex(1)
        control_layout.addWidget(self.data_selector)

        control_layout.addSpacing(8)
        control_layout.addWidget(BodyLabel("通道选择"))
        self.channel_selector = ComboBox(control_card)
        self.channel_selector.addItems(["Fx", "Fy", "Fz", "F"])
        control_layout.addWidget(self.channel_selector)

        control_layout.addSpacing(8)
        control_layout.addWidget(BodyLabel("基础处理参数"))

        self.remove_dc_checkbox = CheckBox("去均值 / 去直流偏置", control_card)
        self.remove_dc_checkbox.setChecked(True)
        control_layout.addWidget(self.remove_dc_checkbox)

        control_layout.addWidget(CaptionLabel("移动平均窗口长度"))
        self.smooth_window_spin = QSpinBox(control_card)
        self.smooth_window_spin.setRange(1, 2000)
        self.smooth_window_spin.setValue(5)
        control_layout.addWidget(self.smooth_window_spin)

        self.resultant_checkbox = CheckBox("计算合力 F = sqrt(Fx² + Fy² + Fz²)", control_card)
        control_layout.addWidget(self.resultant_checkbox)

        control_layout.addWidget(CaptionLabel("时间窗口（样本索引）"))
        window_layout = QHBoxLayout()
        self.start_index_spin = QSpinBox(control_card)
        self.start_index_spin.setRange(0, 9999999)
        self.start_index_spin.setValue(0)
        self.end_index_spin = QSpinBox(control_card)
        self.end_index_spin.setRange(0, 9999999)
        self.end_index_spin.setValue(2000)
        window_layout.addWidget(self.start_index_spin)
        window_layout.addWidget(BodyLabel("至"))
        window_layout.addWidget(self.end_index_spin)
        control_layout.addLayout(window_layout)

        self.processing_status_label = CaptionLabel("状态：空闲")
        control_layout.addWidget(self.processing_status_label)
        control_layout.addStretch(1)

        chart_layout = QVBoxLayout()
        chart_layout.setSpacing(12)
        self.raw_plot_widget = SignalPlotWidget("原始波形")
        self.processed_plot_widget = SignalPlotWidget("处理后波形")

        feature_card = CardWidget(self)
        feature_layout = QVBoxLayout(feature_card)
        feature_layout.setContentsMargins(16, 12, 16, 12)
        feature_layout.setSpacing(8)
        feature_layout.addWidget(BodyLabel("特征表"))

        self.feature_table = QTableWidget(feature_card)
        self.feature_table.setColumnCount(2)
        self.feature_table.setHorizontalHeaderLabels(["特征", "值"])
        self.feature_table.verticalHeader().hide()
        self.feature_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.feature_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.feature_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        feature_layout.addWidget(self.feature_table)

        chart_layout.addWidget(self.raw_plot_widget, 1)
        chart_layout.addWidget(self.processed_plot_widget, 1)
        chart_layout.addWidget(feature_card, 1)

        content_layout.addWidget(control_card, 0)
        content_layout.addLayout(chart_layout, 1)
        self.main_layout.addLayout(content_layout, 1)

    def _build_bottom_actions(self):
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.load_btn = PushButton("加载数据")
        self.apply_btn = PrimaryPushButton("应用处理")
        self.reset_btn = PushButton("重置")
        self.export_signal_btn = PushButton("导出处理信号 CSV")
        self.export_features_btn = PushButton("导出特征 CSV/JSON")
        self.send_to_recommend_btn = PushButton("发送到推荐模块")

        self.export_signal_btn.setEnabled(False)
        self.export_features_btn.setEnabled(False)
        self.send_to_recommend_btn.setEnabled(False)

        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.export_signal_btn)
        button_layout.addWidget(self.export_features_btn)
        button_layout.addWidget(self.send_to_recommend_btn)
        button_layout.addStretch(1)

        self.main_layout.addLayout(button_layout)

    def _connect_signals(self):
        self.load_btn.clicked.connect(self._on_load_clicked)
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        self.export_signal_btn.clicked.connect(self._on_export_signal)
        self.export_features_btn.clicked.connect(self._on_export_features)
        self.send_to_recommend_btn.clicked.connect(self._on_send_to_recommend)

    def set_current_record(self, record: Dict):
        """供数据管理页调用，设置当前记录并预填 UI。"""
        self.current_record = record
        record_id = record.get("id", "--")
        file_url = record.get("file_url", "")
        task_info = record.get("task_info") or {}
        task_code = task_info.get("task_code", "--")

        self.record_info_label.setText(f"当前数据记录ID：{record_id}")
        self.filename_info_label.setText(f"文件名：{file_url or '--'}")
        self.task_info_label.setText(f"任务编号：{task_code}")

        if file_url:
            self.data_selector.setCurrentText(file_url)
        self._set_status("已接收记录，可点击“加载数据”")

    def load_record(self, record_id: int):
        self.set_current_record({"id": record_id})

    def _on_load_clicked(self):
        self._set_status("处理中... 正在加载数据")
        self.load_btn.setEnabled(False)

        source = self.data_selector.currentText().strip()
        self.load_thread = QThread(self)
        self.load_worker = _LoadSignalWorker(self.signal_service, source)
        self.load_worker.moveToThread(self.load_thread)

        self.load_thread.started.connect(self.load_worker.run)
        self.load_worker.finished.connect(self._on_load_success)
        self.load_worker.failed.connect(self._on_load_failed)
        self.load_worker.finished.connect(self.load_thread.quit)
        self.load_worker.failed.connect(self.load_thread.quit)
        self.load_thread.finished.connect(self.load_worker.deleteLater)
        self.load_thread.finished.connect(self.load_thread.deleteLater)
        self.load_thread.finished.connect(lambda: setattr(self, "load_thread", None))
        self.load_thread.finished.connect(lambda: setattr(self, "load_worker", None))

        self.load_thread.start()

    def _on_load_success(self, signal_data: SignalData):
        self.load_btn.setEnabled(True)
        self.loaded_signal_data = signal_data
        self.current_processed_x = []
        self.current_processed_y = []
        self.current_features = {}

        channel = self.channel_selector.currentText()
        if channel == "F" and "F" not in signal_data.channels:
            channel = "Fx"

        values = signal_data.channels[channel]
        x_data = list(range(len(values)))
        self.raw_plot_widget.set_signal_data(x_data, values, "#4C8DFF")
        self.processed_plot_widget.clear()
        self.feature_table.setRowCount(0)

        self.end_index_spin.setValue(min(len(values), 2000))

        source_text = "MOCK/SAMPLE 数据" if signal_data.source == "mock" else signal_data.source
        if self.current_record:
            self.record_info_label.setText(f"当前数据记录ID：{self.current_record.get('id', '--')}")
        else:
            self.record_info_label.setText(f"当前数据记录：{self.data_selector.currentText() or '默认'}")
        self.filename_info_label.setText(f"文件名：{source_text}")
        self.sample_info_label.setText(f"采样率：{signal_data.sample_rate:.1f} Hz")
        self._set_status("已加载数据（若显示 MOCK/SAMPLE 即为示例数据）")

    def _on_load_failed(self, message: str):
        self.load_btn.setEnabled(True)
        self._set_status("数据加载失败")
        logger.error("加载数据失败: %s", message)
        InfoBar.error("加载失败", message, parent=self)

    def _on_apply_clicked(self):
        if self.loaded_signal_data is None:
            InfoBar.warning("提示", "请先加载数据", parent=self)
            return

        params = {
            "channel": self.channel_selector.currentText(),
            "remove_dc": self.remove_dc_checkbox.isChecked(),
            "smooth_window": self.smooth_window_spin.value(),
            "start_index": self.start_index_spin.value(),
            "end_index": self.end_index_spin.value(),
            "compute_resultant": self.resultant_checkbox.isChecked(),
        }

        self._set_status("处理中... 正在应用基础处理")
        self.apply_btn.setEnabled(False)

        self.process_thread = QThread(self)
        self.process_worker = _ProcessSignalWorker(self.signal_service, self.loaded_signal_data, params)
        self.process_worker.moveToThread(self.process_thread)

        self.process_thread.started.connect(self.process_worker.run)
        self.process_worker.finished.connect(self._on_process_success)
        self.process_worker.failed.connect(self._on_process_failed)
        self.process_worker.finished.connect(self.process_thread.quit)
        self.process_worker.failed.connect(self.process_thread.quit)
        self.process_thread.finished.connect(self.process_worker.deleteLater)
        self.process_thread.finished.connect(self.process_thread.deleteLater)
        self.process_thread.finished.connect(lambda: setattr(self, "process_thread", None))
        self.process_thread.finished.connect(lambda: setattr(self, "process_worker", None))

        self.process_thread.start()

    def _on_process_success(self, x_data, y_data):
        self.apply_btn.setEnabled(True)
        self.current_processed_x = list(x_data)
        self.current_processed_y = list(y_data)
        self.processed_plot_widget.set_signal_data(x_data, y_data, "#00BFA5")

        self.current_features = self.signal_service.extract_features(
            self.current_processed_y,
            sampling_rate=self.loaded_signal_data.sample_rate if self.loaded_signal_data else None,
        )
        self._update_feature_table(self.current_features)

        self.export_signal_btn.setEnabled(True)
        self.export_features_btn.setEnabled(True)
        self.send_to_recommend_btn.setEnabled(True)
        self._set_status("处理完成，特征已更新")

    def _on_process_failed(self, message: str):
        self.apply_btn.setEnabled(True)
        self._set_status("处理失败")
        logger.error("信号处理失败: %s", message)
        InfoBar.error("处理失败", message, parent=self)

    def _on_reset_clicked(self):
        self.remove_dc_checkbox.setChecked(True)
        self.smooth_window_spin.setValue(5)
        self.resultant_checkbox.setChecked(False)
        self.start_index_spin.setValue(0)

        if self.loaded_signal_data is not None:
            channel = self.channel_selector.currentText()
            if channel not in self.loaded_signal_data.channels:
                channel = "Fx"
            values = self.loaded_signal_data.channels[channel]
            self.end_index_spin.setValue(min(len(values), 2000))
            self.raw_plot_widget.set_signal_data(range(len(values)), values, "#4C8DFF")
        else:
            self.end_index_spin.setValue(2000)
            self.raw_plot_widget.clear()

        self.processed_plot_widget.clear()
        self.feature_table.setRowCount(0)
        self.current_processed_x = []
        self.current_processed_y = []
        self.current_features = {}
        self.export_signal_btn.setEnabled(False)
        self.export_features_btn.setEnabled(False)
        self.send_to_recommend_btn.setEnabled(False)
        self._set_status("已重置参数")

    def _on_export_signal(self):
        if not self.current_processed_y:
            InfoBar.warning("提示", "请先完成处理再导出", parent=self)
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "导出处理信号", "processed_signal.csv", "CSV Files (*.csv)")
        if not save_path:
            return

        try:
            channel = self.channel_selector.currentText()
            self.signal_service.export_signal_to_csv(save_path, self.current_processed_x, self.current_processed_y, channel)
            InfoBar.success("导出成功", f"处理信号已导出：{save_path}", parent=self)
        except Exception as exc:
            logger.error("导出处理信号失败: %s", exc)
            InfoBar.error("导出失败", str(exc), parent=self)

    def _on_export_features(self):
        if not self.current_features:
            InfoBar.warning("提示", "暂无可导出的特征", parent=self)
            return

        save_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出特征",
            "signal_features.csv",
            "CSV Files (*.csv);;JSON Files (*.json)",
        )
        if not save_path:
            return

        try:
            if selected_filter.startswith("JSON") or save_path.lower().endswith(".json"):
                if not save_path.lower().endswith(".json"):
                    save_path += ".json"
                self.signal_service.export_features_to_json(save_path, self.current_features)
            else:
                if not save_path.lower().endswith(".csv"):
                    save_path += ".csv"
                self.signal_service.export_features_to_csv(save_path, self.current_features)

            InfoBar.success("导出成功", f"特征已导出：{save_path}", parent=self)
        except Exception as exc:
            logger.error("导出特征失败: %s", exc)
            InfoBar.error("导出失败", str(exc), parent=self)

    def _on_send_to_recommend(self):
        if not self.current_features:
            InfoBar.warning("提示", "请先完成处理并生成特征", parent=self)
            return

        payload = {
            "record_id": self.current_record.get("id") if self.current_record else None,
            "channel": self.channel_selector.currentText(),
            "features": self.current_features,
        }
        logger.info("TODO: 发送到推荐模块 payload=%s", payload)
        InfoBar.info("预留接口", "已生成结构化特征对象（见日志，后续对接推荐模块）", parent=self)

    def _update_feature_table(self, features: Dict[str, float]):
        ordered_feature_labels = [
            ("max", "最大值"),
            ("min", "最小值"),
            ("mean", "均值"),
            ("rms", "RMS"),
            ("peak_to_peak", "峰峰值"),
            ("std", "标准差"),
            ("energy", "能量"),
            ("dominant_frequency", "主频(Hz)"),
        ]

        available_items = [(key, label) for key, label in ordered_feature_labels if key in features]
        self.feature_table.setRowCount(len(available_items))

        for row, (key, label) in enumerate(available_items):
            value = features[key]
            self.feature_table.setItem(row, 0, QTableWidgetItem(label))
            self.feature_table.setItem(row, 1, QTableWidgetItem(f"{value:.6f}"))

    def _set_status(self, text: str):
        self.processing_status_label.setText(f"状态：{text}")

    def on_activated(self):
        logger.info("SensorProcessingInterface activated")

    def on_deactivated(self):
        logger.info("SensorProcessingInterface deactivated")

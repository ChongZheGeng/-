# coding:utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from qfluentwidgets import MessageBoxBase, SubtitleLabel, BodyLabel, LineEdit, ComboBox, PrimaryPushButton, InfoBar

from ...api.api_client import api_client
from ...api.async_api import AsyncApiHelper


class RecommendDialog(MessageBoxBase):
    """加工任务中的智能推荐弹窗"""

    def __init__(self, parent=None, default_n=None, default_fz=None):
        super().__init__(parent)
        self.worker = None
        self.result = None

        title = SubtitleLabel("智能推荐参数", self)
        self.viewLayout.addWidget(title)

        content = QVBoxLayout()
        content.setSpacing(10)

        self.n_edit = LineEdit(self)
        self.n_edit.setPlaceholderText("转速 n")
        if default_n is not None:
            self.n_edit.setText(str(default_n))

        self.fz_edit = LineEdit(self)
        self.fz_edit.setPlaceholderText("每齿进给 fz")
        if default_fz is not None:
            self.fz_edit.setText(str(default_fz))

        self.objective_combo = ComboBox(self)
        self.objective_combo.addItems(["A_damage", "F_damage"])

        self.model_combo = ComboBox(self)
        self.model_combo.addItems(["quad", "gp"])

        self.status_label = BodyLabel("点击获取推荐")
        self.result_label = BodyLabel("-")
        self.result_label.setWordWrap(True)

        content.addWidget(BodyLabel("转速 n"))
        content.addWidget(self.n_edit)
        content.addWidget(BodyLabel("每齿进给 fz"))
        content.addWidget(self.fz_edit)
        content.addWidget(BodyLabel("优化目标"))
        content.addWidget(self.objective_combo)
        content.addWidget(BodyLabel("模型类型"))
        content.addWidget(self.model_combo)

        btn_row = QHBoxLayout()
        self.fetch_btn = PrimaryPushButton("获取推荐")
        self.fetch_btn.clicked.connect(self.fetch_recommendation)
        btn_row.addWidget(self.fetch_btn)
        btn_row.addStretch(1)
        content.addLayout(btn_row)

        content.addWidget(self.status_label)
        content.addWidget(self.result_label)

        self.viewLayout.addLayout(content)

        self.yesButton.setText("一键应用")
        self.cancelButton.setText("取消")
        self.yesButton.setEnabled(False)

    def _set_loading(self, loading, text=""):
        self.fetch_btn.setEnabled(not loading)
        self.status_label.setText(text or ("请求中..." if loading else ""))

    def fetch_recommendation(self):
        try:
            n = float(self.n_edit.text().strip())
            fz = float(self.fz_edit.text().strip())
        except ValueError:
            InfoBar.warning("输入错误", "请输入合法的 n 和 fz", parent=self)
            return

        payload = {
            "n": n,
            "fz": fz,
            "objective": self.objective_combo.currentText(),
            "model_type": self.model_combo.currentText(),
        }

        self._set_loading(True, "正在请求推荐...")
        self.worker = AsyncApiHelper.call_async(
            api_client.recommend_parameters,
            self.on_success,
            self.on_error,
            payload,
            timeout=10,
        )

    def on_success(self, response):
        self._set_loading(False, "推荐完成")
        if not response:
            self.result_label.setText("未返回有效结果")
            return

        best = response.get("best") or response
        self.result = {
            "n": best.get("n", response.get("n")),
            "fz": best.get("fz", response.get("fz")),
        }
        self.result_label.setText(f"推荐结果: n={self.result['n']}, fz={self.result['fz']}")
        self.yesButton.setEnabled(self.result.get("n") is not None and self.result.get("fz") is not None)

    def on_error(self, error):
        self._set_loading(False, "请求失败")
        self.result_label.setText(f"请求失败: {error}")
        InfoBar.error("请求失败", "后端不可用或推荐接口异常", parent=self)

    def get_recommended_values(self):
        return self.result

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
        super().closeEvent(event)

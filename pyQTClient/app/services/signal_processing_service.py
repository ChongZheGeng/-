# coding:utf-8
import csv
import json
import logging
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SignalData:
    sample_rate: float
    channels: Dict[str, List[float]]
    source: str


class SignalProcessingService:
    """基础信号加载与处理服务（第二阶段）。"""

    DEFAULT_SAMPLE_RATE = 1000.0

    def load_signal(self, source: Optional[str] = None) -> SignalData:
        """加载信号。当前默认返回 mock/sample 数据；支持简单 CSV 读取。"""
        if source and Path(source).exists():
            try:
                loaded = self._load_from_csv(source)
                logger.info("SignalProcessingService: 已加载真实 CSV 数据 source=%s", source)
                return loaded
            except Exception as exc:
                logger.warning("SignalProcessingService: 真实数据读取失败，将回退 mock 数据。source=%s, error=%s", source, exc)

        logger.info("SignalProcessingService: 使用 MOCK/SAMPLE 数据（阶段二默认实现）")
        return self._create_mock_signal()

    def preprocess_signal(
        self,
        signal_data: SignalData,
        channel: str = "Fx",
        remove_dc: bool = True,
        smooth_window: int = 1,
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
        compute_resultant: bool = False,
    ):
        channels = dict(signal_data.channels)

        if compute_resultant and all(key in channels for key in ["Fx", "Fy", "Fz"]):
            channels["F"] = [
                math.sqrt(fx * fx + fy * fy + fz * fz)
                for fx, fy, fz in zip(channels["Fx"], channels["Fy"], channels["Fz"])
            ]

        if channel not in channels:
            raise ValueError(f"通道 {channel} 不存在")

        values = channels[channel]

        start = 0 if start_index is None else max(int(start_index), 0)
        end = len(values) if end_index is None else min(int(end_index), len(values))
        if end <= start:
            raise ValueError("窗口范围无效：end 必须大于 start")

        windowed = [float(v) for v in values[start:end]]

        if remove_dc and windowed:
            avg = mean(windowed)
            windowed = [v - avg for v in windowed]

        smooth_window = max(int(smooth_window), 1)
        if smooth_window > 1:
            windowed = self._moving_average(windowed, smooth_window)

        x_axis = [float(i) for i in range(start, start + len(windowed))]
        return x_axis, windowed

    def extract_features(self, signal: List[float], sampling_rate: Optional[float] = None) -> Dict[str, float]:
        """提取基础时域特征，并在可行时补充主频。"""
        if not signal:
            return {
                "max": 0.0,
                "min": 0.0,
                "mean": 0.0,
                "rms": 0.0,
                "peak_to_peak": 0.0,
                "std": 0.0,
                "energy": 0.0,
            }

        max_val = max(signal)
        min_val = min(signal)
        avg = mean(signal)
        energy = sum(v * v for v in signal)
        rms = math.sqrt(energy / len(signal))
        variance = sum((v - avg) * (v - avg) for v in signal) / len(signal)
        std_val = math.sqrt(max(variance, 0.0))

        features = {
            "max": max_val,
            "min": min_val,
            "mean": avg,
            "rms": rms,
            "peak_to_peak": max_val - min_val,
            "std": std_val,
            "energy": energy,
        }

        dominant_frequency = self._estimate_dominant_frequency(signal, sampling_rate)
        if dominant_frequency is not None:
            features["dominant_frequency"] = dominant_frequency

        return features

    def export_signal_to_csv(self, file_path: str, x_data: List[float], y_data: List[float], channel: str) -> None:
        """导出处理后的信号到 CSV。"""
        with open(file_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["index", channel])
            for x, y in zip(x_data, y_data):
                writer.writerow([x, y])

    def export_features_to_csv(self, file_path: str, features: Dict[str, float]) -> None:
        """导出特征到 CSV。"""
        with open(file_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["feature", "value"])
            for key, value in features.items():
                writer.writerow([key, value])

    def export_features_to_json(self, file_path: str, features: Dict[str, float]) -> None:
        """导出特征到 JSON。"""
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(features, file, ensure_ascii=False, indent=2)

    def _create_mock_signal(self) -> SignalData:
        sample_count = 10000
        sample_rate = self.DEFAULT_SAMPLE_RATE

        fx = []
        fy = []
        fz = []
        for i in range(sample_count):
            t = i / sample_rate
            fx.append(2.0 * math.sin(2 * math.pi * 2.2 * t) + 0.6 * random.gauss(0, 1))
            fy.append(1.2 * math.sin(2 * math.pi * 3.8 * t + 0.8) + 0.4 * random.gauss(0, 1))
            fz.append(1.6 * math.sin(2 * math.pi * 1.2 * t + 0.2) + 0.5 * random.gauss(0, 1))

        return SignalData(
            sample_rate=sample_rate,
            channels={"Fx": fx, "Fy": fy, "Fz": fz},
            source="mock",
        )

    def _load_from_csv(self, source: str) -> SignalData:
        channels = {"Fx": [], "Fy": [], "Fz": [], "F": []}

        with open(source, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                for key in channels:
                    if key in row and row[key] not in (None, ""):
                        channels[key].append(float(row[key]))

        channels = {key: value for key, value in channels.items() if value}
        if not channels:
            raise ValueError("CSV 中未找到 Fx/Fy/Fz/F 字段")

        return SignalData(
            sample_rate=self.DEFAULT_SAMPLE_RATE,
            channels=channels,
            source=source,
        )

    @staticmethod
    def _moving_average(data: List[float], window: int) -> List[float]:
        half = window // 2
        smoothed = []
        for idx in range(len(data)):
            left = max(idx - half, 0)
            right = min(idx + half + 1, len(data))
            smoothed.append(mean(data[left:right]))
        return smoothed

    @staticmethod
    def _estimate_dominant_frequency(signal: List[float], sampling_rate: Optional[float]) -> Optional[float]:
        """不依赖 numpy 的简易主频估计，避免引入额外依赖。"""
        if sampling_rate is None or sampling_rate <= 0 or len(signal) < 8:
            return None

        sample_count = len(signal)
        half = sample_count // 2
        if half <= 1:
            return None

        best_k = 1
        best_amp = -1.0
        for k in range(1, half):
            real = 0.0
            imag = 0.0
            for n, value in enumerate(signal):
                angle = 2 * math.pi * k * n / sample_count
                real += value * math.cos(angle)
                imag -= value * math.sin(angle)
            amp = real * real + imag * imag
            if amp > best_amp:
                best_amp = amp
                best_k = k

        return best_k * sampling_rate / sample_count

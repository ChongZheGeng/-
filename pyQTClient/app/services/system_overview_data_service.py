# coding:utf-8
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from ..api.api_client import api_client
from ..view.components.parameter_recommend_overview_component import MOCK_RECOMMENDATION_RECORDS


@dataclass
class OverviewFilterSpec:
    key: str
    label: str


class SystemOverviewDataService:
    """系统概览统一数据服务层。

    - 支持真实 API + mock 双入口
    - 对任务、推荐、传感器数据进行统一聚合
    """

    def __init__(self):
        self._mock_payload = self._build_mock_payload()

    def get_dashboard_payload(self, use_mock: bool = False) -> Dict[str, Any]:
        if use_mock:
            return self._build_mock_payload()

        try:
            tasks_resp = api_client.get_processing_tasks() or {}
            sensors_resp = api_client.get_sensor_data() or {}

            tasks = tasks_resp.get("results", []) if isinstance(tasks_resp, dict) else []
            sensors = sensors_resp.get("results", []) if isinstance(sensors_resp, dict) else []
            recommendations = self._load_recommendation_records()

            pending_recommend_tasks = [t for t in tasks if self.is_pending_recommend_task(t)]
            pending_analysis_records = [s for s in sensors if self.is_pending_analysis_record(s)]

            status_counts: Dict[str, int] = {}
            for task in tasks:
                status = str(task.get("status") or "planned")
                status_counts[status] = status_counts.get(status, 0) + 1

            payload = {
                "users": self._safe_count(api_client.get_users()),
                "tasks": len(tasks),
                "sensor": len(sensors),
                "pending_recommend": len(pending_recommend_tasks),
                "pending_analysis": len(pending_analysis_records),
                "alerts": self._estimate_alerts(sensors),
                "recommend_today": self._count_today_recommendations(recommendations),
                "adoption": self._calc_adoption_rate(recommendations),
                "task_status_counts": status_counts,
                "sensor_overview": self._build_sensor_overview(sensors, pending_analysis_records),
                "recommend_overview": self._build_recommend_overview(recommendations),
                "recommendation_records": recommendations,
                "analysis_records": self._build_recent_analysis_records(sensors),
                "activities": self._build_recent_activities(tasks, sensors, recommendations),
                "filters": {
                    "pending_recommend": {"route": "processing_task", "spec": OverviewFilterSpec("pending_recommend", "待推荐任务")},
                    "pending_analysis": {"route": "sensor_data", "spec": OverviewFilterSpec("pending_analysis", "待分析数据")},
                },
            }
            return payload
        except Exception:
            return self._build_mock_payload()

    def _safe_count(self, response: Any) -> int:
        if isinstance(response, dict):
            if "count" in response:
                return int(response.get("count") or 0)
            if "results" in response and isinstance(response["results"], list):
                return len(response["results"])
        return 0

    @staticmethod
    def is_pending_recommend_task(task: Dict[str, Any]) -> bool:
        status = str(task.get("status") or "")
        recommendable = bool(task.get("is_recommendable", status in {"planned", "in_progress"}))
        if not recommendable:
            return False

        if bool(task.get("recommended", False)):
            return False

        recommendation_status = str(task.get("recommendation_status") or "")
        if recommendation_status in {"recommended", "adopted", "completed"}:
            return False

        if task.get("recommended_at"):
            return False

        return True

    @staticmethod
    def is_pending_analysis_record(record: Dict[str, Any]) -> bool:
        if bool(record.get("is_analyzed", False)):
            return False
        analysis_status = str(record.get("analysis_status") or "").lower()
        if analysis_status in {"done", "completed", "success", "finished"}:
            return False
        return True

    def _load_recommendation_records(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in MOCK_RECOMMENDATION_RECORDS]

    def _build_recent_analysis_records(self, sensors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        records = []
        for item in sensors:
            records.append({
                "sensor_id": item.get("sensor_id", "-"),
                "task_code": (item.get("task_info") or {}).get("task_code", "-"),
                "file_url": item.get("file_url", "-"),
                "upload_time": item.get("upload_time", ""),
                "analysis_status": item.get("analysis_status", "pending"),
            })
        records.sort(key=lambda x: str(x.get("upload_time", "")), reverse=True)
        return records[:10]

    def _build_recent_activities(self, tasks, sensors, recommendations):
        def _task(item):
            code = item.get("task_code", "N/A")
            return {
                "title": f"任务 {code} 状态更新",
                "description": f"当前状态：{item.get('status_display', item.get('status', '未知'))}",
                "time": str(item.get("updated_at") or item.get("processing_time") or "")[:16],
            }

        task_activities = sorted(tasks, key=lambda x: str(x.get("updated_at") or x.get("processing_time") or ""), reverse=True)
        task_activities = [_task(t) for t in task_activities[:5]]

        analysis_activities = []
        for sensor in sorted(sensors, key=lambda x: str(x.get("upload_time", "")), reverse=True)[:5]:
            sid = sensor.get("sensor_id", "-")
            analysis_activities.append({
                "title": f"传感器 {sid} 数据入库",
                "description": f"分析状态：{sensor.get('analysis_status', 'pending')}",
                "time": str(sensor.get("upload_time", ""))[:16],
            })

        recommendation_activities = []
        for rec in recommendations[:5]:
            recommendation_activities.append({
                "title": f"任务 {rec.get('task_code', '-') } 生成推荐",
                "description": f"置信度 {float(rec.get('confidence', 0) or 0) * 100:.1f}%",
                "time": str(rec.get("recommended_at", ""))[:16],
            })

        return {
            "task": task_activities,
            "analysis": analysis_activities,
            "recommendation": recommendation_activities,
        }

    def _estimate_alerts(self, sensors):
        return sum(1 for item in sensors if str(item.get("analysis_status", "")).lower() in {"error", "abnormal", "alert"})

    def _count_today_recommendations(self, records):
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(1 for r in records if str(r.get("recommended_at", "")).startswith(today))

    def _calc_adoption_rate(self, records):
        if not records:
            return 0.0
        adopted = sum(1 for r in records if r.get("adopted"))
        return round(adopted * 100 / len(records), 1)

    def _build_sensor_overview(self, sensors, pending):
        total = max(1, len(sensors))
        done = len(sensors) - len(pending)
        coverage = int(done * 100 / total)
        return {
            "coverage": {"value": f"{coverage}%", "ratio": coverage},
            "quality": {"value": "87%", "ratio": 87},
            "alerts": {"value": f"{max(0, 100 - int(len(pending)*100/total))}%", "ratio": max(0, 100 - int(len(pending)*100/total))},
        }

    def _build_recommend_overview(self, records):
        if not records:
            return {
                "confidence": {"value": "0", "ratio": 0},
                "hit_rate": {"value": "0%", "ratio": 0},
                "closed_loop": {"value": "0%", "ratio": 0},
            }
        avg_conf = sum(float(r.get("confidence", 0) or 0) for r in records) / len(records)
        adoption = self._calc_adoption_rate(records)
        return {
            "confidence": {"value": f"{avg_conf:.2f}", "ratio": int(avg_conf * 100)},
            "hit_rate": {"value": f"{adoption:.0f}%", "ratio": int(adoption)},
            "closed_loop": {"value": f"{max(50, int(adoption * 0.9))}%", "ratio": max(50, int(adoption * 0.9))},
        }

    def _build_mock_payload(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        payload = {
            "users": 12,
            "tasks": 28,
            "sensor": 120,
            "pending_recommend": 9,
            "pending_analysis": 24,
            "alerts": 6,
            "recommend_today": 13,
            "adoption": 78.6,
            "task_status_counts": {"planned": 8, "in_progress": 7, "completed": 11, "paused": 2},
            "sensor_overview": {
                "coverage": {"value": "92%", "ratio": 92},
                "quality": {"value": "87%", "ratio": 87},
                "alerts": {"value": "81%", "ratio": 81},
            },
            "recommend_overview": {
                "confidence": {"value": "0.86", "ratio": 86},
                "hit_rate": {"value": "74%", "ratio": 74},
                "closed_loop": {"value": "68%", "ratio": 68},
            },
            "recommendation_records": [dict(item) for item in MOCK_RECOMMENDATION_RECORDS],
            "analysis_records": [
                {
                    "sensor_id": "S-22",
                    "task_code": "TK-240301-01",
                    "file_url": "demo_signal_a.csv",
                    "upload_time": now,
                    "analysis_status": "pending",
                }
            ],
            "activities": {
                "task": [{"title": "任务 TK-108 切换进行中", "description": "现场班组已确认并开始执行。", "time": now}],
                "analysis": [{"title": "传感器 S-22 完成清洗", "description": "有效信号占比提升至 87%。", "time": now}],
                "recommendation": [{"title": "推荐方案 R-013 被采纳", "description": "已进入闭环验证阶段。", "time": now}],
            },
            "filters": {
                "pending_recommend": {"route": "processing_task", "spec": OverviewFilterSpec("pending_recommend", "待推荐任务")},
                "pending_analysis": {"route": "sensor_data", "spec": OverviewFilterSpec("pending_analysis", "待分析数据")},
            },
        }
        return payload


system_overview_data_service = SystemOverviewDataService()

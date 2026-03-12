# coding:utf-8
from __future__ import annotations

from typing import Any, Dict, List

from .system_overview_data_service import system_overview_data_service


class SystemOverviewLinkageManager:
    """首页与任务/推荐/传感器模块联动管理层。"""

    def __init__(self, data_service=system_overview_data_service):
        self.data_service = data_service

    def load_dashboard_payload(self, use_mock: bool = False) -> Dict[str, Any]:
        return self.data_service.get_dashboard_payload(use_mock=use_mock)

    def filter_pending_recommend_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [task for task in tasks if self.data_service.is_pending_recommend_task(task)]

    def filter_pending_analysis_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [record for record in records if self.data_service.is_pending_analysis_record(record)]


system_overview_linkage_manager = SystemOverviewLinkageManager()

import logging

from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """将数据库连接异常转换为统一 JSON，避免前端收到 traceback。"""
    if isinstance(exc, DatabaseError):
        view_name = context.get("view").__class__.__name__ if context.get("view") else "unknown"
        logger.exception("[api] database_error view=%s", view_name)
        return Response(
            {"error": "数据库连接异常，请稍后重试"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return exception_handler(exc, context)

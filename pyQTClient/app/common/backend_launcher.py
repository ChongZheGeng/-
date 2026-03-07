# coding:utf-8
import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

HEALTH_URL = "http://127.0.0.1:8000/api/health/"


def find_repo_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """从当前文件向上查找包含 DjangoService/manage.py 的仓库根目录。"""
    search_start = Path(start_path) if start_path else Path(__file__).resolve()
    for parent in [search_start] + list(search_start.parents):
        if parent.is_file():
            parent = parent.parent

        manage_py = parent / "DjangoService" / "manage.py"
        if manage_py.exists():
            logger.info("检测到 Django manage.py: %s", manage_py)
            return parent

    logger.warning("未找到 DjangoService/manage.py，起始路径: %s", search_start)
    return None


def quick_health_check(timeout: Tuple[float, float] = (1, 2.5)) -> Tuple[bool, str]:
    """执行一次快速健康检查，尽量减少重试等待。"""
    try:
        response = requests.get(HEALTH_URL, timeout=timeout)
        response.raise_for_status()
        return True, "OK"
    except requests.exceptions.RequestException as e:
        return False, str(e)


def _build_windows_command(repo_root: Path, python_exe: str) -> str:
    django_dir = repo_root / "DjangoService"
    return (
        f"cd '{django_dir}'; "
        f"& '{python_exe}' manage.py runserver 127.0.0.1:8000"
    )


def build_manual_command(repo_root: Optional[Path] = None, python_exe: Optional[str] = None) -> str:
    """生成手动启动 Django 的命令。"""
    root = repo_root or find_repo_root() or Path.cwd()
    py = python_exe or sys.executable
    django_dir = root / "DjangoService"

    if os.name == "nt":
        return f"cd /d {django_dir} && \"{py}\" manage.py runserver 127.0.0.1:8000"

    return f"cd '{django_dir}' && '{py}' manage.py runserver 127.0.0.1:8000"


def start_django_server(repo_root: Path, python_exe: Optional[str] = None) -> subprocess.Popen:
    """在新窗口中非阻塞启动 Django 开发服务器。"""
    py = python_exe or sys.executable

    if os.name == "nt":
        powershell_cmd = _build_windows_command(repo_root, py)
        cmd = [
            "powershell",
            "-NoExit",
            "-Command",
            powershell_cmd,
        ]
        logger.info("准备通过 PowerShell 新窗口启动后端: %s", powershell_cmd)
        process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        django_dir = repo_root / "DjangoService"
        cmd = [py, "manage.py", "runserver", "127.0.0.1:8000"]
        logger.info("当前系统非 Windows，使用后台进程启动后端: cwd=%s cmd=%s", django_dir, cmd)
        process = subprocess.Popen(cmd, cwd=str(django_dir))

    logger.info("后端启动进程已拉起，pid=%s", process.pid)
    return process


def wait_for_health(timeout_seconds: float = 25.0, interval_seconds: float = 0.5) -> Tuple[bool, float, str]:
    """轮询等待健康检查通过。"""
    start = time.monotonic()
    last_error = ""

    while time.monotonic() - start <= timeout_seconds:
        ok, message = quick_health_check(timeout=(1, 2.5))
        if ok:
            elapsed = time.monotonic() - start
            logger.info("后端健康检查通过，耗时 %.2fs", elapsed)
            return True, elapsed, "OK"

        last_error = message
        time.sleep(interval_seconds)

    elapsed = time.monotonic() - start
    logger.warning("等待后端就绪超时，耗时 %.2fs, 最后错误: %s", elapsed, last_error)
    return False, elapsed, last_error

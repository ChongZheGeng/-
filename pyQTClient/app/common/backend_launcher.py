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


def quick_health_check(timeout: Tuple[float, float] = (3, 5)) -> Tuple[bool, str]:
    """执行一次快速健康检查，尽量减少误判。"""
    try:
        logger.info("后台健康检查请求: url=%s timeout=%s", HEALTH_URL, timeout)
        response = requests.get(HEALTH_URL, timeout=timeout)
        logger.info("后台健康检查响应: status_code=%s", response.status_code)
        response.raise_for_status()
        return True, "OK"
    except requests.exceptions.RequestException as e:
        logger.warning("后台健康检查失败: type=%s detail=%s", type(e).__name__, e)
        return False, str(e)



def _resolve_paths(repo_root: Optional[Path] = None, python_exe: Optional[str] = None) -> Tuple[Path, str]:
    """解析 DjangoService 与 Python 可执行文件路径。"""
    root = repo_root or find_repo_root() or Path.cwd()
    py = python_exe or sys.executable
    django_dir = root / "DjangoService"
    return django_dir, py


def build_powershell_runserver_command(repo_root: Optional[Path] = None, python_exe: Optional[str] = None) -> str:
    """生成 PowerShell 手动启动 Django 的纯命令字符串。"""
    django_dir, py = _resolve_paths(repo_root, python_exe)
    return f'Set-Location "{django_dir}"\n& "{py}" manage.py runserver 127.0.0.1:8000'


def build_cmd_runserver_command(repo_root: Optional[Path] = None, python_exe: Optional[str] = None) -> str:
    """生成 CMD 手动启动 Django 的纯命令字符串。"""
    django_dir, py = _resolve_paths(repo_root, python_exe)
    return f'cd /d "{django_dir}"\n"{py}" manage.py runserver 127.0.0.1:8000'


def build_manual_command(repo_root: Optional[Path] = None, python_exe: Optional[str] = None) -> str:
    """生成手动启动 Django 的命令（Windows 默认 PowerShell）。"""
    if os.name == "nt":
        return build_powershell_runserver_command(repo_root, python_exe)

    django_dir, py = _resolve_paths(repo_root, python_exe)
    return f"cd '{django_dir}'\n'{py}' manage.py runserver 127.0.0.1:8000"


def build_powershell_manual_command(repo_root: Optional[Path] = None, python_exe: Optional[str] = None) -> str:
    """兼容旧调用：生成 PowerShell 启动命令。"""
    return build_powershell_runserver_command(repo_root, python_exe)


def build_cmd_manual_command(repo_root: Optional[Path] = None, python_exe: Optional[str] = None) -> str:
    """兼容旧调用：生成 CMD 启动命令。"""
    return build_cmd_runserver_command(repo_root, python_exe)


def start_django_server(repo_root: Path, python_exe: Optional[str] = None) -> subprocess.Popen:
    """在新窗口中非阻塞启动 Django 开发服务器。"""
    py = python_exe or sys.executable
    django_dir = repo_root / "DjangoService"
    cmd = [py, "manage.py", "runserver", "127.0.0.1:8000"]

    logger.info("准备启动后端: cwd=%s python=%s cmd=%s", django_dir, py, cmd)
    if os.name == "nt":
        process = subprocess.Popen(
            cmd,
            cwd=str(django_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        process = subprocess.Popen(cmd, cwd=str(django_dir))

    logger.info("后端启动进程已拉起，pid=%s", process.pid)
    return process


def wait_for_health(timeout_seconds: float = 25.0, interval_seconds: float = 0.5) -> Tuple[bool, float, str]:
    """轮询等待健康检查通过。"""
    start = time.monotonic()
    last_error = ""

    while time.monotonic() - start <= timeout_seconds:
        ok, message = quick_health_check(timeout=(3, 5))
        if ok:
            elapsed = time.monotonic() - start
            logger.info("后端健康检查通过，耗时 %.2fs", elapsed)
            return True, elapsed, "OK"

        last_error = message
        time.sleep(interval_seconds)

    elapsed = time.monotonic() - start
    logger.warning("等待后端就绪超时，耗时 %.2fs, 最后错误: %s", elapsed, last_error)
    return False, elapsed, last_error

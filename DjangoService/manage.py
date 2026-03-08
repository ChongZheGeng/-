#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sqlite3
import sys
from pathlib import Path


def _warn_uninitialized_sqlite_for_runserver(argv):
    if not argv or argv[0] != "runserver":
        return

    if os.getenv("USE_MYSQL", "0") == "1":
        return

    sqlite_file = Path(__file__).resolve().parent / "db.sqlite3"
    if not sqlite_file.exists():
        print("[startup] SQLite 开发数据库未初始化，请先运行 dev_init.ps1 或 python manage.py init_dev_data")
        return

    try:
        with sqlite3.connect(str(sqlite_file)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user'")
            row = cursor.fetchone()
            if row is None:
                print("[startup] SQLite 开发数据库未初始化，请先运行 dev_init.ps1 或 python manage.py init_dev_data")
    except sqlite3.Error as exc:
        print(f"[startup] SQLite 初始化检查失败: {exc}")


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoService.settings")
    _warn_uninitialized_sqlite_for_runserver(sys.argv[1:])
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

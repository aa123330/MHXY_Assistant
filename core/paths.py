"""项目路径工具 — 兼容开发模式和 PyInstaller 打包。

PyInstaller 打包后的路径规则:
  - sys._MEIPASS  = 临时解压目录（只读，exe 内嵌的文件都在这里）
  - sys.executable = exe 所在目录（可写，user data 放这里）
"""

import sys
import os
from pathlib import Path


def get_source_dir() -> Path:
    """返回源码/打包资源目录（只读）。

    开发模式: 项目根目录
    打包模式: PyInstaller 临时解压目录
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def get_user_dir() -> Path:
    """返回用户数据目录（可写）。

    开发模式: 项目根目录（和源码在一起）
    打包模式: exe 所在目录（数据存在 exe 旁边）
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def ensure_dirs(*subdirs: str) -> None:
    """确保用户数据子目录存在（自动创建）。"""
    base = get_user_dir()
    for sub in subdirs:
        (base / sub).mkdir(parents=True, exist_ok=True)


# 快捷别名（兼容旧代码）
PROJECT_DIR = get_source_dir()

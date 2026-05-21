"""窗口管理：查找、激活、移动游戏窗口。"""

import re
from pathlib import Path
from typing import Optional

try:
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError as e:
    raise ImportError(
        "pywin32 未安装，窗口管理模块不可用。\n"
        "请运行: pip install pywin32"
    ) from e


def find_window(title_substr: str) -> Optional[int]:
    """按标题部分匹配查找窗口句柄，返回第一个匹配的。"""
    result = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if title_substr in text:
                result.append(hwnd)

    win32gui.EnumWindows(callback, None)
    return result[0] if result else None


def find_window_regex(pattern: str) -> Optional[int]:
    """按正则匹配窗口标题查找窗口句柄。"""
    regex = re.compile(pattern)
    result = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if regex.match(text):
                result.append((hwnd, text))

    win32gui.EnumWindows(callback, None)
    if result:
        hwnd, title = result[0]
        return hwnd
    return None


def list_all_windows() -> list[tuple[int, str]]:
    """列出所有可见窗口的句柄和标题，用于调试。"""
    windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            windows.append((hwnd, win32gui.GetWindowText(hwnd)))

    win32gui.EnumWindows(callback, None)
    return windows


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    """获取窗口的屏幕坐标 (left, top, right, bottom)。"""
    return win32gui.GetWindowRect(hwnd)


def get_client_rect(hwnd: int) -> tuple[int, int, int, int]:
    """获取窗口客户区的屏幕坐标。"""
    rect = win32gui.GetClientRect(hwnd)
    left, top = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
    right = left + rect[2] - rect[0]
    bottom = top + rect[3] - rect[1]
    return left, top, right, bottom


def get_client_size(hwnd: int) -> tuple[int, int]:
    """获取客户区宽高。"""
    rect = win32gui.GetClientRect(hwnd)
    return rect[2] - rect[0], rect[3] - rect[1]


def activate_window(hwnd: int) -> None:
    """将窗口置顶并激活。"""
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)


def move_window(hwnd: int, x: int, y: int) -> bool:
    """移动窗口到指定屏幕位置，保持原有大小。"""
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w, h = right - left, bottom - top
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_SHOWWINDOW,
        )
        return True
    except Exception:
        return False


def set_window_size(hwnd: int, width: int, height: int) -> bool:
    """设置窗口大小，保持当前位置。"""
    try:
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOP, left, top, width, height, win32con.SWP_SHOWWINDOW,
        )
        return True
    except Exception:
        return False


def get_window_info(hwnd: int) -> dict:
    """获取窗口详细信息。"""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return {
        "left": left, "top": top,
        "right": right, "bottom": bottom,
        "width": right - left, "height": bottom - top,
    }


def set_topmost(hwnd: int, enable: bool = True) -> None:
    """设置窗口置顶 (借鉴 windows-manager: SetWindowPos HWND_TOPMOST)。"""
    if enable:
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                             0, 0, 0, 0,
                             win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    else:
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST,
                             0, 0, 0, 0,
                             win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def send_to_bottom(hwnd: int) -> None:
    """窗口置底 (借鉴 windows-manager: HWND_BOTTOM)。"""
    win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM,
                         0, 0, 0, 0,
                         win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def window_from_point(x: int, y: int) -> Optional[int]:
    """返回指定屏幕坐标下的窗口句柄 (借鉴 windows-manager: WindowFromPoint)。"""
    return win32gui.WindowFromPoint((x, y))


def verify_click_window(x: int, y: int, expected_hwnd: int) -> bool:
    """验证点击位置是否落在目标窗口内。

    返回 True 表示坐标处的窗口就是（或属于）目标窗口。
    """
    hwnd_at_point = window_from_point(x, y)
    if hwnd_at_point == expected_hwnd:
        return True
    # 检查是否为目标窗口的子窗口
    parent = hwnd_at_point
    while parent:
        if parent == expected_hwnd:
            return True
        parent = win32gui.GetParent(parent)
    return False


def enum_child_windows(hwnd: int) -> list[tuple[int, str, str]]:
    """枚举所有直接子窗口 (借鉴 windows-manager: EnumChildWindows)。

    返回 [(hwnd, title, class_name), ...]
    """
    result = []

    def callback(child_hwnd, _):
        title = win32gui.GetWindowText(child_hwnd)
        cls = win32gui.GetClassName(child_hwnd)
        result.append((child_hwnd, title, cls))

    win32gui.EnumChildWindows(hwnd, callback, None)
    return result


def get_window_process_name(hwnd: int) -> Optional[str]:
    """获取窗口所属进程名称 (借鉴 windows-manager: GetWindowThreadProcessId)。"""
    import win32process
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        handle = win32api.OpenProcess(0x0400 | 0x0010, False, pid)
        path = win32process.GetModuleFileNameEx(handle, 0)
        win32api.CloseHandle(handle)
        return Path(path).name
    except Exception:
        return None

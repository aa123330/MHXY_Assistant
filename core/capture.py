"""屏幕截图：支持 mss GPU 加速截图和 win32 后台窗口截图。"""

import mss
import numpy as np
from typing import Optional

try:
    import win32gui
    import win32ui
    import win32con
except ImportError as e:
    raise ImportError(
        "pywin32 未安装，截图模块不可用。\n"
        "请运行: pip install pywin32"
    ) from e


def capture_screen(region: Optional[dict] = None) -> np.ndarray:
    """截取屏幕指定区域（mss GPU 加速），返回 BGR numpy 数组。region 为 None 则截全屏。"""
    with mss.mss() as sct:
        monitor = region if region is not None else sct.monitors[1]
        img = sct.grab(monitor)
        return np.array(img)[:, :, :3]


def capture_window(hwnd: int, window_rect_getter) -> np.ndarray:
    """截取指定窗口的客户区（mss 方式，需窗口可见）。"""
    left, top, right, bottom = window_rect_getter(hwnd)
    region = {"left": left, "top": top, "width": right - left, "height": bottom - top}
    return capture_screen(region)


def capture_region(left: int, top: int, width: int, height: int) -> np.ndarray:
    """截取指定屏幕坐标区域。"""
    region = {"left": left, "top": top, "width": width, "height": height}
    return capture_screen(region)


def capture_window_bg(hwnd: int) -> Optional[np.ndarray]:
    """通过 win32 API 后台截取窗口（窗口可被遮挡/最小化）。
    返回 BGR numpy 数组，失败返回 None。
    """
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

        signed_ints = bitmap.GetBitmapBits(True)
        img = np.frombuffer(signed_ints, dtype="uint8")
        img.shape = (height, width, 4)

        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        return img[:, :, :3]  # BGRA → BGR

    except Exception:
        return None

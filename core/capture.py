"""屏幕截图：支持 mss 快速截图和 win32 后台窗口截图。"""

import ctypes
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
    if region is not None:
        region = dict(region)
        region["width"] = max(int(region.get("width", 0)), 1)
        region["height"] = max(int(region.get("height", 0)), 1)
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
    if width <= 0 or height <= 0:
        raise ValueError(f"截图区域尺寸无效: {width}x{height}")
    region = {"left": left, "top": top, "width": width, "height": height}
    return capture_screen(region)


def _bitmap_to_bgr(bitmap, width: int, height: int) -> np.ndarray:
    signed_ints = bitmap.GetBitmapBits(True)
    img = np.frombuffer(signed_ints, dtype="uint8")
    img.shape = (height, width, 4)
    return img[:, :, :3].copy()


def capture_window_client_bg(hwnd: int) -> Optional[np.ndarray]:
    """后台截取窗口客户区。

    优先使用 PrintWindow(PW_CLIENTONLY)，失败时退回 GetWindowDC + BitBlt
    截客户区偏移。部分游戏窗口会拒绝后台渲染，此时返回 None。
    """
    hwnd_dc = None
    mfc_dc = None
    save_dc = None
    bitmap = None
    try:
        client = win32gui.GetClientRect(hwnd)
        width = client[2] - client[0]
        height = client[3] - client[1]
        if width <= 0 or height <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)

        # 1=PW_CLIENTONLY, 2=PW_RENDERFULLCONTENT。后者在新版 Windows 上
        # 对部分窗口更稳；不支持时 PrintWindow 会返回 0。
        ok = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0x3)
        if ok:
            return _bitmap_to_bgr(bitmap, width, height)

        win_left, win_top, _, _ = win32gui.GetWindowRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))
        src_x = client_left - win_left
        src_y = client_top - win_top
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (src_x, src_y), win32con.SRCCOPY)
        return _bitmap_to_bgr(bitmap, width, height)
    except Exception:
        return None
    finally:
        try:
            if bitmap is not None:
                win32gui.DeleteObject(bitmap.GetHandle())
            if save_dc is not None:
                save_dc.DeleteDC()
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
            if hwnd_dc is not None:
                win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            pass


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

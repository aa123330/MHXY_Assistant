"""键鼠模拟 — 融合 7 个参考项目的最佳实践。

参考项目:
  SimuTouch:       SendInput via ctypes INPUT/MOUSEINPUT (最正规的 Windows API)
  AutoControl:     SendInput(move) + mouse_event(click) 混合、GetMessageExtraInfo
  YOLOv11-CS:      PID 控制 + dead zone + 不瞎点
  hermes-agent:    two-tier 验证、DPI 修正、closed-loop retry
  mhxy_fz:         win32api.SetCursorPos + mouse_event 直连
  mhxy-escort:     迭代减速鼠标移动、坐标验证、点击后随机移开
  lua-touchsprite: randomTap(x, y, range) 随机偏移
"""

import time
import random
import math
import ctypes
import ctypes.wintypes
from typing import Optional, Callable

from pynput.mouse import Button as _PynputButton
from pynput.keyboard import Key as _PynputKey
from pynput.keyboard import Controller as _PynputKbCtrl

_keyboard = _PynputKbCtrl()

try:
    import win32api as _w32
    import win32con as _w32c
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
    _w32 = None
    _w32c = None

# ====== SendInput 底层结构 (SimuTouch + AutoControl 方案) ======

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE       = 0x0001
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_RIGHTDOWN  = 0x0008
MOUSEEVENTF_RIGHTUP    = 0x0010
MOUSEEVENTF_ABSOLUTE   = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

KEYEVENTF_KEYUP = 0x0002

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", _ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", _ULONG_PTR),
    ]

class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]

_user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int)
_user32.SendInput.restype = ctypes.c_uint
_user32.GetSystemMetrics.argtypes = (ctypes.c_int,)
_user32.GetSystemMetrics.restype = ctypes.c_int
_user32.GetCursorPos.argtypes = (ctypes.POINTER(ctypes.wintypes.POINT),)
_user32.GetCursorPos.restype = ctypes.c_bool


def _send_input(*inputs: INPUT) -> int:
    """SendInput 封装 — Windows 最底层的合法输入 API。"""
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    return _user32.SendInput(n, ctypes.pointer(arr), ctypes.sizeof(INPUT))


def _send_input_ok(*inputs: INPUT) -> bool:
    sent = _send_input(*inputs)
    if sent != len(inputs):
        err = _kernel32.GetLastError()
        print(f"[输入] SendInput 失败: sent={sent}/{len(inputs)}, error={err}")
        return False
    return True


def _abs_to_screen(x: int, y: int) -> tuple[int, int]:
    """转换为 SendInput 的 0-65535 绝对坐标空间。"""
    # 使用虚拟桌面坐标，兼容多显示器和负坐标屏幕。
    vx = _user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = _user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = max(_user32.GetSystemMetrics(78), 1)  # SM_CXVIRTUALSCREEN
    vh = max(_user32.GetSystemMetrics(79), 1)  # SM_CYVIRTUALSCREEN
    return int((x - vx) * 65535 / max(vw - 1, 1)), int((y - vy) * 65535 / max(vh - 1, 1))


def _mouse_input(dx: int = 0, dy: int = 0, flags: int = 0,
                 extra_info: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dx = dx
    inp.mi.dy = dy
    inp.mi.dwFlags = flags
    inp.mi.dwExtraInfo = _ULONG_PTR(extra_info)
    return inp


def _set_pos_si(x: int, y: int) -> bool:
    """通过 SendInput 绝对定位鼠标（比 SetCursorPos 更底层）。"""
    ax, ay = _abs_to_screen(x, y)
    return _send_input_ok(_mouse_input(
        ax, ay, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
    ))


def _button_flags(btn: str) -> tuple[int, int]:
    if btn == "left":
        return MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    if btn == "right":
        return MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    raise ValueError(f"不支持的鼠标按钮: {btn}")


def _mouse_down_si(btn: str = "left", extra_info: int = 0) -> bool:
    down, _ = _button_flags(btn)
    return _send_input_ok(_mouse_input(flags=down, extra_info=extra_info))


def _mouse_up_si(btn: str = "left", extra_info: int = 0) -> bool:
    _, up = _button_flags(btn)
    return _send_input_ok(_mouse_input(flags=up, extra_info=extra_info))


def _click_si(x: int, y: int, btn: str = "left",
              extra_info: int = 0) -> bool:
    """通过 SendInput 执行点击（参考 AutoControl: GetMessageExtraInfo）。"""
    # 坐标参数必须真正生效：先定位，再按下/抬起。
    # 旧实现只发送 down/up，verify 重试若已 move_away 会点在移开后的位置。
    if not _set_pos_si(x, y):
        return False
    down, up = _button_flags(btn)
    return _send_input_ok(
        _mouse_input(flags=down, extra_info=extra_info),
        _mouse_input(flags=up, extra_info=extra_info),
    )


def _send_rel(dx: int, dy: int) -> bool:
    """SendInput 相对移动（参考 YOLOv11-CS: mouse_event RELATIVE）。"""
    return _send_input_ok(_mouse_input(dx, dy, MOUSEEVENTF_MOVE))


# ====== 鼠标定位 ======

def _jitter(base: int, variance: int = 5) -> int:
    return base + random.randint(-variance, variance)


def _jitter_point(x: int, y: int, variance: int = 5) -> tuple[int, int]:
    if variance <= 0:
        return x, y
    return _jitter(x, variance), _jitter(y, variance)


def get_pos() -> tuple[int, int]:
    if _HAS_WIN32:
        return _w32.GetCursorPos()
    # fallback to ctypes
    pt = ctypes.wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _set_pos(x: int, y: int) -> bool:
    """设置鼠标位置 — SendInput 优先（更底层）。"""
    return _set_pos_si(x, y)


# ====== 鼠标移动 ======

def _move_bezier(x1: int, y1: int, x2: int, y2: int,
                 duration: float = 0.15, control_off: int = 30) -> None:
    """贝塞尔曲线拟人移动 — 比线性插值更接近真实鼠标轨迹。

    在起点和终点之间加入一个随机偏移的控制点，产生弧形路径。
    """
    cx = (x1 + x2) // 2 + random.randint(-control_off, control_off)
    cy = (y1 + y2) // 2 + random.randint(-control_off, control_off)

    steps = max(10, int(duration * 120))
    for i in range(1, steps + 1):
        t = i / steps
        # quadratic bezier: B(t) = (1-t)^2*P0 + 2*(1-t)*t*P1 + t^2*P2
        bx = int((1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2)
        by = int((1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2)
        if not _set_pos(bx, by):
            return
        time.sleep(random.uniform(duration / steps * 0.7, duration / steps * 1.5))
    _set_pos(x2, y2)


def move_to(x: int, y: int, variance: int = 5, human: bool = False) -> None:
    """移动到绝对坐标（human=True 使用贝塞尔曲线）。"""
    tx, ty = _jitter(x, variance), _jitter(y, variance)
    if human:
        cur = get_pos()
        _move_bezier(cur[0], cur[1], tx, ty, duration=random.uniform(0.08, 0.2))
    else:
        _set_pos(tx, ty)


def move_rel(dx: int, dy: int, human: bool = False) -> None:
    """相对移动 dx, dy 像素（参考 SimuTouch 相对移动系统）。"""
    cur = get_pos()
    tx, ty = cur[0] + dx, cur[1] + dy
    if human:
        _move_bezier(cur[0], cur[1], tx, ty)
    else:
        _send_rel(dx, dy)


def _move_away(x: int, y: int, radius: int = 50) -> None:
    """点击后随机移开鼠标（mhxy-escort 防悬停检测）。"""
    angle = random.uniform(0, 2 * math.pi)
    r = random.randint(radius // 2, radius)
    _set_pos(x + int(math.cos(angle) * r), y + int(math.sin(angle) * r))


# ====== 核心: 点击 ======

def click(x: int, y: int, button: str = "left", variance: int = 5,
          human: bool = False, move_away: bool = True,
          dead_zone: int = 0, verify: Optional[Callable] = None,
          max_verify_retries: int = 2) -> bool:
    """点击屏幕坐标 (x, y) — 融合最优实践。

    流程:
      定位(Bezier/+jitter) → 等0.3s → 点击(SendInput) → 等0.2s → 移开
      → (可选) verify() 检查是否成功 → 失败则 retry

    参数:
      dead_zone: 鼠标已在目标 N 像素内则跳过移动 (YOLOv11-CS)
      verify:    回调函数, 返回 bool, 用于检查点击是否生效 (hermes-agent)
      human:     启用贝塞尔曲线移动
    """
    attempts = max(1, max_verify_retries + 1 if verify is not None else 1)

    for attempt in range(attempts):
        tx, ty = _jitter_point(x, y, variance)

        # Dead zone (YOLOv11-CS): 已在目标附近就不移动
        cur = get_pos()
        dist = math.sqrt((cur[0] - tx) ** 2 + (cur[1] - ty) ** 2)
        skip_move = dead_zone > 0 and dist <= dead_zone
        should_move_away = move_away and not skip_move

        # 1. 定位
        if not skip_move:
            if human:
                _move_bezier(cur[0], cur[1], tx, ty, duration=random.uniform(0.08, 0.2))
            else:
                if not _set_pos(tx, ty):
                    return False

        # 2. 等游戏响应
        time.sleep(random.uniform(0.25, 0.4))

        # 3. 点击 (SendInput 优先)
        if not _click_si(tx, ty, button):
            return False
        time.sleep(random.uniform(0.04, 0.08))

        # 4. 等注册
        time.sleep(random.uniform(0.15, 0.25))

        # 5. 验证 (hermes-agent: closed-loop)
        if verify is None:
            if should_move_away:
                _move_away(tx, ty)
            return True

        time.sleep(random.uniform(0.3, 0.5))
        if verify():
            if should_move_away:
                _move_away(tx, ty)
            return True

        # 验证失败时不要在 move_away 后原地重试；下一轮重新定位并点击。
        time.sleep(random.uniform(0.15, 0.25) * (attempt + 1))

    return False


def double_click(x: int, y: int, variance: int = 5, move_away: bool = True) -> None:
    tx, ty = _jitter_point(x, y, variance)
    if not _set_pos(tx, ty):
        return
    time.sleep(random.uniform(0.04, 0.06))
    if not _click_si(tx, ty, "left"):
        return
    time.sleep(random.uniform(0.05, 0.08))
    _click_si(tx, ty, "left")
    if move_away:
        _move_away(tx, ty)


def right_click(x: int, y: int, variance: int = 5) -> None:
    click(x, y, button="right", variance=variance)


def drag(start_x: int, start_y: int, end_x: int, end_y: int,
         duration: float = 0.3) -> None:
    tx1, ty1 = _jitter_point(start_x, start_y, 3)
    tx2, ty2 = _jitter_point(end_x, end_y, 3)
    if not _set_pos(tx1, ty1):
        return
    time.sleep(0.05)
    if not _mouse_down_si("left"):
        return
    try:
        steps = max(int(duration / 0.01), 10)
        for i in range(1, steps + 1):
            t = i / steps
            if not _set_pos(int(tx1 + (tx2 - tx1) * t), int(ty1 + (ty2 - ty1) * t)):
                break
            time.sleep(0.01)
    finally:
        _mouse_up_si("left")


# ====== 键盘 ======

def press_key(key: str) -> None:
    _keyboard.press(key)
    time.sleep(random.uniform(0.03, 0.06))
    _keyboard.release(key)


def hotkey(*keys: str) -> None:
    for k in keys:
        _keyboard.press(k)
        time.sleep(random.uniform(0.015, 0.03))
    time.sleep(0.05)
    for k in reversed(keys):
        _keyboard.release(k)
        time.sleep(random.uniform(0.015, 0.03))


def type_text(text: str, interval: float = 0.05) -> None:
    for ch in text:
        _keyboard.press(ch)
        _keyboard.release(ch)
        time.sleep(interval)


# ====== DPI 感知 ======

def get_dpi_scale() -> float:
    """获取系统 DPI 缩放比例（hermes-agent 方案）。"""
    try:
        return _user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


def dpi_correct(x: int, y: int) -> tuple[int, int]:
    """将逻辑坐标修正为物理坐标。"""
    scale = get_dpi_scale()
    return int(x * scale), int(y * scale)


# ====== 别名 ======
click_smart = click
click_win32 = click
click_at = click
move_win32 = move_to
click_away = _move_away

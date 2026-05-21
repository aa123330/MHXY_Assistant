"""像素级变化检测 — 借鉴 ScreenChangeShockDevice 的 numpy diff 方案。

提供极快的屏幕区域变化检测，用于：
  - 等待 UI 出现/消失
  - 验证点击是否生效
  - 检测游戏状态切换（加载完成、对话框出现等）
"""

import time
import numpy as np
from typing import Optional, Callable


def pixel_diff(img1: np.ndarray, img2: np.ndarray) -> tuple[bool, int, int]:
    """比较两张图像是否有像素差异。

    返回 (changed, first_x, first_y) — 第一个不同像素的位置。
    比 OpenCV 模板匹配快 100 倍 (~0.05ms)。
    """
    if img1.shape != img2.shape:
        return True, 0, 0
    diff = img1 != img2
    if diff.any():
        indices = np.where(diff)
        return True, int(indices[1][0]), int(indices[0][0])
    return False, 0, 0


def diff_count(img1: np.ndarray, img2: np.ndarray,
               threshold: float = 0.01) -> bool:
    """检查两张图像是否有超过 threshold 比例的像素不同。"""
    if img1.shape != img2.shape:
        return True
    total = img1.size
    changed = np.count_nonzero(img1 != img2)
    return changed / total > threshold


def wait_for_change(capture_fn: Callable, timeout: float = 10.0,
                    interval: float = 0.2, region: Optional[tuple] = None) \
                    -> Optional[tuple[int, int]]:
    """等待屏幕区域发生变化。

    capture_fn: 无参截图函数，返回 numpy 数组
    返回变化点坐标 (x, y)，超时返回 None。
    """
    ref = capture_fn() if region is None else capture_fn(region)
    if ref is None:
        return None

    deadline = time.time() + timeout
    while time.time() < deadline:
        cur = capture_fn() if region is None else capture_fn(region)
        if cur is None:
            continue
        changed, x, y = pixel_diff(ref, cur)
        if changed:
            if region:
                x += region[0]
                y += region[1]
            return x, y
        time.sleep(interval)
    return None


def wait_for_stable(capture_fn: Callable, stability: float = 1.0,
                    timeout: float = 10.0, region: Optional[tuple] = None) -> bool:
    """等待屏幕区域稳定（不再变化）。

    用于等待加载完成、动画结束等场景。
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        ref = capture_fn() if region is None else capture_fn(region)
        if ref is None:
            time.sleep(0.2)
            continue
        time.sleep(stability)
        cur = capture_fn() if region is None else capture_fn(region)
        if cur is None:
            continue
        changed, _, _ = pixel_diff(ref, cur)
        if not changed:
            return True
        time.sleep(0.2)
    return False


def verify_disappeared(capture_fn: Callable, template_hash: str = None,
                       region: Optional[tuple] = None, timeout: float = 5.0) -> bool:
    """验证某个 UI 是否已消失。

    如果提供 template_hash，用感知哈希匹配；
    否则用像素对比（需要先截参考图）。
    """
    if template_hash:
        from .hasher import get_hasher
        h = get_hasher()

        deadline = time.time() + timeout
        while time.time() < deadline:
            img = capture_fn() if region is None else capture_fn(region)
            if img is not None and not h.matches(img, template_hash):
                return True
            time.sleep(0.3)
        return False

    # 无模板 → 像素对比
    ref = capture_fn() if region is None else capture_fn(region)
    if ref is None:
        return False
    time.sleep(timeout * 0.5)
    cur = capture_fn() if region is None else capture_fn(region)
    if cur is None:
        return False
    changed, _, _ = pixel_diff(ref, cur)
    return changed

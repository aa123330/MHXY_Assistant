"""快速颜色像素检测：比 OCR / 模板匹配快 10-50 倍。

借鉴 lua-touchsprite: 多点颜色指纹检测 UI 状态
借鉴 mhxy-escort:   HSV 颜色过滤 + 坐标采样

适用场景:
  - 检测战斗界面（血条红色像素）
  - 检测对话框（底部白色区域）
  - 检测特定按钮/图标
  - 检测地图文字（黄色坐标）
  - 检测任务红字
"""

import numpy as np
from typing import Tuple, Optional


def sample_pixel(img: np.ndarray, x: int, y: int) -> Tuple[int, int, int]:
    """采样单点 RGB 颜色。"""
    h, w = img.shape[:2]
    if 0 <= x < w and 0 <= y < h:
        b, g, r = img[y, x]
        return int(r), int(g), int(b)
    return (-1, -1, -1)


def sample_pixels(img: np.ndarray,
                  points: list[Tuple[int, int]]) -> list[Tuple[int, int, int]]:
    """批量采样多点 RGB 颜色。"""
    return [sample_pixel(img, x, y) for x, y in points]


def match_multi_point(img: np.ndarray,
                      fingerprints: list[Tuple[int, int, Tuple[int, int, int]]],
                      tolerance: int = 30) -> bool:
    """多点颜色指纹匹配。

    fingerprints: [(x, y, (r, g, b)), ...]
    tolerance: 每个通道允许的色差值

    返回 True 表示所有指纹点都匹配（借鉴 lua-touchsprite 的 findUtil 逻辑）。
    """
    for x, y, (r, g, b) in fingerprints:
        pr, pg, pb = sample_pixel(img, x, y)
        if pr < 0:
            return False
        if (abs(pr - r) > tolerance or
            abs(pg - g) > tolerance or
            abs(pb - b) > tolerance):
            return False
    return True


def match_any_fingerprint(img: np.ndarray,
                          fingerprints_list: list[list],
                          tolerance: int = 30) -> Optional[int]:
    """匹配多个指纹组中的任一个。返回匹配的 index，或 None。"""
    for i, fps in enumerate(fingerprints_list):
        if match_multi_point(img, fps, tolerance):
            return i
    return None


def count_color(img: np.ndarray,
                lower: Tuple[int, int, int],
                upper: Tuple[int, int, int],
                region: Optional[Tuple[int, int, int, int]] = None) -> int:
    """统计指定颜色范围内的像素数量（HSV）。

    lower/upper: (H, S, V) 或 (R, G, B) 范围
    region: (x, y, w, h) 可选区域
    """
    if region:
        x, y, w, h = region
        x = max(0, x)
        y = max(0, y)
        roi = img[y:y+max(0, h), x:x+max(0, w)]
    else:
        roi = img
    if roi.size == 0:
        return 0

    mask = cv2_in_range(roi, lower, upper)
    return int(np.sum(mask > 0))


def ratio_color(img: np.ndarray,
                lower: Tuple[int, int, int],
                upper: Tuple[int, int, int],
                region: Optional[Tuple[int, int, int, int]] = None) -> float:
    """指定颜色像素占比。"""
    if region:
        x, y, w, h = region
        total = w * h
    else:
        total = img.shape[0] * img.shape[1]

    if total == 0:
        return 0.0
    return count_color(img, lower, upper, region) / total


def has_red_text(img: np.ndarray,
                 region: Optional[Tuple[int, int, int, int]] = None,
                 threshold: float = 0.01) -> bool:
    """检测是否有红色文字（任务追踪栏中的可点击目标）。

    梦幻西游任务红字: HSV 范围大约 H∈[0,10]∪[170,180], S>150, V>100
    """
    ratio1 = ratio_color(img, (0, 150, 100), (10, 255, 255), region)
    ratio2 = ratio_color(img, (170, 150, 100), (180, 255, 255), region)
    return (ratio1 + ratio2) >= threshold


def has_battle_ui(img: np.ndarray, threshold: float = 0.03) -> bool:
    """检测战斗界面（右下角指令区红色血条）。"""
    h, w = img.shape[:2]
    cmd_region = (int(w * 0.06), int(h * 0.67),
                  int(w * 0.88), int(h * 0.16))
    return ratio_color(img, (0, 100, 50), (10, 255, 255), cmd_region) >= threshold


def has_dialog(img: np.ndarray, threshold: float = 0.3) -> bool:
    """检测对话框（底部大面积白色区域）。"""
    h, w = img.shape[:2]
    dialog_region = (int(w * 0.12), int(h * 0.63),
                     int(w * 0.76), int(h * 0.30))
    # 用灰度做快速检查
    if dialog_region[2] <= 0 or dialog_region[3] <= 0:
        return False
    x, y, rw, rh = dialog_region
    roi = img[y:y+rh, x:x+rw]
    if roi.size == 0:
        return False
    gray = np.mean(roi, axis=2) if len(roi.shape) == 3 else roi
    return np.sum(gray > 180) / max(gray.size, 1) >= threshold


def find_red_text_center(img: np.ndarray,
                         region: Optional[Tuple[int, int, int, int]] = None
                         ) -> Optional[Tuple[int, int]]:
    """找到红色文字区域的中心坐标（用于点击任务红字）。"""
    if region:
        x, y, w, h = region
        roi = img[y:y+h, x:x+w]
        offset_x, offset_y = x, y
    else:
        roi = img
        offset_x, offset_y = 0, 0

    # 提取红色像素
    r_channel = roi[:, :, 2]  # BGR → R 在 index 2
    g_channel = roi[:, :, 1]
    b_channel = roi[:, :, 0]

    # 红色条件: R > G + threshold AND R > B + threshold
    red_mask = (r_channel.astype(int) > g_channel.astype(int) + 40) & \
               (r_channel.astype(int) > b_channel.astype(int) + 40) & \
               (r_channel > 100)

    if np.sum(red_mask) < 10:
        return None

    ys, xs = np.where(red_mask)
    return (int(np.mean(xs)) + offset_x, int(np.mean(ys)) + offset_y)


# 内部辅助
try:
    import cv2
    def cv2_in_range(img, lower, upper):
        if len(img.shape) == 3:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            return cv2.inRange(hsv, np.array(lower), np.array(upper))
        return cv2.inRange(img, np.array(lower), np.array(upper))
except ImportError:
    def cv2_in_range(img, lower, upper):
        if len(img.shape) == 3:
            r, g, b = img[:,:,2], img[:,:,1], img[:,:,0]
            return ((r >= lower[0]) & (r <= upper[0]) &
                    (g >= lower[1]) & (g <= upper[1]) &
                    (b >= lower[2]) & (b <= upper[2])).astype(np.uint8) * 255
        return np.zeros(img.shape[:2], dtype=np.uint8)

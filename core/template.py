"""模板匹配：基于 OpenCV 的图像模板匹配。"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional
from functools import lru_cache

from .paths import get_source_dir, get_user_dir


def _template_search_dirs(category: str = "") -> list[Path]:
    """返回模板搜索目录列表，用户目录优先。"""
    dirs = []
    user = get_user_dir() / "data" / "templates" / category
    source = get_source_dir() / "data" / "templates" / category
    if user.exists():
        dirs.append(user)
    dirs.append(source)
    return dirs


@lru_cache(maxsize=256)
def load_template(name: str, category: str = "") -> np.ndarray:
    """加载模板图片。在多目录中搜索，用户目录优先。"""
    if not name.endswith((".png", ".jpg", ".bmp")):
        name = name + ".png"

    for d in _template_search_dirs(category):
        path = d / name
        if path.exists():
            img = cv2.imread(str(path))
            if img is not None:
                return img

    raise FileNotFoundError(f"Template not found: {name} (category: {category or 'root'})")


def _can_match(screenshot: np.ndarray, template: np.ndarray) -> bool:
    if screenshot is None or template is None:
        return False
    sh, sw = screenshot.shape[:2]
    th, tw = template.shape[:2]
    return sh >= th and sw >= tw and sh > 0 and sw > 0 and th > 0 and tw > 0


def match_template(
    screenshot: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    method: int = cv2.TM_CCOEFF_NORMED,
) -> Optional[tuple[int, int]]:
    """单模板匹配，返回最佳匹配的左上角坐标，低于阈值返回 None。"""
    if not _can_match(screenshot, template):
        return None
    h, w = template.shape[:2]
    result = cv2.matchTemplate(screenshot, template, method)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        return max_loc
    return None


def match_all(
    screenshot: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    method: int = cv2.TM_CCOEFF_NORMED,
) -> list[tuple[int, int]]:
    """多目标模板匹配，返回所有超过阈值的匹配位置。"""
    if not _can_match(screenshot, template):
        return []
    h, w = template.shape[:2]
    result = cv2.matchTemplate(screenshot, template, method)
    locations = []
    ys, xs = np.where(result >= threshold)
    used = set()
    for x, y in sorted(zip(xs, ys), key=lambda p: result[p[1], p[0]], reverse=True):
        if any(abs(x - ux) < w // 2 and abs(y - uy) < h // 2 for ux, uy in used):
            continue
        locations.append((x, y))
        used.add((x, y))
    return locations


def get_center(template: np.ndarray, match_loc: tuple[int, int]) -> tuple[int, int]:
    """根据匹配位置和模板尺寸，计算中心点坐标。"""
    h, w = template.shape[:2]
    return match_loc[0] + w // 2, match_loc[1] + h // 2


def match_best(
    screenshot: np.ndarray,
    template_names: list[str],
    category: str = "",
    threshold: float = 0.8,
) -> Optional[tuple[str, tuple[int, int], float]]:
    """从多个模板中匹配最佳的一个，返回 (名称, 位置, 置信度)。"""
    best_name, best_loc, best_val = None, None, 0
    for name in template_names:
        tmpl = load_template(name, category)
        if not _can_match(screenshot, tmpl):
            continue
        h, w = tmpl.shape[:2]
        result = cv2.matchTemplate(screenshot, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_val and max_val >= threshold:
            best_val = max_val
            best_loc = max_loc
            best_name = name
    if best_name:
        return best_name, best_loc, best_val
    return None


# ====== 多方法共识匹配（借鉴 BestBurning/mhxy） ======

MATCH_METHODS = [
    cv2.TM_CCOEFF,
    cv2.TM_CCOEFF_NORMED,
    cv2.TM_CCORR,
    cv2.TM_CCORR_NORMED,
    cv2.TM_SQDIFF,
    cv2.TM_SQDIFF_NORMED,
]


def match_consensus(screenshot: np.ndarray, template: np.ndarray,
                    min_votes: int = 3) -> tuple | None:
    """6种匹配方法投票共识 — 找到最可靠的匹配位置。

    返回: (x, y, w, h) 或 None
    借鉴 BestBurning/mhxy 的做法，用 6 种 OpenCV 匹配方法同时跑，
    取多方法共识的 bbox，大幅减少误匹配。
    """
    if not _can_match(screenshot, template):
        return None

    gray_src = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    gray_tmpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    h, w = gray_tmpl.shape

    shape_votes: dict[tuple, int] = {}

    for method in MATCH_METHODS:
        res = cv2.matchTemplate(gray_src, gray_tmpl, method)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            _, _, min_loc, _ = cv2.minMaxLoc(res)
            top_left = min_loc
        else:
            top_left = max_loc

        shape = (top_left[0], top_left[1], top_left[0] + w, top_left[1] + h)
        shape_votes[shape] = shape_votes.get(shape, 0) + 1

    if not shape_votes:
        return None

    best_shape = max(shape_votes, key=shape_votes.get)
    votes = shape_votes[best_shape]

    if votes >= min_votes:
        return (
            best_shape[0], best_shape[1],
            best_shape[2] - best_shape[0], best_shape[3] - best_shape[1],
        )
    return None


def match_consensus_with_score(screenshot: np.ndarray, template: np.ndarray,
                               min_votes: int = 3) -> tuple | None:
    """多方法共识匹配，返回 (x, y, w, h, vote_count)。"""
    if not _can_match(screenshot, template):
        return None

    gray_src = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    gray_tmpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    h, w = gray_tmpl.shape

    shape_votes: dict[tuple, int] = {}

    for method in MATCH_METHODS:
        res = cv2.matchTemplate(gray_src, gray_tmpl, method)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            _, _, min_loc, _ = cv2.minMaxLoc(res)
            top_left = min_loc
        else:
            top_left = max_loc

        shape = (top_left[0], top_left[1], top_left[0] + w, top_left[1] + h)
        shape_votes[shape] = shape_votes.get(shape, 0) + 1

    if not shape_votes:
        return None

    best_shape = max(shape_votes, key=shape_votes.get)
    votes = shape_votes[best_shape]

    if votes >= min_votes:
        return (
            best_shape[0], best_shape[1],
            best_shape[2] - best_shape[0], best_shape[3] - best_shape[1],
            votes,
        )
    return None

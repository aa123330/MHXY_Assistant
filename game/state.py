"""游戏状态机：融合场景模板匹配 + 特征检测判断当前游戏状态。"""

import time
import cv2
import numpy as np
from enum import Enum
from pathlib import Path
from .constants import GameState

from core.paths import get_source_dir
from core.hasher import get_hasher
from core.color_detect import has_battle_ui, has_dialog
TEMPLATE_DIR = get_source_dir() / "data" / "templates"


class StateDetector:
    """综合状态检测器。

    优先级：
    1. YOLO 检测（如可用）— 最精确
    2. 场景模板匹配（SceneDetector）— 适合固定场景
    3. 像素特征检测 — 兜底方案
    """

    def __init__(self, scene_detector=None, yolo_detector=None):
        self._current_state = GameState.UNKNOWN
        self._state_start = time.time()
        self._last_minimap_hash = None
        self._stuck_since = None
        self.scene_detector = scene_detector
        self.yolo = yolo_detector
        self.hasher = get_hasher()  # 感知哈希快速检测

    @property
    def current(self) -> GameState:
        return self._current_state

    @property
    def duration(self) -> float:
        return time.time() - self._state_start

    def update(self, screenshot: np.ndarray, minimap_img: np.ndarray = None) -> GameState:
        """分析截图，更新并返回当前状态。"""
        new_state = self._detect(screenshot, minimap_img)
        if new_state != self._current_state:
            self._current_state = new_state
            self._state_start = time.time()
        return self._current_state

    def _detect(self, screen: np.ndarray, minimap: np.ndarray) -> GameState:
        # 0. 感知哈希快速检查 — 比 YOLO/模板匹配快 50 倍
        hash_state = self._hash_quick_check(screen)
        if hash_state != GameState.UNKNOWN:
            return hash_state

        # 1. YOLO 检测
        if self.yolo:
            yolo_state = self._detect_by_yolo(screen)
            if yolo_state != GameState.UNKNOWN:
                return yolo_state

        # 2. 场景模板匹配
        if self.scene_detector:
            scene_name, conf = self.scene_detector.detect(screen)
            if conf >= 0.5:
                if "battle" in scene_name or "fight" in scene_name:
                    return GameState.BATTLE
                elif "dialog" in scene_name or "word" in scene_name:
                    return GameState.DIALOG
                elif "login" in scene_name:
                    return GameState.IDLE

        # 3. 像素特征兜底
        if self._is_battle(screen):
            return GameState.BATTLE
        if self._is_dialog(screen):
            return GameState.DIALOG
        if self._is_loading(screen):
            return GameState.LOADING
        if minimap is not None and self._is_walking(minimap):
            return GameState.WALKING

        return GameState.IDLE

    def _hash_quick_check(self, screen: np.ndarray) -> GameState:
        """感知哈希快速检查：只截取几个关键 UI 小区域。"""
        if screen is None or screen.size == 0:
            return GameState.UNKNOWN
        h, w = screen.shape[:2]

        # 检查战斗 UI（右下角指令区 ~80x40 像素足够）
        battle_patch = screen[int(h * 0.78):int(h * 0.85), int(w * 0.06):int(w * 0.3)]
        if self.hasher.matches_any(battle_patch, ["battle_cmd", "battle_ui"], threshold=20):
            return GameState.BATTLE

        # 检查对话框区域（底部中央 ~100x30）
        dialog_patch = screen[int(h * 0.8):int(h * 0.88), int(w * 0.3):int(w * 0.7)]
        if self.hasher.matches_any(dialog_patch, ["dialog_next", "dialog_box"], threshold=20):
            return GameState.DIALOG

        return GameState.UNKNOWN

    def _detect_by_yolo(self, screen: np.ndarray) -> GameState:
        """通过 YOLO 类别判断状态。"""
        try:
            detections = self.yolo.detect(screen)
        except Exception:
            return GameState.UNKNOWN
        class_names = {str(d.get("class_name", "")).lower() for d in detections}

        battle_names = {"monster", "battle_ui", "command_ui", "battle_command"}
        dialog_names = {"dialog", "dialog_box", "dialog_next"}

        if class_names.intersection(battle_names):
            return GameState.BATTLE
        if class_names.intersection(dialog_names):
            return GameState.DIALOG

        return GameState.UNKNOWN

    # ---------- 像素特征检测（兜底） ----------

    def _is_battle(self, screen: np.ndarray) -> bool:
        return has_battle_ui(screen, threshold=0.03)

    def _is_dialog(self, screen: np.ndarray) -> bool:
        return has_dialog(screen, threshold=0.3)

    def _is_loading(self, screen: np.ndarray) -> bool:
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        return np.sum(gray < 30) / max(gray.size, 1) > 0.7

    def _is_walking(self, minimap: np.ndarray) -> bool:
        if minimap is None or minimap.size == 0:
            return False
        if hasattr(cv2, "img_hash"):
            current_hash = cv2.img_hash.blockMeanHash(minimap)
        else:
            small = cv2.resize(minimap, (16, 16), interpolation=cv2.INTER_AREA)
            current_hash = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if self._last_minimap_hash is not None:
            diff = cv2.norm(self._last_minimap_hash, current_hash, cv2.NORM_HAMMING)
            self._last_minimap_hash = current_hash
            if diff > 5:
                self._stuck_since = None
                return True
            elif diff <= 1 and self._stuck_since is None:
                self._stuck_since = time.time()
        self._last_minimap_hash = current_hash
        return False

    def is_stuck(self, threshold: float = 5.0) -> bool:
        if self._stuck_since is None:
            return False
        return (time.time() - self._stuck_since) > threshold

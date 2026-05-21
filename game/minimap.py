"""小地图定位：通过模板匹配确定玩家在世界地图中的位置。"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional

from core.paths import get_source_dir
MAPS_DIR = get_source_dir() / "data" / "maps"


class MinimapTracker:
    """追踪小地图位置变化，推算角色在世界中的坐标。"""

    def __init__(self, world_map_name: str = "changan"):
        self.world_map = cv2.imread(str(MAPS_DIR / f"{world_map_name}.png"))
        self.world_x = 0
        self.world_y = 0
        self._prev_minimap: Optional[np.ndarray] = None

    def locate(self, minimap_img: np.ndarray) -> Optional[tuple[int, int]]:
        """用小地图在世界地图中做模板匹配，返回世界坐标。"""
        if self.world_map is None or minimap_img is None or minimap_img.size == 0:
            return None

        h, w = minimap_img.shape[:2]
        result = cv2.matchTemplate(self.world_map, minimap_img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= 0.5:
            self.world_x = max_loc[0] + w // 2
            self.world_y = max_loc[1] + h // 2
            return self.world_x, self.world_y

        return None

    def update_position(self, dx: int, dy: int) -> None:
        """手动更新位置偏移。"""
        self.world_x += dx
        self.world_y += dy

    @property
    def position(self) -> tuple[int, int]:
        return self.world_x, self.world_y

    def load_map(self, name: str) -> None:
        """切换世界地图。"""
        self.world_map = cv2.imread(str(MAPS_DIR / f"{name}.png"))

    def get_minimap_bounds(self) -> tuple[int, int, int, int]:
        """估算当前小地图对应的世界地图区域。"""
        h, w = 160, 160  # 小地图大约 160x160
        return (
            max(self.world_x - w // 2, 0),
            max(self.world_y - h // 2, 0),
            min(self.world_x + w // 2, self.world_map.shape[1]),
            min(self.world_y + h // 2, self.world_map.shape[0]),
        )

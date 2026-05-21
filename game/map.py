"""地图与寻路：A* 算法在世界地图网格上寻路，输出屏幕点击坐标。"""

import heapq
import json
import numpy as np
from pathlib import Path
from typing import Optional
from math import sqrt

from core.paths import get_source_dir, get_user_dir, ensure_dirs
MAPS_DIR = get_source_dir() / "data" / "maps"
USER_MAPS_DIR = get_user_dir() / "data" / "maps"


class GridMap:
    """基于网格的地图，支持 A* 寻路。"""

    def __init__(self, width: int, height: int, grid_size: int = 8):
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.cols = width // grid_size
        self.rows = height // grid_size
        # 0 = 可行走, 1 = 障碍
        self.grid = np.zeros((self.rows, self.cols), dtype=np.uint8)

    def set_obstacle(self, x: int, y: int) -> None:
        """标记障碍格。"""
        r, c = y // self.grid_size, x // self.grid_size
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.grid[r, c] = 1

    def set_walkable(self, x: int, y: int) -> None:
        """标记可行走格。"""
        r, c = y // self.grid_size, x // self.grid_size
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.grid[r, c] = 0

    def is_walkable(self, x: int, y: int) -> bool:
        r, c = y // self.grid_size, x // self.grid_size
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r, c] == 0
        return False

    def world_to_grid(self, wx: int, wy: int) -> tuple[int, int]:
        return wx // self.grid_size, wy // self.grid_size

    def grid_to_world(self, gx: int, gy: int) -> tuple[int, int]:
        return gx * self.grid_size + self.grid_size // 2, gy * self.grid_size + self.grid_size // 2

    def save(self, name: str) -> None:
        """保存网格到 JSON。"""
        path = MAPS_DIR / f"{name}.json"
        data = {
            "width": self.width, "height": self.height,
            "grid_size": self.grid_size,
            "grid": self.grid.tolist(),
        }
        path.write_text(json.dumps(data, ensure_ascii=False))

    @classmethod
    def load(cls, name: str) -> "GridMap":
        """从 JSON 加载网格。"""
        path = MAPS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        gm = cls(data["width"], data["height"], data["grid_size"])
        gm.grid = np.array(data["grid"], dtype=np.uint8)
        return gm


def astar_path(
    grid: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """A* 寻路，返回路径点列表 [(gx,gy), ...]，空列表表示不可达。"""
    rows, cols = grid.shape

    def neighbors(node):
        r, c = node
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr, nc] == 0:
                # 对角线需检查两侧是否可通过
                if dr != 0 and dc != 0:
                    if grid[r + dr, c] == 1 or grid[r, c + dc] == 1:
                        continue
                cost = sqrt(2) if dr != 0 and dc != 0 else 1
                yield (nr, nc), cost

    open_set = [(0, 0, start, [start])]  # (f, g, node, path)
    closed = {}

    while open_set:
        f, g, node, path = heapq.heappop(open_set)
        if node == goal:
            return path
        if node in closed and closed[node] <= g:
            continue
        closed[node] = g

        for neighbor, cost in neighbors(node):
            ng = g + cost
            nf = ng + sqrt((neighbor[0] - goal[0]) ** 2 + (neighbor[1] - goal[1]) ** 2)
            heapq.heappush(open_set, (nf, ng, neighbor, path + [neighbor]))

    return []


def simplify_path(path: list[tuple[int, int]], grid: np.ndarray) -> list[tuple[int, int]]:
    """使用线-of-sight 简化路径，移除冗余拐点。"""
    if len(path) <= 2:
        return path

    simplified = [path[0]]
    i = 1
    while i < len(path) - 1:
        if not _line_of_sight(simplified[-1], path[i + 1], grid):
            simplified.append(path[i])
        i += 1
    simplified.append(path[-1])
    return simplified


def _line_of_sight(a: tuple, b: tuple, grid: np.ndarray) -> bool:
    """Bresenham 线检查 a 到 b 之间是否无障碍。"""
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while (x0, y0) != (x1, y1):
        if 0 <= y0 < grid.shape[0] and 0 <= x0 < grid.shape[1] and grid[y0, x0] == 1:
            return False
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return True


class PathPlanner:
    """将世界坐标路径转换为屏幕点击坐标序列。"""

    def __init__(self, grid_map: GridMap, window_rect: tuple, minimap_screen_rect: tuple):
        self.grid_map = grid_map
        self.win_left, self.win_top = window_rect[:2]
        self.mm_left, self.mm_top = minimap_screen_rect[:2]  # 小地图屏幕坐标
        self.mm_w = minimap_screen_rect[2] - minimap_screen_rect[0]
        self.mm_h = minimap_screen_rect[3] - minimap_screen_rect[1]

    def plan(
        self,
        world_start: tuple[int, int],
        world_goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """规划路径，返回屏幕点击坐标列表。"""
        gs = self.grid_map.world_to_grid(*world_start)
        gg = self.grid_map.world_to_grid(*world_goal)

        grid_path = astar_path(self.grid_map.grid, gs, gg)
        if not grid_path:
            return []

        grid_path = simplify_path(grid_path, self.grid_map.grid)

        # 转为屏幕坐标：需要知道小地图当前显示的世界区域
        screen_clicks = []
        for gx, gy in grid_path[1:]:  # 跳过起点
            wx, wy = self.grid_map.grid_to_world(gx, gy)
            sx, sy = self._world_to_screen(wx, wy)
            screen_clicks.append((sx, sy))

        return screen_clicks

    def _world_to_screen(self, wx: int, wy: int) -> tuple[int, int]:
        """世界坐标转屏幕坐标（通过小地图映射）。"""
        # 简化：小地图中心对应玩家位置，偏移量映射到屏幕
        # 实际需根据小地图的缩放比例换算
        sx = self.mm_left + self.mm_w // 2
        sy = self.mm_top + self.mm_h // 2
        return sx, sy

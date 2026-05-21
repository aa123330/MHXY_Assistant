"""自动巡逻：在指定地图循环走动，遇怪自动战斗。

用于刷经验、练宝宝等挂机场景。
"""

import time
import random
from .base import BaseTask, Step


class PatrolTask(BaseTask):
    name = "自动巡逻"
    description = "在指定地图循环走动，自动遇怪战斗"

    def __init__(self, game_context: dict):
        super().__init__(game_context)
        self._patrol_points = []
        self._current_point = 0
        self._battle_count = 0

    def set_patrol_route(self, points: list[tuple[int, int]]) -> None:
        self._patrol_points = points

    def build_steps(self) -> list[Step]:
        return [
            Step("检查战斗状态", self._check_battle_first, timeout=5),
            Step("移动到巡逻点", self._move_to_point, timeout=15),
            Step("等待到达并检查遇怪", self._wait_arrival, timeout=10),
            Step("处理战斗", self._handle_battle, timeout=120),
            Step("检查补给", self._check_supplies, timeout=5),
        ]

    def _check_battle_first(self) -> bool:
        """先检查是否已经在战斗中。"""
        detector = self.ctx.get("state_detector")
        battle = self.ctx.get("battle_handler")
        if detector and detector.current.name == "BATTLE" and battle:
            battle.handle()
        return True

    def _move_to_point(self) -> bool:
        if not self._patrol_points:
            return True

        click = self.ctx.get("click")
        if click:
            x, y = self._patrol_points[self._current_point]
            click(x, y)
            self._current_point = (self._current_point + 1) % len(self._patrol_points)

        time.sleep(random.uniform(2.0, 4.0))
        return True

    def _wait_arrival(self) -> bool:
        detector = self.ctx.get("state_detector")
        deadline = time.time() + 10
        while time.time() < deadline:
            if detector and detector.current.name == "BATTLE":
                return True
            time.sleep(0.5)
        return True

    def _handle_battle(self) -> bool:
        detector = self.ctx.get("state_detector")
        battle = self.ctx.get("battle_handler")
        if detector and battle:
            while detector.current.name == "BATTLE":
                battle.handle()
                time.sleep(0.5)
            self._battle_count += 1
        return True

    def _check_supplies(self) -> bool:
        """检查是否需要回复 HP/MP。"""
        # TODO: 检测血条蓝条，低于阈值自动吃药
        return True

    @property
    def battle_count(self) -> int:
        return self._battle_count

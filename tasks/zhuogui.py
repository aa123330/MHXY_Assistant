"""捉鬼任务：自动捉鬼 10 轮。

流程：
1. 前往地府找钟馗
2. 接取捉鬼任务
3. 天眼定位鬼怪位置
4. 自动寻路到鬼怪
5. 对话进入战斗
6. 战斗结束 → 返回地府交任务
"""

import time
import pyautogui
from .base import BaseTask, Step


class ZhuoguiTask(BaseTask):
    name = "捉鬼任务"
    description = "自动完成捉鬼日常任务（10轮）"

    def __init__(self, game_context: dict):
        super().__init__(game_context)
        task_cfg = self.ctx.get("config", {}).get("tasks", {}).get("zhuogui", {})
        self.max_rounds = task_cfg.get("max_rounds", 10)
        self._round = 0

    def build_steps(self) -> list[Step]:
        return [
            Step("前往地府", self._go_to_difu, timeout=30),
            Step("找钟馗对话", self._talk_to_zhongkui, timeout=15),
            Step("接受捉鬼任务", self._accept_quest, timeout=10),
            Step("天眼定位", self._use_tianyan, timeout=5),
            Step("前往目标地图", self._go_to_target, timeout=30),
            Step("找到鬼怪并进入战斗", self._find_and_fight, timeout=60),
            Step("等待战斗结束", self._wait_battle, timeout=180),
            Step("返回交任务", self._return_and_turnin, timeout=30),
        ]

    def _go_to_difu(self) -> bool:
        navigator = self.ctx.get("navigator")
        if navigator:
            return navigator.go_to_location("地府")
        return True

    def _talk_to_zhongkui(self) -> bool:
        npc = self.ctx.get("npc")
        click = self.ctx.get("click")
        if npc:
            return npc.find_and_talk("钟馗")
        elif click:
            click(400, 300)
            time.sleep(2)
        return True

    def _accept_quest(self) -> bool:
        click = self.ctx.get("click")
        if click:
            for _ in range(3):
                click(400, 520)
                time.sleep(0.8)
        return True

    def _use_tianyan(self) -> bool:
        print("[捉鬼] 使用天眼通符...")
        pyautogui.hotkey("alt", "t")
        time.sleep(1)
        return True

    def _go_to_target(self) -> bool:
        navigator = self.ctx.get("navigator")
        ocr = self.ctx.get("ocr")
        if ocr and navigator:
            screen = self.ctx.get("capture")()
            results = ocr(screen)
            for r in results:
                for map_name in ["长安", "长寿", "傲来", "朱紫", "建邺", "东海湾",
                                 "大唐境外", "花果山", "江南野外", "大唐国境",
                                 "长寿郊外", "北俱芦洲"]:
                    if map_name in r["text"]:
                        return navigator.go_to_location(map_name)
        return True

    def _find_and_fight(self) -> bool:
        """找到鬼怪并进入战斗。"""
        click = self.ctx.get("click")
        yolo = self.ctx.get("yolo_detector")
        screen = self.ctx.get("capture")()

        # YOLO 优先
        if yolo:
            ghost = yolo.find_class(screen, 2)  # 鬼怪类别
            if ghost:
                click(*ghost["center"])
                time.sleep(2)
                # 对话框确认
                click(400, 520)
                time.sleep(1)
                return True

        # OCR 兜底
        ocr = self.ctx.get("ocr")
        if ocr:
            for item in ocr(screen):
                if any(kw in item["text"] for kw in ["鬼", "僵尸", "马面", "牛头", "骷髅"]):
                    cx = (item["bbox"][0] + item["bbox"][2]) // 2
                    cy = (item["bbox"][1] + item["bbox"][3]) // 2
                    click(cx, cy)
                    time.sleep(2)
                    click(400, 520)
                    return True

        return False

    def _wait_battle(self) -> bool:
        detector = self.ctx.get("state_detector")
        battle = self.ctx.get("battle_handler")
        if battle and detector:
            while detector.current.name == "BATTLE":
                battle.handle()
                time.sleep(0.5)
        return True

    def _return_and_turnin(self) -> bool:
        """返回钟馗处交任务。"""
        navigator = self.ctx.get("navigator")
        if navigator:
            navigator.go_to_location("地府")

        npc = self.ctx.get("npc")
        if npc and npc.find_and_talk("钟馗"):
            click = self.ctx.get("click")
            if click:
                for _ in range(3):
                    click(400, 520)
                    time.sleep(0.8)
            self._round += 1
            print(f"[捉鬼] 完成第 {self._round} 轮")
            return True
        return False

    @property
    def current_round(self) -> int:
        return self._round

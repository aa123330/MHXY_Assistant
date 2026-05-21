"""师门任务：自动完成 20 轮师门任务。

参考项目:
  - menghuanxiyou:  template matching + OCR 任务识别 + recursive retry
  - lua-touchsprite: combat loop + sub-action dispatch (buy/use/submit)
  - mhxy_fz:         simple polling loop with hash comparison

流程:
  回师门(F8) → 找师傅(模板匹配) → 领任务(点击) → 识别任务类型(OCR)
  → 按类型执行 → 回去交任务 → 循环 20 次直到完成
"""

import time
import random
from .base import BaseTask, Step, register_task


@register_task("shimen")
class ShimenTask(BaseTask):
    name = "师门任务"
    description = "自动完成 20 轮师门任务（找师傅、领任务、执行、回去交）"

    DONE_KEYWORDS = ["已完成", "完成", "已结束", "已领取", "20/20"]

    TASK_TYPES = {
        "combat":  ["战斗", "击败", "消灭", "打败", "怪物", "妖魔", "示威"],
        "buy":     ["购买", "买", "商会", "杂货"],
        "use":     ["使用", "给", "送"],
        "submit":  ["上交", "提交", "交", "献"],
        "escort":  ["护送", "保护"],
        "deliver": ["送信", "传话", "告诉", "通知"],
        "patrol":  ["巡逻"],
    }

    def __init__(self, game_context: dict):
        super().__init__(game_context)
        task_cfg = self.ctx.get("config", {}).get("tasks", {}).get("shimen", {})
        self._max_rounds = task_cfg.get("max_rounds", 20)
        self._round = 0
        self._task_type = ""
        self._last_task_text = ""
        self._battle_count = 0

    def build_steps(self) -> list[Step]:
        return [
            Step("回师门",       self._go_back,           timeout=15, retries=2),
            Step("找师傅领任务",  self._find_master,       timeout=20, retries=3),
            Step("识别任务类型",  self._identify_task,     timeout=10, retries=3),
            Step("执行任务",     self._execute_task,       timeout=120, retries=1),
            Step("回去交任务",    self._submit_task,        timeout=30, retries=2),
            Step("检查是否完成",  self._check_completion,   timeout=10, retries=2),
        ]

    # ====== 步骤 1: 回师门 ======

    def _go_back(self) -> bool:
        hotkey = self.ctx.get("input_hotkey")
        if hotkey:
            hotkey("f8")
        time.sleep(2.0)
        return True

    # ====== 步骤 2: 找师傅 ======

    def _find_master(self) -> bool:
        match = self.ctx.get("template_match")
        click = self.ctx.get("click")
        capture = self.ctx.get("capture")

        if not match or not click:
            return True

        img = capture()
        if img is None:
            return False

        result = match(img, "master", "npc")
        if result:
            cx, cy = result
            print(f"[师门] 找到师傅: ({cx}, {cy})")
            click(cx, cy)
            time.sleep(1.5)
            return True

        # 没扫到模板也继续（可能已站在师傅面前）
        print("[师门] 未找到师傅，尝试继续")
        click(400, 300)  # 画面中央点击
        time.sleep(1.0)
        return True

    # ====== 步骤 3: 识别任务类型 ======

    def _identify_task(self) -> bool:
        click = self.ctx.get("click")
        capture = self.ctx.get("capture")
        ocr = self.ctx.get("ocr")
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")

        # 点击推进对话框
        if click:
            for _ in range(5):
                click(400, 520)
                time.sleep(0.8)

        if not ocr or not capture:
            self._task_type = "unknown"
            return True

        if tracker_region:
            img = capture(tuple(tracker_region))
            if img is not None:
                results = ocr(img)
                if results:
                    texts = [r["text"] for r in results]
                    all_text = " ".join(texts)
                    print(f"[师门] 任务文字: {all_text}")
                    self._last_task_text = all_text

                    for ttype, keywords in self.TASK_TYPES.items():
                        if any(kw in all_text for kw in keywords):
                            self._task_type = ttype
                            print(f"[师门] 识别为: {ttype}")
                            return True

        self._task_type = "unknown"
        return True

    # ====== 步骤 4: 执行任务 ======

    def _execute_task(self) -> bool:
        print(f"[师门] 执行 {self._task_type} 任务...")

        handlers = {
            "combat":  self._do_go_and_fight,
            "buy":     self._do_go_and_find,
            "use":     self._do_give_item,
            "submit":  self._do_give_item,
            "deliver": self._do_go_and_find,
            "escort":  self._do_go_and_fight,
            "patrol":  self._do_patrol,
        }

        handler = handlers.get(self._task_type, self._do_go_and_find)
        return handler()

    def _do_go_and_fight(self) -> bool:
        """去目标地点战斗。"""
        self._click_tracker_target()
        self._handle_combat_loop(timeout=60)
        return True

    def _do_go_and_find(self) -> bool:
        """去目标地点找 NPC/物品。"""
        self._click_tracker_target()
        self._wait_for_arrival(timeout=60)
        return True

    def _do_give_item(self) -> bool:
        """给予/上交物品。"""
        click = self.ctx.get("click")
        hotkey = self.ctx.get("input_hotkey")
        if hotkey:
            hotkey("alt", "g")
        time.sleep(1.0)
        if click:
            click(400, 450)
            time.sleep(1.0)
        return True

    def _do_patrol(self) -> bool:
        """巡逻：在区域内走动。"""
        click = self.ctx.get("click")
        if click:
            for _ in range(10):
                click(random.randint(300, 500), random.randint(200, 400), variance=20)
                time.sleep(3.0)
                if self._check_battle():
                    self._handle_combat_loop(timeout=30)
                    return True
        return True

    # ====== 步骤 5: 回去交任务 ======

    def _submit_task(self) -> bool:
        hotkey = self.ctx.get("input_hotkey")
        click = self.ctx.get("click")
        match = self.ctx.get("template_match")
        capture = self.ctx.get("capture")

        if hotkey:
            hotkey("f8")
        time.sleep(2.0)

        if match and capture:
            img = capture()
            if img is not None:
                result = match(img, "master", "npc")
                if result:
                    click(result[0], result[1])
                    time.sleep(1.5)
                else:
                    click(400, 300)
                    time.sleep(1.0)

        # 推进对话交任务
        if click:
            for _ in range(5):
                click(400, 520)
                time.sleep(0.8)

        return True

    # ====== 步骤 6: 检查完成 ======

    def _check_completion(self) -> bool:
        capture = self.ctx.get("capture")
        ocr = self.ctx.get("ocr")
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")

        self._round += 1
        print(f"[师门] 第 {self._round}/{self._max_rounds} 轮完成")

        if self._round >= self._max_rounds:
            print("[师门] 已完成全部轮次")
            return True

        if ocr and capture and tracker_region:
            img = capture(tuple(tracker_region))
            if img is not None:
                results = ocr(img)
                if results:
                    all_text = " ".join(r["text"] for r in results)
                    if all(kw in all_text for kw in ["完成", "20"]):
                        print("[师门] 全部完成")
                        return True

        # 继续下一轮
        self._current_step = 0
        self._steps = self.build_steps()
        return True

    # ====== 辅助方法 ======

    def _click_tracker_target(self):
        """点击任务追踪栏的红色目标文字（使用剧情任务的逻辑）。"""
        try:
            from tasks.plot import PlotTask
            pt = PlotTask(self.ctx)
            pt._scan_quest()
            if pt._last_objective:
                pt._click_objective()
        except Exception:
            pass

    def _handle_combat_loop(self, timeout: float = 60):
        """循环处理战斗直到结束。"""
        detector = self.ctx.get("state_detector")
        battle = self.ctx.get("battle_handler")
        deadline = time.time() + timeout

        while time.time() < deadline:
            if detector and detector.current.name == "BATTLE":
                print("[师门] 战斗中...")
                if battle:
                    battle.handle()
                self._battle_count += 1
                time.sleep(0.5)
            else:
                time.sleep(1.0)
                if not detector:
                    break
                if detector.current.name not in ("BATTLE",):
                    break

    def _wait_for_arrival(self, timeout: float = 60):
        """等待角色到达目的地。"""
        detector = self.ctx.get("state_detector")
        click = self.ctx.get("click")
        deadline = time.time() + timeout

        while time.time() < deadline:
            if self._check_battle():
                self._handle_combat_loop(timeout=30)
                continue
            if detector and detector.current.name == "DIALOG":
                if click:
                    click(400, 520)
                time.sleep(0.5)
                return
            time.sleep(1.0)

    def _check_battle(self) -> bool:
        detector = self.ctx.get("state_detector")
        return detector is not None and detector.current.name == "BATTLE"

    @property
    def battle_count(self) -> int:
        return self._battle_count

    @property
    def current_round(self) -> int:
        return self._round

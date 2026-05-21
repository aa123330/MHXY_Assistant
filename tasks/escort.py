"""押镖任务：自动接镖 → 护送 → 交镖。

参考 mhxy-escort:
  - 到长风镖局找郑镖头接镖
  - OCR 识别押镖目标 NPC
  - 剧情任务逻辑自动寻路到交付 NPC
  - 路上处理战斗
  - 到目标 NPC 交付镖银

简化版：复用剧情任务的 OCR+点击自动寻路逻辑。
"""

import time
import random
from .base import BaseTask, Step, register_task


@register_task("escort")
class EscortTask(BaseTask):
    name = "押镖任务"
    description = "自动接镖、护送、交镖（需先在长风镖局）"

    # 押镖关键词
    ESCORT_KEYWORDS = ["押镖", "镖", "郑镖头", "镖银", "四级镖"]
    DELIVER_KEYWORDS = ["交付", "送达", "交给", "送到"]

    def __init__(self, game_context: dict):
        super().__init__(game_context)
        task_cfg = self.ctx.get("config", {}).get("tasks", {}).get("escort", {})
        self._max_rounds = task_cfg.get("max_rounds", 5)
        self._round = 0
        self._target_npc = ""
        self._escort_accepted = False
        self._battle_count = 0

    def build_steps(self) -> list[Step]:
        if not self._escort_accepted:
            # 第一阶段：接镖
            return [
                Step("找到郑镖头",    self._find_escort_npc,  timeout=20, retries=3),
                Step("接受押镖任务",   self._accept_escort,    timeout=15, retries=2),
                Step("识别交付目标",   self._identify_target,  timeout=10, retries=3),
            ]
        else:
            # 第二阶段：护送 + 交付
            return [
                Step("自动寻路到目标",  self._navigate_to_target, timeout=180, retries=1),
                Step("交付镖银",       self._deliver_goods,     timeout=30, retries=2),
                Step("返回镖局",       self._return_to_start,   timeout=30, retries=2),
            ]

    # ====== 接镖阶段 ======

    def _find_escort_npc(self) -> bool:
        """找郑镖头（模板匹配 + 点击）。"""
        click = self.ctx.get("click")
        match = self.ctx.get("template_match")
        capture = self.ctx.get("capture")

        if not click:
            return True

        # 模板匹配找 NPC
        if match and capture:
            img = capture()
            if img is not None:
                # 尝试匹配押镖相关模板
                for tmpl_name in ("escort_npc", "zhengbiaotou", "master"):
                    try:
                        result = match(img, tmpl_name, "npc")
                        if result:
                            print(f"[押镖] 找到 NPC: {tmpl_name}")
                            click(result[0], result[1])
                            time.sleep(1.5)
                            return True
                    except Exception:
                        continue

        # 没找到模板 → OCR 方式找 NPC
        ocr = self.ctx.get("ocr")
        if ocr and capture:
            img = capture()
            if img is not None:
                results = ocr(img)
                for r in results:
                    if any(kw in r["text"] for kw in ["镖", "郑"]):
                        cx = (r["bbox"][0] + r["bbox"][2]) // 2
                        cy = (r["bbox"][1] + r["bbox"][3]) // 2
                        click(cx, cy)
                        time.sleep(1.5)
                        return True

        # 兜底：点击画面中央
        click(400, 300)
        time.sleep(1.5)
        return True

    def _accept_escort(self) -> bool:
        """接受押镖任务。"""
        click = self.ctx.get("click")
        ocr = self.ctx.get("ocr")
        capture = self.ctx.get("capture")

        if not click:
            return True

        # 推进对话框
        for _ in range(5):
            click(400, 520)
            time.sleep(0.8)

        # 寻找"押镖"或"接取任务"按钮
        if ocr and capture:
            img = capture()
            if img is not None:
                results = ocr(img)
                for r in results:
                    if any(kw in r["text"] for kw in ["押镖", "接取", "四级镖", "普通镖"]):
                        cx = (r["bbox"][0] + r["bbox"][2]) // 2
                        cy = (r["bbox"][1] + r["bbox"][3]) // 2
                        click(cx, cy)
                        time.sleep(1.0)
                        break

        # 确认接取
        time.sleep(1.0)
        click(400, 450)
        time.sleep(1.0)

        self._escort_accepted = True
        print("[押镖] 已接受押镖任务")
        return True

    def _identify_target(self) -> bool:
        """OCR 识别要交付的目标 NPC 名字。"""
        ocr = self.ctx.get("ocr")
        capture = self.ctx.get("capture")
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")

        if not ocr or not capture:
            return True

        if tracker_region:
            img = capture(tuple(tracker_region))
            if img is not None:
                results = ocr(img)
                if results:
                    texts = [r["text"] for r in results]
                    all_text = " ".join(texts)
                    print(f"[押镖] 任务文字: {all_text}")

                    # 找 NPC 名字（通常在人名关键词后面的 2-4 字中文）
                    for kw in ["交给", "送至", "送给", "交付给"]:
                        if kw in all_text:
                            idx = all_text.index(kw)
                            after = all_text[idx + len(kw):idx + len(kw) + 8]
                            self._target_npc = after.strip()
                            print(f"[押镖] 目标 NPC: {self._target_npc}")
                            return True

        return True

    # ====== 护送阶段 ======

    def _navigate_to_target(self) -> bool:
        """自动寻路到目标 NPC（复用剧情任务逻辑）。"""
        click = self.ctx.get("click")
        capture = self.ctx.get("capture")
        ocr = self.ctx.get("ocr")
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")

        # 尝试点击追踪栏目标 → 触发自动寻路
        if click and ocr and capture and tracker_region:
            try:
                from tasks.plot import PlotTask
                pt = PlotTask(self.ctx)
                deadline = time.time() + 180
                last_scan = 0

                while time.time() < deadline:
                    # 处理战斗
                    if self._check_battle():
                        self._handle_escort_combat()
                        continue

                    # 每 5 秒重新扫描
                    now = time.time()
                    if now - last_scan > 5:
                        pt._scan_quest()
                        last_scan = now

                    if pt._last_objective:
                        pt._click_objective()
                        # 等待到达
                        time.sleep(3.0)
                    else:
                        time.sleep(1.0)

                    # 检查是否已到目的地（对话框出现）
                    detector = self.ctx.get("state_detector")
                    if detector and detector.current.name == "DIALOG":
                        print("[押镖] 已到达目的地")
                        return True

            except Exception as e:
                print(f"[押镖] 寻路异常: {e}")

        return True

    def _deliver_goods(self) -> bool:
        """交付镖银给目标 NPC。"""
        click = self.ctx.get("click")
        hotkey = self.ctx.get("input_hotkey")

        if not click:
            return True

        # 确保对话框已打开
        time.sleep(1.0)
        for _ in range(3):
            click(400, 520)
            time.sleep(0.8)

        # Alt+G 打开给予界面
        if hotkey:
            hotkey("alt", "g")
        time.sleep(1.5)

        # 找镖银并点击
        ocr = self.ctx.get("ocr")
        capture = self.ctx.get("capture")
        if ocr and capture:
            img = capture()
            if img is not None:
                results = ocr(img)
                for r in results:
                    if any(kw in r["text"] for kw in ["镖银", "四级镖", "银两"]):
                        cx = (r["bbox"][0] + r["bbox"][2]) // 2
                        cy = (r["bbox"][1] + r["bbox"][3]) // 2
                        click(cx, cy)
                        time.sleep(0.5)
                        break

        # 确认给予
        click(400, 450)
        time.sleep(1.5)

        self._round += 1
        print(f"[押镖] 第 {self._round} 次任务交付完成")
        return True

    def _return_to_start(self) -> bool:
        """返回长风镖局（可选：只为了继续下一轮）。"""
        if self._round >= self._max_rounds:
            print("[押镖] 已完成全部轮次")
            return True

        # 重置接镖状态，准备下一轮
        self._escort_accepted = False
        self._current_step = 0
        self._steps = self.build_steps()
        return True

    # ====== 辅助 ======

    def _handle_escort_combat(self):
        """处理押镖路上的战斗。"""
        detector = self.ctx.get("state_detector")
        battle = self.ctx.get("battle_handler")

        print("[押镖] 遭遇战斗，自动处理...")
        while detector and detector.current.name == "BATTLE":
            if battle:
                battle.handle()
            self._battle_count += 1
            time.sleep(0.5)

    def _check_battle(self) -> bool:
        detector = self.ctx.get("state_detector")
        return detector is not None and detector.current.name == "BATTLE"

    @property
    def battle_count(self) -> int:
        return self._battle_count

    @property
    def current_round(self) -> int:
        return self._round

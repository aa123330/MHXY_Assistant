"""剧情任务：自动完成剧情/主线任务。

原理:
  梦幻西游的任务追踪栏有可点击的任务目标文字（通常为红色/高亮）。
  点击目标后游戏会自动寻路到 NPC/地点。

定位策略 (双重):
  1. OCR 识别追踪栏文字 → 评分选最可能是红字的
  2. 颜色检测找红色像素区域 → 作为 OCR 的补充

鼠标 (借鉴 mhxy-escort + mhxy_fz):
  - win32api 直连 + 随机偏移 (防检测)
  - 点击后立即移开鼠标
  - 最多 3 次位置修正重试
"""

import time
from .base import BaseTask, Step, register_task


@register_task("plot")
class PlotTask(BaseTask):
    name = "剧情任务"
    description = "自动完成剧情/主线任务（通用，不需要预设任务信息）"

    DONE_KEYWORDS = ["已完成", "完成", "已结束", "领取奖励"]

    def __init__(self, game_context: dict):
        super().__init__(game_context)
        self._last_objective = ""
        self._clicked_objective = ""
        self._click_retries = 0
        self._same_objective_count = 0
        self._dialog_count = 0
        self._battle_count = 0

    def build_steps(self) -> list[Step]:
        return [
            Step("扫描任务目标", self._scan_quest, timeout=10, retries=3),
            Step("点击目标寻路", self._click_objective, timeout=10, retries=3),
            Step("等待到达+处理交互", self._wait_and_handle, timeout=120, retries=1),
            Step("检查任务进度", self._check_progress, timeout=10, retries=2),
        ]

    # ====== 步骤 1: 扫描 ======

    def _scan_quest(self) -> bool:
        """双重定位任务目标: 颜色检测红字(优先) + OCR(辅助)。"""
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")
        capture = self.ctx.get("capture")
        ocr = self.ctx.get("ocr")

        if not capture:
            return True

        img = capture(tuple(tracker_region)) if tracker_region else capture()
        if img is None:
            return True

        best_text = ""
        best_bbox = None

        # 1. 颜色检测优先 — 找红色文字像素中心 (比 OCR bbox 更精确)
        try:
            from core.color_detect import find_red_text_center
            red_center = find_red_text_center(img)
            if red_center:
                rx, ry = red_center
                best_text = "(红字)"
                # 小 bbox 环绕红字中心
                best_bbox = (rx - 25, ry - 10, rx + 25, ry + 10)
                print(f"[剧情] 颜色定位红字: ({rx}, {ry})")
        except Exception as e:
            print(f"[剧情] 颜色检测异常: {e}")

        # 2. OCR 补充 — 获取文字内容，辅助验证
        if ocr and (not best_text or best_text == "(红字)"):
            results = ocr(img) if img is not None else []
            candidates = []
            if results:
                for r in results:
                    text = r["text"].strip()
                    if not text or len(text) < 2:
                        continue
                    if any(kw in text for kw in self.DONE_KEYWORDS):
                        continue
                    if text.isdigit() and len(text) > 3:
                        continue
                    candidates.append(r)

            if candidates:
                def _score(r):
                    text = r["text"].strip()
                    cy = (r["bbox"][1] + r["bbox"][3]) / 2
                    s = cy / 1000.0
                    if 2 <= len(text) <= 5:
                        s += 2.0
                    if any('一' <= c <= '鿿' for c in text):
                        s += 3.0
                    return s
                candidates.sort(key=_score, reverse=True)
                best = candidates[0]
                # 如果颜色检测没找到，用 OCR bbox
                if not best_text:
                    best_text = best["text"]
                    best_bbox = best["bbox"]
                elif best_text == "(红字)":
                    # 用 OCR 文字替换 "(红字)" 占位
                    best_text = best["text"]
                print(f"[剧情] OCR 候选: {len(candidates)} 条, 最佳: '{best_text}'")

        if not best_text:
            self._last_objective = ""
            print("[剧情] 未找到任务目标（无红字无OCR文本）")
            return True

        if best_text != self._last_objective:
            self._clicked_objective = ""
            self._click_retries = 0

        self._last_objective = best_text
        if tracker_region and best_bbox:
            self._target_bbox = (
                best_bbox[0] + tracker_region[0],
                best_bbox[1] + tracker_region[1],
                best_bbox[2] + tracker_region[0],
                best_bbox[3] + tracker_region[1],
            )
        else:
            self._target_bbox = best_bbox

        print(f"[剧情] 目标: '{self._last_objective}' bbox={self._target_bbox}")
        return True

    # ====== 步骤 2: 点击 ======

    def _click_objective(self) -> bool:
        """点击目标文字，带 X+Y 位置修正重试。

        红字通常在任务描述右侧，OCR bbox 可能包含整行文字。
        策略: 优先点 bbox 偏右偏上的位置，然后向外螺旋修正。
        """
        if not hasattr(self, '_target_bbox') or not self._last_objective:
            return True
        if self._click_retries >= 5:
            print(f"[剧情] 放弃点击 '{self._last_objective}'")
            self._clicked_objective = self._last_objective
            return True
        if self._last_objective == self._clicked_objective:
            return True

        click = self.ctx.get("click")
        if not click:
            return True

        bbox_w = self._target_bbox[2] - self._target_bbox[0]
        bbox_h = self._target_bbox[3] - self._target_bbox[1]

        # 螺旋偏移: (x_ratio, y_px) — X 用 bbox 宽度比例，Y 用像素
        # 从偏右偏上开始，逐步向外修正
        offsets = [
            (0.75, -2),   # 首次: bbox 75%处(偏右), 上移2px
            (0.70, -4),   # 第2次: 稍微左移, 更上
            (0.80, 0),    # 第3次: 偏右, 正中Y
            (0.65, -6),   # 第4次: 再左, 再上
            (0.50, 2),    # 第5次: 正中, 下移
        ]
        x_ratio, oy = offsets[min(self._click_retries, len(offsets) - 1)]

        cx = int(self._target_bbox[0] + bbox_w * x_ratio)
        cy = int(self._target_bbox[1] + bbox_h * 0.4 + oy)  # bbox 40%高度处 + 偏移

        print(f"[剧情] 点击 (第{self._click_retries+1}次, x@{x_ratio:.0%}+y{oy:+d}): "
              f"({cx}, {cy}) bbox({self._target_bbox[0]},{self._target_bbox[1]} "
              f"{bbox_w}x{bbox_h}) → '{self._last_objective}'")
        click(cx, cy, variance=4)
        self._click_retries += 1
        time.sleep(1.0)

        # 验证
        capture = self.ctx.get("capture")
        ocr = self.ctx.get("ocr")
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")

        if capture and ocr and tracker_region:
            try:
                img = capture(tuple(tracker_region))
                if img is not None:
                    results = ocr(img)
                    current = [r["text"].strip() for r in results] if results else []
                    if self._last_objective not in current:
                        print(f"[剧情] ✓ 点击生效，目标已变化")
                        self._clicked_objective = self._last_objective
                        return True
                    print(f"[剧情] 目标未变化，调整位置重试")
            except Exception as e:
                print(f"[剧情] 验证失败: {e}")

        return True

    # ====== 步骤 3: 等待 & 交互 ======

    def _wait_and_handle(self) -> bool:
        detector = self.ctx.get("state_detector")
        battle = self.ctx.get("battle_handler")
        click = self.ctx.get("click")

        deadline = time.time() + 120
        stuck = 0

        while time.time() < deadline:
            if detector and detector.current.name == "BATTLE":
                print("[剧情] 战斗中...")
                while detector.current.name == "BATTLE":
                    if battle:
                        battle.handle()
                    time.sleep(0.5)
                self._battle_count += 1
                continue

            if detector and detector.current.name == "DIALOG":
                print("[剧情] NPC 对话，点击推进...")
                self._dialog_count += 1
                for _ in range(20):
                    if detector.current.name != "DIALOG":
                        break
                    if click:
                        click(400, 520, variance=8)
                    time.sleep(0.6)
                return True

            if detector and detector.current.name != "WALKING":
                stuck += 1
                if stuck > 6:
                    print("[剧情] 角色停止移动，可能已到达")
                    return True
            else:
                stuck = 0

            if self._check_objective_changed():
                print("[剧情] 任务文字已更新")
                return True

            time.sleep(0.5)

        print("[剧情] 等待超时")
        return True

    # ====== 步骤 4: 检查进度 ======

    def _check_progress(self) -> bool:
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")
        capture = self.ctx.get("capture")
        ocr = self.ctx.get("ocr")

        if not capture or not ocr:
            return True

        img = capture(tuple(tracker_region)) if tracker_region else capture()
        if img is None:
            return True

        results = ocr(img)
        if not results:
            # 可能是区域不对 → 尝试全屏 OCR
            if tracker_region:
                full = capture()
                if full is not None:
                    results = ocr(full)
            if not results:
                print("[剧情] 任务追踪栏为空，全部完成！")
                return True

        all_text = " ".join(r["text"] for r in results)
        print(f"[剧情] 追踪栏: {all_text}")

        has_unfinished = any(
            not any(kw in r["text"] for kw in self.DONE_KEYWORDS)
            for r in results
        )

        if not has_unfinished:
            print("[剧情] 所有任务已完成！")
            return True

        # 继续循环
        self._current_step = 0
        self._steps = self.build_steps()
        return True

    # ====== 辅助 ======

    def _check_objective_changed(self) -> bool:
        tracker_region = self.ctx.get("config", {}).get("regions", {}).get("task_tracker")
        capture = self.ctx.get("capture")
        ocr = self.ctx.get("ocr")

        if not capture or not ocr or not tracker_region:
            return False

        img = capture(tuple(tracker_region))
        if img is None:
            return False

        results = ocr(img)
        if not results:
            return False

        current = results[0]["text"].strip() if results else ""
        changed = current != self._last_objective and current != ""
        return changed

    @property
    def dialog_count(self) -> int:
        return self._dialog_count

    @property
    def battle_count(self) -> int:
        return self._battle_count

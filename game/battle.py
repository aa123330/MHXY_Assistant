"""战斗模块：智能目标选择 + 弹窗选人处理。

借鉴 BestBurning/mhxy 的 6方法投票匹配 + 角色分类思路：
- 检测"请选择"弹窗 → 裁剪角色区域
- 用 YOLO / 特征分析判断该点哪个角色
- 精确计算点击位置，避免点错被强制退出
"""

import time
import cv2
import numpy as np
from pathlib import Path
from .constants import GameState

# 弹窗人物裁剪参数（基于 800×600 窗口，需根据实际调整）
POPUP_CROP_PARAMS = {
    # 弹窗出现时，4个角色的排列区域（相对于弹窗左上角的偏移）
    "sub_offset": (0, 60),       # 角色区域相对于弹窗的偏移
    "sub_size": (360, 120),      # 4角色总区域大小
    "char_width": 90,            # 单个角色宽度 (360/4)
    "char_height": 120,          # 单个角色高度
}

# 选人弹窗模板文件名
POPUP_TEMPLATE_NAMES = ["popup_flag_1.png", "popup_flag_2.png",
                        "popup_select.png", "popup_choose.png"]

DATA_DIR = Path(__file__).parent.parent / "data" / "templates" / "battle"


class BattleHandler:
    """自动战斗处理器（含弹窗选人 + 智能目标选择）。"""

    TARGET_PROMPTS = ["请选择", "选择目标", "选择攻击", "请点击", "请选择攻击"]

    def __init__(self, capture_fn, input_click_fn, input_hotkey_fn, ocr_fn,
                 config: dict, yolo_detector=None):
        self.capture = capture_fn
        self.click = input_click_fn
        self.hotkey = input_hotkey_fn
        self.ocr = ocr_fn
        self.config = config
        self.yolo = yolo_detector
        self._round_count = 0
        self._last_action_time = 0
        self._wrong_clicks = 0
        self._max_wrong = config.get("max_wrong_clicks", 5)
        self._verify_after_action = config.get("use_yolo_verify", True)
        self._smart_targeting = config.get("smart_targeting", True)

        # 弹窗选人模板（懒加载）
        self._popup_templates: list[np.ndarray] | None = None

    # ====== 主入口 ======

    def handle(self) -> GameState:
        screen = self.capture()
        if screen is None:
            return GameState.BATTLE

        if not self._in_battle(screen):
            self._wrong_clicks = 0
            return GameState.IDLE

        if not self._is_my_turn(screen):
            time.sleep(0.3)
            return GameState.BATTLE

        # ── 关键：先检查是否有选人弹窗 ──
        if self._smart_targeting:
            popup_result = self._detect_and_handle_popup(screen)
            if popup_result:
                self._round_count += 1
                return GameState.BATTLE

        # 正常攻击流程
        action = self.config.get("default_action", "attack")
        if action == "attack":
            self._do_attack()
        elif action == "skill":
            self._do_skill()
        elif action == "defend":
            self._do_defend()

        self._round_count += 1
        self._last_action_time = time.time()

        if self._verify_after_action:
            time.sleep(0.5)
            self._verify_action_success()

        return GameState.BATTLE

    # ====== 弹窗选人（核心新增） ======

    def _load_popup_templates(self) -> list[np.ndarray]:
        """加载选人弹窗的模板图片。"""
        if self._popup_templates is not None:
            return self._popup_templates

        templates = []
        for name in POPUP_TEMPLATE_NAMES:
            path = DATA_DIR / name
            if path.exists():
                img = cv2.imread(str(path))
                if img is not None:
                    templates.append(img)

        self._popup_templates = templates
        return templates

    def _detect_and_handle_popup(self, screen: np.ndarray) -> bool:
        """检测选人弹窗并处理。返回 True 表示弹窗已处理。"""
        # 方法1: 模板匹配找弹窗标识
        templates = self._load_popup_templates()
        if templates:
            from core.template import match_consensus_with_score

            for tmpl in templates:
                result = match_consensus_with_score(screen, tmpl, min_votes=3)
                if result is not None:
                    x, y, w, h, votes = result
                    print(f"[战斗] 检测到选人弹窗 (votes={votes}) at ({x},{y})")
                    self._handle_character_selection(screen, x, y, w, h)
                    return True

        # 方法2: OCR 检测"请选择"文字
        if self.ocr:
            h, w = screen.shape[:2]
            prompt_area = screen[0:int(h * 0.3), int(w * 0.15):int(w * 0.85)]
            try:
                results = self.ocr(prompt_area)
                for r in results:
                    for kw in self.TARGET_PROMPTS:
                        if kw in r["text"]:
                            print(f"[战斗] OCR检测到选人提示: {r['text']}")
                            # 估算弹窗位置
                            self._handle_character_selection_fallback(screen)
                            return True
            except Exception:
                pass

        return False

    def _handle_character_selection(self, screen: np.ndarray,
                                     popup_x: int, popup_y: int,
                                     popup_w: int, popup_h: int) -> None:
        """处理选人弹窗：裁剪角色 → 判断该点谁 → 点击。"""
        h, w = screen.shape[:2]

        # 计算角色区域在截图中的位置
        sub_ox, sub_oy = POPUP_CROP_PARAMS["sub_offset"]
        sub_w, sub_h = POPUP_CROP_PARAMS["sub_size"]
        char_w = POPUP_CROP_PARAMS["char_width"]

        sub_x = max(0, popup_x + sub_ox)
        sub_y = max(0, popup_y + sub_oy)
        sub_x2 = min(w, sub_x + sub_w)
        sub_y2 = min(h, sub_y + sub_h)

        if sub_x2 <= sub_x or sub_y2 <= sub_y:
            print("[战斗] 弹窗角色区域越界，使用兜底方案")
            self._handle_character_selection_fallback(screen)
            return

        # 裁剪4角色区域
        char_region = screen[sub_y:sub_y2, sub_x:sub_x2]
        if char_region.size == 0:
            return

        # 切成4张单个角色图
        char_imgs = []
        actual_char_w = (sub_x2 - sub_x) // 4
        for i in range(4):
            cx = i * actual_char_w
            c_img = char_region[:, cx:cx + actual_char_w]
            char_imgs.append(c_img)

        # 判断该点哪个（第几个）
        target_idx = self._classify_character(char_imgs)
        print(f"[战斗] 选人结果: 第 {target_idx + 1} 个角色")

        # 计算该角色在截图中的中心坐标
        char_cx = sub_x + target_idx * actual_char_w + actual_char_w // 2
        char_cy = sub_y + (sub_y2 - sub_y) // 2

        # 点击
        self.click(char_cx, char_cy)
        time.sleep(0.3)

        # 验证：点完后弹窗还在吗？
        verify_screen = self.capture()
        if verify_screen is not None:
            templates = self._load_popup_templates()
            if templates:
                from core.template import match_consensus
                still_there = any(
                    match_consensus(verify_screen, t, min_votes=2) is not None
                    for t in templates
                )
                if still_there:
                    # 还在 → 可能点错了，尝试下一个
                    next_idx = (target_idx + 1) % 4
                    print(f"[战斗] 弹窗未消失，尝试第 {next_idx + 1} 个")
                    next_cx = sub_x + next_idx * actual_char_w + actual_char_w // 2
                    self.click(next_cx, char_cy)
                    time.sleep(0.3)

    def _handle_character_selection_fallback(self, screen: np.ndarray) -> None:
        """兜底：没有模板时，用 OCR 或 YOLO 找目标。"""
        h, w = screen.shape[:2]

        # YOLO
        if self.yolo:
            detections = self.yolo.detect(screen)
            chars = [d for d in detections
                     if d["class_name"] in ("npc", "monster") or d["class_id"] in (1, 2)]
            if chars:
                chars.sort(key=lambda d: d["confidence"], reverse=True)
                self.click(*chars[0]["center"])
                time.sleep(0.3)
                return

        # 兜底：点画面中央偏左第一个角色位置
        # （大多数情况下第一个角色就是目标）
        self.click(int(w * 0.35), int(h * 0.45))
        time.sleep(0.3)

    def _classify_character(self, char_imgs: list[np.ndarray]) -> int:
        """判断4个角色中该选哪一个。

        返回 0-3 的索引。

        方法优先级:
          1. YOLO 检测正面朝向的角色
          2. 图像特征分析（正面角色通常面部区域更亮/更多细节）
          3. 默认选第2个（中间位置，多数情况）
        """
        # 方法1: YOLO
        if self.yolo:
            scores = []
            for img in char_imgs:
                if img.size == 0:
                    scores.append(0)
                    continue
                detections = self.yolo.detect(img)
                # 正面角色 → YOLO 检测到的置信度更高
                best_conf = max((d["confidence"] for d in detections), default=0)
                scores.append(best_conf)

            if any(s > 0 for s in scores):
                # 最高置信度的 → 最有可能是正面角色
                return scores.index(max(scores))

        # 方法2: 面部亮度特征
        brightness_scores = []
        for img in char_imgs:
            if img.size == 0:
                brightness_scores.append(0)
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 正面角色 → 面部更大 → 浅色区域更多（人脸肤色亮）
            light_pixels = np.sum(gray > 140)
            brightness_scores.append(light_pixels)

        if brightness_scores:
            # 浅色像素最多的 = 正面朝向
            return brightness_scores.index(max(brightness_scores))

        # 方法3: 默认第2个
        return 1

    # ====== 战斗检测 ======

    def _in_battle(self, screen: np.ndarray = None) -> bool:
        if screen is None:
            screen = self.capture()
        if self.yolo:
            for d in self.yolo.detect(screen):
                if d["class_name"] in ("monster", "battle_ui"):
                    return True
        h, w = screen.shape[:2]
        cmd_region = screen[int(h * 0.67):int(h * 0.83), int(w * 0.06):int(w * 0.94)]
        red_mask = cv2.inRange(cmd_region, (0, 0, 100), (50, 50, 255))
        return np.sum(red_mask > 0) / max(red_mask.size, 1) > 0.03

    def _is_my_turn(self, screen: np.ndarray) -> bool:
        if self.yolo:
            for d in self.yolo.detect(screen):
                if d["class_name"] in ("button", "command_ui"):
                    return True
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        cmd_area = gray[int(h * 0.67):int(h * 0.83), int(w * 0.06):int(w * 0.94)]
        return np.sum(cmd_area > 200) > 500

    # ====== 目标选择 ======

    def _is_targeting(self) -> bool:
        screen = self.capture()
        if screen is None or not self.ocr:
            return False
        h, w = screen.shape[:2]
        prompt_region = screen[0:int(h * 0.3), int(w * 0.2):int(w * 0.8)]
        try:
            for r in self.ocr(prompt_region):
                for kw in self.TARGET_PROMPTS:
                    if kw in r["text"]:
                        return True
        except Exception:
            pass
        return False

    def _find_enemy_targets(self, screen: np.ndarray) -> list[dict]:
        targets = []
        h, w = screen.shape[:2]

        if self.yolo:
            for d in self.yolo.detect(screen):
                if d["class_name"] in ("monster",) or d["class_id"] in (2,):
                    targets.append({
                        "center": d["center"], "bbox": d["bbox"],
                        "confidence": d["confidence"], "source": "yolo",
                    })

        if not targets:
            battle_area = screen[int(h * 0.15):int(h * 0.55), int(w * 0.1):int(w * 0.9)]
            red_mask = cv2.inRange(battle_area, (0, 0, 120), (60, 60, 255))
            contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if cv2.contourArea(cnt) < 30:
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                targets.append({
                    "center": (x + int(w * 0.1) + bw // 2, y + int(h * 0.15) + bh + 40),
                    "bbox": (x + int(w * 0.1), y + int(h * 0.15), bw, bh),
                    "confidence": 0.5, "source": "color",
                })

        return targets

    def _find_enemy_by_ocr(self, target_name: str = None) -> tuple[int, int] | None:
        if not self.ocr:
            return None
        screen = self.capture()
        if screen is None:
            return None
        h, w = screen.shape[:2]
        enemy_area = screen[int(h * 0.1):int(h * 0.6), int(w * 0.1):int(w * 0.9)]
        try:
            for r in self.ocr(enemy_area):
                cx = (r["bbox"][0] + r["bbox"][2]) // 2 + int(w * 0.1)
                cy = (r["bbox"][1] + r["bbox"][3]) // 2 + int(h * 0.1) + 50
                if target_name and target_name in r["text"]:
                    return cx, cy
                elif not target_name and len(r["text"].strip()) >= 2:
                    return cx, cy
        except Exception:
            pass
        return None

    # ====== 攻击操作 ======

    def _do_attack(self) -> None:
        self.hotkey("alt", "a")
        time.sleep(0.4)

        if not self._is_targeting():
            return

        screen = self.capture()
        if screen is None:
            screen = np.zeros((600, 800, 3), dtype=np.uint8)
        targets = self._find_enemy_targets(screen)
        if targets:
            targets.sort(key=lambda t: t["confidence"], reverse=True)
            self.click(*targets[0]["center"])
            time.sleep(0.3)
            if self._is_targeting() and len(targets) > 1:
                self.click(*targets[1]["center"])
                time.sleep(0.3)
            self._wrong_clicks = 0
            return

        ocr_pos = self._find_enemy_by_ocr()
        if ocr_pos:
            self.click(*ocr_pos)
            self._wrong_clicks = 0
            return

        self._wrong_clicks += 1
        if self._wrong_clicks >= self._max_wrong:
            self._try_tab_select()
            self._wrong_clicks = 0
        else:
            self.hotkey("esc")

    def _do_skill(self) -> None:
        self.hotkey("alt", "w")
        time.sleep(0.4)
        if not self._is_targeting():
            return
        screen = self.capture()
        if screen is None:
            screen = np.zeros((600, 800, 3), dtype=np.uint8)
        targets = self._find_enemy_targets(screen)
        if targets:
            targets.sort(key=lambda t: t["confidence"], reverse=True)
            self.click(*targets[0]["center"])
            self._wrong_clicks = 0
            return
        self._wrong_clicks += 1
        if self._wrong_clicks >= self._max_wrong:
            self._try_tab_select()
            self._wrong_clicks = 0

    def _do_defend(self) -> None:
        self.hotkey("alt", "d")

    def _click_target(self) -> bool:
        """（保留兼容旧接口）"""
        screen = self.capture()
        if screen is None:
            return False
        targets = self._find_enemy_targets(screen)
        if targets:
            targets.sort(key=lambda t: t["confidence"], reverse=True)
            self.click(*targets[0]["center"])
            return True
        ocr_pos = self._find_enemy_by_ocr()
        if ocr_pos:
            self.click(*ocr_pos)
            return True
        return False

    def _try_tab_select(self) -> None:
        print(f"[战斗] 已点错 {self._wrong_clicks} 次，切换策略")
        self.hotkey("esc")
        time.sleep(0.2)
        self.hotkey("alt", "a")
        time.sleep(0.4)
        for _ in range(3):
            self.hotkey("tab")
            time.sleep(0.2)
        self.hotkey("alt", "a")

    def _verify_action_success(self) -> bool:
        if self._is_targeting():
            return False
        screen = self.capture()
        if self.yolo and screen is not None:
            return any(
                d["class_name"] in ("monster", "battle_ui")
                for d in self.yolo.detect(screen)
            )
        return True

    @property
    def round_count(self) -> int:
        return self._round_count

    @property
    def wrong_clicks(self) -> int:
        return self._wrong_clicks

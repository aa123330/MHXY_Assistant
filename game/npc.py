"""NPC 交互：查找 NPC、对话、选择选项。"""

import time
from typing import Optional
from .constants import NPC_OPTION_RECT


class NPCInteraction:
    """NPC 查找与对话管理。"""

    def __init__(self, capture_fn, click_fn, ocr_fn, match_fn):
        self.capture = capture_fn
        self.click = click_fn
        self.ocr = ocr_fn
        self.match = match_fn

    def find_and_talk(
        self,
        npc_name: str,
        search_region: Optional[tuple] = None,
    ) -> bool:
        """在场景中查找 NPC 并点击对话。"""
        screen = self.capture(search_region)
        result = self.ocr(screen)
        for item in result:
            if npc_name in item["text"]:
                cx, cy = (
                    (item["bbox"][0] + item["bbox"][2]) // 2,
                    (item["bbox"][1] + item["bbox"][3]) // 2,
                )
                self.click(cx, cy)
                time.sleep(1.0)
                return self.wait_dialog_open()
        return False

    def wait_dialog_open(self, timeout: float = 5.0) -> bool:
        """等待对话框打开。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            screen = self.capture()
            h, w = screen.shape[:2]
            dialog = screen[int(h * 0.63):int(h * 0.93), int(w * 0.12):int(w * 0.88)]
            gray = dialog.mean() if hasattr(dialog, 'mean') else 0
            # 简化检测：灰度均值高 = 浅色对话框
            gray_val = gray.mean() if hasattr(gray, 'mean') else gray
            if hasattr(dialog, 'mean'):
                if dialog.mean() > 150:
                    return True
            else:
                if gray_val > 150:
                    return True
            time.sleep(0.3)
        return False

    def click_dialog_option(self, text: str, timeout: float = 3.0) -> bool:
        """点击对话中的选项。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            screen = self.capture(NPC_OPTION_RECT)
            result = self.ocr(screen)
            for item in result:
                if text in item["text"]:
                    cx = (item["bbox"][0] + item["bbox"][2]) // 2 + NPC_OPTION_RECT[0]
                    cy = (item["bbox"][1] + item["bbox"][3]) // 2 + NPC_OPTION_RECT[1]
                    self.click(cx, cy)
                    time.sleep(0.5)
                    return True
            time.sleep(0.3)
        return False

    def advance_dialog(self, count: int = 1) -> None:
        """点击对话框推进对话（模拟点击"下一步"）。"""
        for _ in range(count):
            self.click(400, 520)
            time.sleep(0.5)

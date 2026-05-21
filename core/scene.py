"""场景检测：通过多模板匹配判断当前游戏场景。

借鉴 menghuanxiyou 项目的 SceneDetector 设计：
截取不同游戏场景（登录、战斗、对话、大地图等）作为模板，
运行时用模板匹配判断当前处于哪个场景。
"""

import os
import numpy as np
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
from pathlib import Path
from typing import Optional, Tuple
from .paths import get_source_dir, get_user_dir


class SceneDetector:
    """基于多模板匹配的场景检测器。"""

    def __init__(
        self,
        template_dir: str = "data/templates/scenes",
        match_threshold: float = 0.7,
    ):
        self.template_dir = Path(template_dir)
        if not self.template_dir.is_absolute():
            self.template_dir = get_user_dir() / self.template_dir
        self.source_template_dir = get_source_dir() / template_dir
        self.match_threshold = match_threshold
        self.templates: dict[str, np.ndarray] = {}
        self.gray_templates: dict[str, np.ndarray] = {}
        self.current_scene = "未知"
        self.last_confidence = 0.0
        self._load_templates()

    def _load_templates(self):
        """加载场景模板图片。"""
        self.template_dir.mkdir(parents=True, exist_ok=True)
        dirs = []
        if self.source_template_dir.exists():
            dirs.append(self.source_template_dir)
        if self.template_dir.exists():
            dirs.append(self.template_dir)

        for directory in dirs:
            for filename in os.listdir(directory):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    scene_name = os.path.splitext(filename)[0]
                    path = directory / filename
                    template = cv2.imread(str(path))
                    if template is not None:
                        self.templates[scene_name] = template
                        self.gray_templates[scene_name] = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    def add_template(self, name: str, image: np.ndarray):
        """动态添加场景模板。"""
        self.templates[name] = image
        self.gray_templates[name] = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        path = self.template_dir / f"{name}.png"
        cv2.imwrite(str(path), image)

    def detect(self, screenshot: np.ndarray) -> Tuple[str, float]:
        """检测当前场景，返回 (场景名, 置信度)。"""
        if screenshot is None or not self.templates:
            return "未知", 0.0

        gray_screen = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        best_name, best_score, best_conf = "未知", 0.0, 0.0

        for name, gray_tmpl in self.gray_templates.items():
            h, w = gray_tmpl.shape

            if h > gray_screen.shape[0] or w > gray_screen.shape[1]:
                continue

            res = cv2.matchTemplate(gray_screen, gray_tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            # 综合评分 = 最高匹配度 * 匹配区域面积比
            area_ratio = (w * h) / (gray_screen.shape[0] * gray_screen.shape[1])
            score = max_val * (1.0 + area_ratio)

            if score > best_score and max_val >= self.match_threshold:
                best_score = score
                best_name = name
                best_conf = max_val

        self.current_scene = best_name
        self.last_confidence = best_conf
        return best_name, best_conf

    def is_scene(self, name: str, screenshot: np.ndarray) -> bool:
        """检查是否处于指定场景。"""
        detected, conf = self.detect(screenshot)
        return detected == name

    @property
    def scene(self) -> str:
        return self.current_scene

    @property
    def confidence(self) -> float:
        return self.last_confidence

"""轻量动作脚本执行器。

借鉴 genshin_autoplay_domain 的 YAML 动作脚本思想，但保持本项目低依赖：
只复用现有截图、点击、热键、OCR/模板接口，不引入新的自动化框架。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import yaml


class ActionScriptError(RuntimeError):
    pass


class ActionScriptRunner:
    """执行 YAML 描述的动作序列。

    ctx 约定：
      - click(x, y, **kwargs) -> bool
      - input_hotkey(*keys)
      - capture(region=None)
      - template_match(image, template_name, category="")
      - ocr(image) -> list
      - log(text, level="info") 可选
    """

    def __init__(self, ctx: dict[str, Any]):
        self.ctx = ctx

    def run_file(self, path: str | Path) -> bool:
        with open(path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f) or {}
        return self.run(spec)

    def run(self, spec: dict[str, Any] | list[dict[str, Any]]) -> bool:
        steps = spec.get("steps", spec) if isinstance(spec, dict) else spec
        if not isinstance(steps, list):
            raise ActionScriptError("动作脚本必须是 steps 列表")
        for step in steps:
            if not self._run_step(step or {}):
                return False
        return True

    def _run_step(self, step: dict[str, Any]) -> bool:
        action = step.get("action") or step.get("type")
        if not action:
            raise ActionScriptError(f"缺少 action/type: {step}")

        if action == "wait":
            time.sleep(float(step.get("seconds", step.get("duration", 0.5))))
            return True

        if action == "click":
            return self._click(step)

        if action in ("hotkey", "key"):
            return self._hotkey(step)

        if action == "until_template":
            return self._until(step, self._check_template)

        if action == "ocr_contains":
            return self._until(step, self._check_ocr_contains)

        if action == "log":
            self._log(str(step.get("message", "")), step.get("level", "info"))
            return True

        raise ActionScriptError(f"不支持的动作: {action}")

    def _click(self, step: dict[str, Any]) -> bool:
        click = self._required("click")
        pos = step.get("pos") or step.get("point")
        if not pos or len(pos) != 2:
            raise ActionScriptError(f"click 需要 pos: [x, y]: {step}")
        kwargs = {
            "variance": int(step.get("variance", 5)),
            "move_away": bool(step.get("move_away", True)),
        }
        if "button" in step:
            kwargs["button"] = step["button"]
        return bool(click(int(pos[0]), int(pos[1]), **kwargs))

    def _hotkey(self, step: dict[str, Any]) -> bool:
        hotkey = self._required("input_hotkey")
        keys = step.get("keys")
        if isinstance(keys, str):
            keys = [keys]
        if not keys:
            raise ActionScriptError(f"hotkey/key 需要 keys: {step}")
        hotkey(*keys)
        return True

    def _until(self, step: dict[str, Any], checker: Callable[[dict[str, Any]], bool]) -> bool:
        timeout = float(step.get("timeout", 5.0))
        interval = float(step.get("interval", 0.3))
        deadline = time.time() + timeout
        while time.time() <= deadline:
            if checker(step):
                return True
            time.sleep(interval)
        return False

    def _check_template(self, step: dict[str, Any]) -> bool:
        capture = self._required("capture")
        match = self._required("template_match")
        image = capture(step.get("region"))
        if image is None:
            return False
        template = step.get("template")
        if not template:
            raise ActionScriptError(f"until_template 需要 template: {step}")
        result = match(image, template, step.get("category", ""))
        if not result:
            return False
        if step.get("click", False):
            click = self._required("click")
            cx, cy = self._match_center(result)
            region = step.get("region")
            if region:
                cx += int(region[0])
                cy += int(region[1])
            return bool(click(cx, cy, variance=int(step.get("variance", 3))))
        return True

    @staticmethod
    def _match_center(result) -> tuple[int, int]:
        if isinstance(result, dict):
            if "center" in result:
                return int(result["center"][0]), int(result["center"][1])
            if "bbox" in result:
                x, y, w, h = result["bbox"]
                return int(x + w / 2), int(y + h / 2)
        if isinstance(result, (list, tuple)) and len(result) >= 2:
            return int(result[0]), int(result[1])
        raise ActionScriptError(f"无法从模板匹配结果计算中心点: {result}")

    def _check_ocr_contains(self, step: dict[str, Any]) -> bool:
        capture = self._required("capture")
        ocr = self._required("ocr")
        text = str(step.get("text", ""))
        if not text:
            raise ActionScriptError(f"ocr_contains 需要 text: {step}")
        image = capture(step.get("region"))
        if image is None:
            return False
        lines = ocr(image) or []
        joined = "\n".join(str(item) for item in lines)
        return text in joined

    def _required(self, name: str):
        value = self.ctx.get(name)
        if value is None:
            raise ActionScriptError(f"上下文缺少 {name}")
        return value

    def _log(self, message: str, level: str = "info") -> None:
        logger = self.ctx.get("log")
        if logger:
            logger(message, level)


def run_action_script(path: str | Path, ctx: dict[str, Any]) -> bool:
    return ActionScriptRunner(ctx).run_file(path)

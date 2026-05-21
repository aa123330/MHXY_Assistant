"""AI 模型抽象层 — 可插拔的多模型接口。

支持的模型提供商:
  - OpenAI (GPT-4V / GPT-4o)
  - Anthropic (Claude)
  - Ollama (本地模型)
  - 自定义 HTTP API

使用方式:
  from core.ai_model import create_ai_model

  model = create_ai_model(config["ai"])
  result = model.analyze_screenshot(image, "识别这张图中的NPC和按钮")
  suggestions = model.suggest_labels(image, existing_classes=["npc", "monster"])
"""

import json
import base64
import os
import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import numpy as np

from .paths import get_user_dir
PROJECT_DIR = get_user_dir()


# ==================== 抽象基类 ====================

class BaseAIModel(ABC):
    """AI 模型抽象基类。所有模型实现需继承此类。"""

    name: str = "base"
    supports_vision: bool = False

    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        """发送文本对话，返回回复文本。"""
        ...

    def analyze_image(self, image, prompt: str) -> str:
        """分析图像（视觉模型）。默认转 base64 后调用 _vision_chat。"""
        if not self.supports_vision:
            raise NotImplementedError(f"{self.name} 不支持视觉分析")

        if isinstance(image, np.ndarray):
            import cv2
            _, buf = cv2.imencode(".jpg", image)
            b64 = base64.b64encode(buf).decode()
        elif isinstance(image, (str, Path)):
            path = Path(image)
            if path.exists():
                b64 = base64.b64encode(path.read_bytes()).decode()
            else:
                raise FileNotFoundError(f"图片不存在: {image}")
        elif isinstance(image, bytes):
            b64 = base64.b64encode(image).decode()
        else:
            raise TypeError(f"不支持的图片类型: {type(image)}")

        return self._vision_chat(b64, prompt)

    def _vision_chat(self, image_b64: str, prompt: str) -> str:
        """视觉对话实现，子类重写。"""
        raise NotImplementedError

    # ---------- 训练辅助 ----------

    def suggest_labels(
        self, image, existing_classes: list[str] = None
    ) -> dict:
        """分析截图，建议标注目标和类别。

        返回格式:
        {
            "suggested_classes": ["npc", "monster", "button", ...],
            "detected_objects": [
                {"class": "npc", "description": "NPC 观音姐姐", "location": "画面中央偏左"},
                {"class": "button", "description": "攻击按钮", "location": "右下角"},
            ],
            "advice": "建议添加 'portal' 类用于传送门..."
        }
        """
        if not self.supports_vision:
            return {"error": f"{self.name} 不支持视觉分析"}

        existing = ", ".join(existing_classes) if existing_classes else "未定义"
        prompt = f"""你是一个游戏自动化训练数据标注专家。请分析这张梦幻西游游戏截图。

当前已有的标注类别: [{existing}]

请完成以下任务:
1. 识别图中所有值得标注的 UI 元素、NPC、怪物、按钮等
2. 建议新增哪些类别（如当前类别不足以覆盖）
3. 描述每个检测到的目标的大致位置

请以 JSON 格式返回，格式如下:
{{
  "suggested_classes": ["类1", "类2", ...],
  "detected_objects": [
    {{"class": "类名", "description": "描述", "location": "位置描述"}}
  ],
  "advice": "训练建议"
}}

只返回 JSON，不要其他内容。"""

        try:
            resp = self.analyze_image(image, prompt)
            # 提取 JSON
            resp = resp.strip()
            if resp.startswith("```"):
                resp = resp.split("\n", 1)[1]
                if resp.endswith("```"):
                    resp = resp[:-3]
            return json.loads(resp)
        except Exception as e:
            return {"error": str(e), "raw": resp if 'resp' in dir() else ""}

    def validate_labels(
        self, image, labels: list[str]
    ) -> dict:
        """验证标注质量：检查一张图的标签是否合理。

        返回:
        {
            "valid": true/false,
            "issues": ["问题1", "问题2"],
            "suggestions": ["建议1"],
            "confidence": 0.85
        }
        """
        if not self.supports_vision:
            return {"error": f"{self.name} 不支持视觉分析"}

        labels_text = ", ".join(labels)
        prompt = f"""你是标注质量审核专家。请审核这张梦幻西游截图的标注质量。

当前标注的目标类别: [{labels_text}]

请判断:
1. 标注是否合理（是否有明显漏标或错标）
2. 类别名称是否清晰
3. 是否有改进建议

以 JSON 返回:
{{"valid": true/false, "issues": ["问题描述"], "suggestions": ["改进建议"], "confidence": 0.0-1.0}}
只返回 JSON。"""

        try:
            resp = self.analyze_image(image, prompt)
            resp = resp.strip()
            if resp.startswith("```"):
                resp = resp.split("\n", 1)[1]
                if resp.endswith("```"):
                    resp = resp[:-3]
            return json.loads(resp)
        except Exception as e:
            return {"error": str(e)}

    def auto_describe_dataset(
        self, screenshot_paths: list[str], existing_classes: list[str] = None
    ) -> dict:
        """批量分析截图，生成数据集优化建议。"""
        if not screenshot_paths:
            return {"error": "无截图"}

        # 抽样分析（太多会慢）
        sample = screenshot_paths[:5] if len(screenshot_paths) > 5 else screenshot_paths

        results = []
        for path in sample:
            try:
                r = self.suggest_labels(path, existing_classes)
                results.append({"path": str(path), "result": r})
            except Exception as e:
                results.append({"path": str(path), "error": str(e)})

        # 汇总
        all_classes = set(existing_classes or [])
        for r in results:
            if "suggested_classes" in r.get("result", {}):
                all_classes.update(r["result"]["suggested_classes"])

        return {
            "analyzed": len(sample),
            "total": len(screenshot_paths),
            "merged_classes": sorted(all_classes),
            "details": results,
        }


# ==================== OpenAI 实现 ====================

class OpenAIModel(BaseAIModel):
    name = "openai"
    supports_vision = True

    def __init__(self, api_key: str, model: str = "gpt-4o",
                 base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def chat(self, messages: list[dict]) -> str:
        import urllib.request
        import urllib.error

        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"OpenAI API 错误 ({e.code}): {e.read().decode()}")

    def _vision_chat(self, image_b64: str, prompt: str) -> str:
        return self.chat([{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }])


# ==================== Anthropic 实现 ====================

class ClaudeModel(BaseAIModel):
    name = "claude"
    supports_vision = True

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        import urllib.request
        import urllib.error

        # 转换消息格式为 Anthropic 格式
        system = ""
        anthropic_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                anthropic_msgs.append({"role": m["role"], "content": m["content"]})

        body = json.dumps({
            "model": self.model,
            "messages": anthropic_msgs,
            "system": system,
            "max_tokens": 4096,
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["content"][0]["text"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Anthropic API 错误 ({e.code}): {e.read().decode()}")

    def _vision_chat(self, image_b64: str, prompt: str) -> str:
        return self.chat([{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_b64,
                }},
                {"type": "text", "text": prompt},
            ],
        }])


# ==================== Ollama 本地模型 ====================

class OllamaModel(BaseAIModel):
    name = "ollama"
    supports_vision = True

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "llama3.2-vision"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        import urllib.request
        import urllib.error

        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["message"]["content"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama 错误 ({e.code}): {e.read().decode()}")

    def _vision_chat(self, image_b64: str, prompt: str) -> str:
        return self.chat([{
            "role": "user",
            "content": prompt,
            "images": [image_b64],
        }])


# ==================== Mock 模型（测试用） ====================

class MockModel(BaseAIModel):
    """Mock 模型，用于测试，不调用任何 API。"""

    name = "mock"
    supports_vision = True

    def chat(self, messages: list[dict]) -> str:
        return json.dumps({"message": "Mock response", "echo": str(messages)[:200]})

    def _vision_chat(self, image_b64: str, prompt: str) -> str:
        return json.dumps({
            "suggested_classes": ["npc", "monster", "button"],
            "detected_objects": [
                {"class": "npc", "description": "疑似NPC", "location": "中央"},
                {"class": "button", "description": "疑似按钮", "location": "右下"},
            ],
            "advice": "请用 labelImg 标注后开始训练",
        })


# ==================== 工厂函数 ====================

def create_ai_model(config: dict) -> Optional[BaseAIModel]:
    """根据配置创建 AI 模型实例。

    配置示例:
      ai:
        provider: "openai"      # openai / anthropic / ollama / custom / mock
        enabled: true
        openai:
          api_key: "sk-xxx"     # 或 ${OPENAI_API_KEY}
          model: "gpt-4o"
          base_url: "https://api.openai.com/v1"
        anthropic:
          api_key: "sk-ant-xxx"
          model: "claude-sonnet-4-6"
        ollama:
          base_url: "http://localhost:11434"
          model: "llama3.2-vision"
        custom:
          endpoint: "https://your-api.com/v1/chat"
          api_key: "xxx"
          model: "your-model"
    """
    if not config or not config.get("enabled", False):
        return None

    provider = config.get("provider", "openai").lower()

    def _resolve_key(value: str) -> str:
        """解析 ${ENV_VAR} 格式的 API key。"""
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, "")
        return value or ""

    try:
        if provider == "openai":
            cfg = config.get("openai", {})
            api_key = _resolve_key(cfg.get("api_key", ""))
            return OpenAIModel(
                api_key=api_key,
                model=cfg.get("model", "gpt-4o"),
                base_url=cfg.get("base_url", "https://api.openai.com/v1"),
            )

        elif provider == "anthropic":
            cfg = config.get("anthropic", {})
            api_key = _resolve_key(cfg.get("api_key", ""))
            return ClaudeModel(
                api_key=api_key,
                model=cfg.get("model", "claude-sonnet-4-6"),
            )

        elif provider == "ollama":
            cfg = config.get("ollama", {})
            return OllamaModel(
                base_url=cfg.get("base_url", "http://localhost:11434"),
                model=cfg.get("model", "llama3.2-vision"),
            )

        elif provider == "mock":
            return MockModel()

        elif provider == "custom":
            cfg = config.get("custom", {})
            # 通用 OpenAI 兼容 API
            api_key = _resolve_key(cfg.get("api_key", ""))
            return OpenAIModel(
                api_key=api_key,
                model=cfg.get("model", ""),
                base_url=cfg.get("endpoint", ""),
            )

    except Exception as e:
        print(f"AI 模型初始化失败 ({provider}): {e}")
        return None

    return None


# ==================== 便捷函数 ====================

def encode_image(image) -> str:
    """将 numpy 数组或文件路径编码为 base64。"""
    if isinstance(image, np.ndarray):
        import cv2
        _, buf = cv2.imencode(".jpg", image)
        return base64.b64encode(buf).decode()
    elif isinstance(image, (str, Path)):
        return base64.b64encode(Path(image).read_bytes()).decode()
    elif isinstance(image, bytes):
        return base64.b64encode(image).decode()
    raise TypeError(f"不支持的类型: {type(image)}")

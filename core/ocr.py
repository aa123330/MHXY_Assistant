"""OCR 识别：基于 PaddleOCR 的中文文字识别封装。"""

import time
import numpy as np
from typing import Optional

try:
    from paddleocr import PaddleOCR
    HAS_PADDLE = True
except ImportError:
    HAS_PADDLE = False
    PaddleOCR = None

_ocr: Optional["PaddleOCR"] = None


def get_ocr(lang: str = "ch", use_angle_cls: bool = True):
    """获取 OCR 实例（懒加载）。"""
    if not HAS_PADDLE:
        raise ImportError("PaddleOCR 未安装，OCR 功能不可用")
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(lang=lang, use_angle_cls=use_angle_cls)
    return _ocr


def ocr_region(image: np.ndarray, confidence: float = 0.7) -> list[dict]:
    """对给定图像区域做 OCR，返回 [{text, confidence, bbox}, ...]。

    兼容 PaddleOCR 2.x (ocr.ocr) 和 3.x (ocr.predict)。
    """
    ocr = get_ocr()

    # PaddleOCR 2.x: ocr.ocr(image, cls=True) 返回 [[[bbox, (text, conf)], ...]]
    # PaddleOCR 3.x: ocr.ocr(image) 内部调用 predict(image)，不接受 cls 参数
    try:
        results = ocr.ocr(image, cls=True)
    except TypeError:
        results = ocr.ocr(image)

    if not results or not results[0]:
        return []
    items = []
    for line in results[0]:
        bbox, (text, conf) = line
        if conf >= confidence:
            items.append({
                "text": text,
                "confidence": conf,
                "bbox": (
                    int(bbox[0][0]), int(bbox[0][1]),
                    int(bbox[2][0]), int(bbox[2][1]),
                ),
            })
    return items


def find_text(
    image: np.ndarray,
    target: str,
    confidence: float = 0.7,
) -> Optional[tuple[str, tuple[int, int, int, int], float]]:
    """在图像中查找特定文字，返回 (text, bbox, confidence) 或 None。"""
    for item in ocr_region(image, confidence):
        if target in item["text"]:
            return item["text"], item["bbox"], item["confidence"]
    return None


def wait_text(
    capture_fn,
    target: str,
    region: tuple[int, int, int, int],
    timeout: float = 10.0,
    interval: float = 0.5,
    confidence: float = 0.7,
) -> Optional[dict]:
    """轮询等待指定文字出现（用于等待对话框加载等），超时返回 None。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        img = capture_fn(region)
        result = find_text(img, target, confidence)
        if result:
            return {"text": result[0], "bbox": result[1], "confidence": result[2]}
        time.sleep(interval)
    return None


def get_text_center(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
    """根据 OCR bbox 返回文字中心坐标。"""
    return (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2

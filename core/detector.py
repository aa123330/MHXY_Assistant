"""YOLOv8 目标检测：用于检测游戏中的 UI 元素、NPC、怪物、按钮等。"""

from __future__ import annotations

import os
import time
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, TYPE_CHECKING

try:
    from ultralytics import YOLO
    import torch
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    YOLO = None  # type: ignore
    torch = None


class YOLODetector:
    """YOLOv8 游戏元素检测器。

    用于替代纯模板匹配，能更鲁棒地检测 NPC、按钮、怪物等动态元素。
    """

    def __init__(
        self,
        model_path: str = "yolo_dataset/runs/detect/train/weights/best.pt",
        conf_threshold: float = 0.5,
        device: str = "cuda",
    ):
        if not HAS_YOLO:
            raise ImportError("ultralytics 未安装，请执行: pip install ultralytics torch")

        self.conf_threshold = conf_threshold
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = self._load_model(model_path)
        self.class_names = self.model.names if hasattr(self.model, "names") else {}

    def _load_model(self, model_path: str) -> YOLO:
        """加载 YOLO 模型。"""
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"YOLO 模型未找到: {model_path}\n"
                "请先训练模型或从 menghuanxiyou 项目复制模型文件。"
            )
        model = YOLO(model_path)
        # 预热
        dummy = np.zeros((256, 640, 3), dtype=np.uint8)
        _ = model(dummy, device=self.device, verbose=False)
        return model

    def detect(self, image: np.ndarray) -> List[Dict]:
        """对图像进行目标检测，返回检测结果列表。

        每个结果包含:
            class_id: 类别 ID
            class_name: 类别名称
            confidence: 置信度
            bbox: (x, y, w, h) 边界框
            center: (cx, cy) 中心坐标
        """
        results = self.model(image, conf=self.conf_threshold, device=self.device, verbose=False)
        detections = []

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if conf < self.conf_threshold:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                w, h = x2 - x1, y2 - y1
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                class_name = self.class_names.get(cls_id, f"class_{cls_id}")

                detections.append({
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox": (x1, y1, w, h),
                    "center": (cx, cy),
                })

        return detections

    def find_class(
        self, image: np.ndarray, class_id: int, min_conf: float = 0.0
    ) -> Optional[Dict]:
        """查找特定类别的第一个检测结果。"""
        conf = max(min_conf, self.conf_threshold)
        detections = self.detect(image)
        for d in detections:
            if d["class_id"] == class_id and d["confidence"] >= conf:
                return d
        return None

    def find_class_name(
        self, image: np.ndarray, class_name: str, min_conf: float = 0.0
    ) -> Optional[Dict]:
        """按类别名称查找。"""
        conf = max(min_conf, self.conf_threshold)
        detections = self.detect(image)
        for d in detections:
            if d["class_name"] == class_name and d["confidence"] >= conf:
                return d
        return None

    def has_class(self, image: np.ndarray, class_id: int) -> bool:
        """检查图像中是否存在指定类别。"""
        return self.find_class(image, class_id) is not None

    def draw_boxes(self, image: np.ndarray, detections: List[Dict] = None) -> np.ndarray:
        """在图像上绘制检测框（调试用）。"""
        if detections is None:
            detections = self.detect(image)
        vis = image.copy()
        for d in detections:
            x1, y1, w, h = d["bbox"]
            x2, y2 = x1 + w, y1 + h
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{d['class_name']} ({d['confidence']:.2f})"
            cv2.putText(vis, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return vis


class YOLODetectionWindow:
    """实时 YOLO 检测预览窗口（调试用）。按 Q 或关闭窗口退出。"""

    def __init__(self, detector: YOLODetector, capture_fn):
        self.detector = detector
        self.capture = capture_fn
        self.running = False
        self._window_name = "YOLO Detection"

    def start(self, window_name: str = "YOLO Detection"):
        """启动实时检测预览。"""
        self._window_name = window_name
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        self.running = True
        print(f"YOLO 检测预览已启动，按 Q 或关闭窗口退出...")

        while self.running:
            frame = self.capture()
            if frame is None:
                time.sleep(0.1)
                continue

            detections = self.detector.detect(frame)
            vis = self.detector.draw_boxes(frame, detections)
            cv2.imshow(window_name, vis)

            key = cv2.waitKey(1) & 0xFF
            # 按 Q 退出
            if key == ord("q"):
                break
            # 点击 X 关闭窗口退出
            try:
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break

        self.stop()

    def stop(self):
        """停止预览并关闭窗口。"""
        self.running = False
        try:
            cv2.destroyWindow(self._window_name)
        except cv2.error:
            pass

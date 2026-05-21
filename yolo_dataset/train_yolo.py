#!/usr/bin/env python3
"""YOLO 模型训练脚本。

用法:
  # 从零开始训练（使用预训练权重）
  python train_yolo.py --base yolov8s.pt --epochs 100

  # 继续训练已有模型
  python train_yolo.py --base runs/detect/train/weights/last.pt --epochs 50

  # 验证模型
  python train_yolo.py --val runs/detect/train/weights/best.pt

数据集准备:
  1. 采集游戏截图放到 yolo_dataset/images/train/
  2. 用标注工具（labelImg / CVAT）标注后导出 YOLO 格式
  3. 标注文件(.txt)放到 yolo_dataset/labels/train/
  4. 更新 data.yaml 中的类别名称
"""

import argparse
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    print("请先安装 ultralytics: pip install ultralytics")
    sys.exit(1)


if getattr(sys, 'frozen', False):
    DATA_DIR = Path(sys._MEIPASS) / "yolo_dataset"
else:
    DATA_DIR = Path(__file__).parent


def train(base_model: str, epochs: int, batch: int, imgsz: int, name: str):
    """训练 YOLO 模型。"""
    data_yaml = str(DATA_DIR / "data.yaml")

    print(f"数据集: {data_yaml}")
    print(f"基础模型: {base_model}")
    print(f"训练轮数: {epochs}, batch: {batch}, 图像尺寸: {imgsz}")

    model = YOLO(base_model)

    model.train(
        data=data_yaml,
        device=0,                # GPU 0（CPU 则设为 'cpu'）
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        augment=True,            # 数据增强
        multi_scale=True,        # 多尺度训练
        lr0=0.001,
        name=name,
        project=str(DATA_DIR / "runs" / "detect"),
    )

    # 验证
    best_pt = DATA_DIR / "runs" / "detect" / name / "weights" / "best.pt"
    print(f"\n训练完成！最佳模型: {best_pt}")
    print(f"更新 config.yaml 中 yolo.model_path 为: {best_pt}")
    return best_pt


def validate(model_path: str):
    """验证模型在验证集上的表现。"""
    model = YOLO(model_path)
    data_yaml = str(DATA_DIR / "data.yaml")
    metrics = model.val(data=data_yaml)
    print(f"\n验证结果: mAP50={metrics.box.map50:.3f}, mAP50-95={metrics.box.map:.3f}")
    return metrics


def predict(model_path: str, image_dir: str):
    """用模型对一组图片做推理，保存结果。"""
    model = YOLO(model_path)
    results = model.predict(
        source=image_dir,
        save=True,
        conf=0.5,
        project=str(DATA_DIR / "runs" / "predict"),
    )
    print(f"推理完成，结果保存在 runs/predict/")


def main():
    parser = argparse.ArgumentParser(description="YOLO 模型训练与验证")
    parser.add_argument("--base", default="yolov8s.pt",
                       help="基础模型 (yolov8n.pt / yolov8s.pt / 已有模型路径)")
    parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    parser.add_argument("--batch", type=int, default=8, help="批大小")
    parser.add_argument("--imgsz", type=int, default=640, help="图像尺寸")
    parser.add_argument("--name", default="mhxy_train", help="训练任务名称")
    parser.add_argument("--val", action="store_true", help="仅验证不训练")
    parser.add_argument("--predict", help="对指定目录做推理")
    args = parser.parse_args()

    if args.val:
        validate(args.base)
    elif args.predict:
        predict(args.base, args.predict)
    else:
        train(args.base, args.epochs, args.batch, args.imgsz, args.name)


if __name__ == "__main__":
    main()

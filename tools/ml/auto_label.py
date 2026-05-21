# 标注辅助工具：用现有模型做自动标注，人工修正后加入训练集
"""自动标注脚本 — 用已有模型检测新截图，生成 YOLO 格式标注。

用法:
  python tools/ml/auto_label.py --model path/to/best.pt --images debug/screenshots

输出:
  tools/ml/labels/auto/  — 自动生成的标注文件
  tools/ml/images/auto/  — 对应的图片（软链接）
"""

import argparse
import sys
from pathlib import Path
import cv2

try:
    from ultralytics import YOLO
except ImportError:
    print("请先安装 ultralytics: pip install ultralytics")
    sys.exit(1)

DATA_DIR = Path(__file__).parent


def auto_label(model_path: str, image_dir: str, conf: float = 0.5):
    """用模型检测图片并生成 YOLO 标注。"""
    model = YOLO(model_path)
    image_dir = Path(image_dir)
    out_label_dir = DATA_DIR / "labels" / "auto"
    out_label_dir.mkdir(parents=True, exist_ok=True)

    for img_path in image_dir.glob("*"):
        if not img_path.suffix.lower() in (".png", ".jpg", ".jpeg"):
            continue

        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]
        results = model(img, conf=conf, verbose=False)

        labels = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                # YOLO 格式: class cx cy w h (归一化)
                cx = ((x1 + x2) / 2) / w
                cy = ((y1 + y2) / 2) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                labels.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        label_path = out_label_dir / f"{img_path.stem}.txt"
        label_path.write_text("\n".join(labels))
        print(f"{img_path.name}: {len(labels)} 个目标")

    print(f"\n标注完成！输出目录: {out_label_dir}")
    print("请人工检查修正后移动到 tools/ml/labels/train/")


def main():
    parser = argparse.ArgumentParser(description="自动标注工具")
    parser.add_argument("--model", required=True, help="YOLO 模型路径")
    parser.add_argument("--images", required=True, help="待标注图片目录")
    parser.add_argument("--conf", type=float, default=0.5, help="置信度阈值")
    args = parser.parse_args()
    auto_label(args.model, args.images, args.conf)


if __name__ == "__main__":
    main()

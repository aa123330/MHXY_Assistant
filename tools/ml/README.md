# ML Tooling

This folder is only for training and auto-labeling. Runtime YOLO inference in the WPF app uses ONNX Runtime and does not load `.pt` files.

Generated folders are ignored by git:

- `images/`
- `labels/`
- `runs/`
- `models/`

Typical command:

```powershell
python tools/ml/train_yolo.py --base yolov8n.pt --epochs 100 --device cpu
```

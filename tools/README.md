# Optional Tools

This directory contains optional Python utilities. They are not part of the .NET/WPF runtime and are not required to start `MHXY_Assistant.exe`.

## Directories

- `ml/`: YOLO training and auto-labeling helpers.
- `cloud-server/`: local Flask file service compatible with the WPF cloud window.

## ML Setup

```powershell
py -3.12 -m venv .venv-ml
.\.venv-ml\Scripts\Activate.ps1
pip install -r tools/ml/requirements.txt
```

Train:

```powershell
python tools/ml/train_yolo.py --base yolov8n.pt --epochs 100 --device cpu
```

Auto-label:

```powershell
python tools/ml/auto_label.py --model tools/ml/runs/detect/mhxy_train/weights/best.pt --images debug/screenshots --conf 0.5
```

Export the trained `.pt` model to ONNX before using it in the WPF runtime, then place it under `models/yolo/best.onnx` or update `config.yaml`.

## Cloud Server

```powershell
pip install -r tools/cloud-server/requirements.txt
python tools/cloud-server/train_server.py --port 9527
```

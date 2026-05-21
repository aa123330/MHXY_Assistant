"""
云端数据存储服务 — 数据集和模型的上传/下载/列表。

用法:
  pip install flask
  python train_server.py --port 9527

API:
  POST /api/upload          上传文件
  GET  /api/list            列出所有文件
  GET  /api/download/<name> 下载文件
  DELETE /api/delete/<name> 删除文件
  GET  /api/health          健康检查
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

DATA_DIR = Path("cloud_storage")
DATA_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "files": len(list(DATA_DIR.iterdir()))})


@app.route("/api/upload", methods=["POST"])
def upload():
    """上传文件（数据集 zip 或模型 .pt）。"""
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no file"}), 400

    file = request.files["file"]
    name = request.form.get("name", file.filename)
    if not name:
        name = file.filename
    if not name:
        return jsonify({"ok": False, "error": "no filename"}), 400

    save_path = DATA_DIR / name
    file.save(str(save_path))
    size_mb = round(save_path.stat().st_size / 1024 / 1024, 2)

    return jsonify({
        "ok": True,
        "name": name,
        "size_mb": size_mb,
        "path": str(save_path),
    })


@app.route("/api/list", methods=["GET"])
def list_files():
    """列出所有存储的文件。"""
    files = []
    for f in sorted(DATA_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file():
            files.append({
                "name": f.name,
                "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
                "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return jsonify({"files": files})


@app.route("/api/download/<name>", methods=["GET"])
def download(name):
    """下载文件。"""
    path = DATA_DIR / name
    if not path.exists():
        return jsonify({"ok": False, "error": "file not found"}), 404
    return send_file(str(path), as_attachment=True, download_name=name)


@app.route("/api/delete/<name>", methods=["DELETE"])
def delete(name):
    """删除文件。"""
    path = DATA_DIR / name
    if not path.exists():
        return jsonify({"ok": False, "error": "file not found"}), 404
    path.unlink()
    return jsonify({"ok": True})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9527)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    print(f"Storage server: http://{args.host}:{args.port}")
    print(f"Data dir: {DATA_DIR.absolute()}")
    app.run(host=args.host, port=args.port, debug=False)

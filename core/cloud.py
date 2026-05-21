"""云端存储客户端 — 数据集和模型的上传/下载。

用法:
  from core.cloud import CloudStorage

  cloud = CloudStorage("http://your-server:9527")
  cloud.upload("path/to/file.zip", "my_dataset.zip")
  cloud.list_files()
  cloud.download("my_model.pt", "local/path/")
"""

import json
import time
import shutil
import tempfile
import os
from pathlib import Path
from typing import Optional, Callable


class CloudStorage:
    """云端文件存储客户端。"""

    def __init__(self, server_url: str):
        self.server = server_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.server}{path}"

    def _get(self, path: str) -> dict:
        import urllib.request, urllib.error
        try:
            with urllib.request.urlopen(self._url(path), timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _post(self, path: str, filename: str, content: bytes,
              extra_fields: dict = None) -> dict:
        import urllib.request, urllib.error

        boundary = "----CloudBoundary"
        body = b""
        if extra_fields:
            for k, v in extra_fields.items():
                body += f"--{boundary}\r\n".encode()
                body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
                body += str(v).encode()
                body += b"\r\n"

        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: application/octet-stream\r\n\r\n"
        body += content
        body += f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            self._url(path), data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _delete(self, path: str) -> dict:
        import urllib.request, urllib.error
        req = urllib.request.Request(self._url(path), method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ====== API ======

    def check_health(self) -> dict:
        return self._get("/api/health")

    def list_files(self) -> list[dict]:
        """列出服务器上所有文件。"""
        return self._get("/api/list").get("files", [])

    def upload(self, local_path: str, remote_name: str = None,
               progress_cb: Callable = None) -> dict:
        """上传文件到服务器。

        local_path: 本地文件路径
        remote_name: 服务器上的文件名（默认用本地文件名）
        """
        path = Path(local_path)
        if not path.exists():
            return {"ok": False, "error": f"File not found: {local_path}"}

        name = remote_name or path.name
        content = path.read_bytes()

        if progress_cb:
            progress_cb("uploading", 50)

        result = self._post("/api/upload", name, content)
        if progress_cb:
            progress_cb("done" if result.get("ok") else "error", 100)

        return result

    def upload_directory(self, dir_path: str, zip_name: str = None) -> dict:
        """打包目录并上传。"""
        dir_path = Path(dir_path)
        if not dir_path.exists():
            return {"ok": False, "error": f"Dir not found: {dir_path}"}

        name = zip_name or f"{dir_path.name}_{int(time.time())}.zip"

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            zip_path = tmp.name

        shutil.make_archive(zip_path.replace(".zip", ""), "zip", dir_path)

        result = self.upload(zip_path, name)
        os.unlink(zip_path)
        return result

    def download(self, remote_name: str, save_dir: str = None) -> Optional[str]:
        """下载文件到本地。返回本地文件路径。"""
        import urllib.request

        save_dir = Path(save_dir) if save_dir else Path(".")
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / remote_name

        url = self._url(f"/api/download/{remote_name}")
        try:
            urllib.request.urlretrieve(url, str(save_path))
            return str(save_path)
        except Exception as e:
            print(f"Download failed: {e}")
            return None

    def delete(self, remote_name: str) -> dict:
        return self._delete(f"/api/delete/{remote_name}")

    # ====== 便捷方法 ======

    def upload_dataset(self, dataset_dir: str) -> dict:
        """上传本地 yolo_dataset。"""
        name = f"dataset_{int(time.time())}.zip"
        return self.upload_directory(dataset_dir, name)

    def upload_model(self, model_path: str) -> dict:
        """上传训练好的模型。"""
        path = Path(model_path)
        name = path.name if path.suffix == ".pt" else f"{path.name}.pt"
        return self.upload(str(path), name)

    def list_datasets(self) -> list[dict]:
        return [f for f in self.list_files() if f["name"].startswith("dataset")]

    def list_models(self) -> list[dict]:
        return [f for f in self.list_files() if f["name"].endswith(".pt")]

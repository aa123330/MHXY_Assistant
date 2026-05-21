"""诊断包导出工具。

参考 BetterGI / Maa 系列项目的问题排查方式：把窗口信息、配置摘要、
截图样本和运行环境集中打包，方便定位截图、坐标、OCR/YOLO 等问题。
"""

from __future__ import annotations

import json
import platform
import time
import zipfile
from pathlib import Path
from typing import Any

from .paths import get_user_dir


SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "access_key",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(s in key_text for s in SENSITIVE_KEYS):
                result[key] = "***"
            else:
                result[key] = _redact(item)
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _json_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def _black_ratio(image) -> float | None:
    try:
        import numpy as np

        gray = image.mean(axis=2) if len(image.shape) == 3 else image
        return float(np.mean(gray < 5))
    except Exception:
        return None


def _encode_png(image) -> bytes | None:
    try:
        import cv2

        ok, buf = cv2.imencode(".png", image)
        return bytes(buf) if ok else None
    except Exception:
        return None


def _window_info(assistant) -> dict:
    info: dict[str, Any] = {
        "hwnd": getattr(assistant, "hwnd", None),
        "win_rect": getattr(assistant, "win_rect", None),
        "client_rect": getattr(assistant, "client_rect", None),
    }

    hwnd = info["hwnd"]
    if not hwnd:
        return info

    try:
        from . import window

        info.update(
            {
                "valid": window.is_window_valid(hwnd),
                "minimized": window.is_window_minimized(hwnd),
                "process": window.get_window_process_name(hwnd),
                "client_size": window.get_client_size(hwnd),
                "window_rect_now": window.get_window_rect(hwnd),
                "client_rect_now": window.get_client_rect(hwnd),
            }
        )
    except Exception as exc:
        info["error"] = str(exc)

    return info


def export_diagnostics(assistant, output_dir: str | Path | None = None) -> Path:
    """导出诊断包，返回 zip 路径。"""
    base = Path(output_dir) if output_dir else get_user_dir() / "debug" / "diagnostics"
    base.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    zip_path = base / f"diagnostics_{ts}.zip"

    config = _redact(getattr(assistant, "config", {}))
    window_info = _window_info(assistant)
    env = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "executable": platform.python_implementation(),
    }

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("config.redacted.json", _json_bytes(config))
        zf.writestr("window.json", _json_bytes(window_info))
        zf.writestr("environment.json", _json_bytes(env))

        try:
            img = assistant._capture()
            if img is not None:
                zf.writestr(
                    "capture_mss_info.json",
                    _json_bytes(
                        {
                            "shape": getattr(img, "shape", None),
                            "black_ratio": _black_ratio(img),
                        }
                    ),
                )
                png = _encode_png(img)
                if png:
                    zf.writestr("capture_mss.png", png)
        except Exception as exc:
            zf.writestr("capture_mss_error.txt", str(exc))

        try:
            from . import capture

            hwnd = getattr(assistant, "hwnd", None)
            if hwnd and hasattr(capture, "capture_window_client_bg"):
                bg = capture.capture_window_client_bg(hwnd)
                if bg is not None:
                    zf.writestr(
                        "capture_background_info.json",
                        _json_bytes(
                            {
                                "shape": getattr(bg, "shape", None),
                                "black_ratio": _black_ratio(bg),
                            }
                        ),
                    )
                    png = _encode_png(bg)
                    if png:
                        zf.writestr("capture_background.png", png)
        except Exception as exc:
            zf.writestr("capture_background_error.txt", str(exc))

    return zip_path

# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build used by the Windows installer.

This intentionally builds a folder instead of a single-file executable.  The
Paddle/PaddleOCR stack imports native libraries and Cython utility files at
runtime, and keeping those files on disk is much more reliable than unpacking a
multi-GB onefile bundle into a temporary _MEI directory.
"""

import os
import sys
import sysconfig
from pathlib import Path


PROJECT_DIR = Path(os.getcwd()).resolve()
VENDOR_DIR = PROJECT_DIR / "vendor"
PACKAGE_ML = os.environ.get("PACKAGE_ML", "1") != "0"

if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))
    for pth_file in VENDOR_DIR.glob("*.pth"):
        try:
            for line in pth_file.read_text(encoding="utf-8").splitlines():
                rel = line.strip()
                if rel and not rel.startswith("#"):
                    p = VENDOR_DIR / rel
                    if p.exists() and str(p) not in sys.path:
                        sys.path.insert(0, str(p))
        except Exception:
            pass

try:
    from PyInstaller.utils.hooks import (
        collect_data_files,
        collect_dynamic_libs,
        collect_submodules,
    )
except ImportError:
    def collect_submodules(_pkg):
        return []

    def collect_data_files(_pkg):
        return []

    def collect_dynamic_libs(_pkg):
        return []


def collect_many(fn, packages):
    items = []
    for pkg in packages:
        try:
            items += fn(pkg)
        except Exception:
            pass
    return items


def add_tree_if_exists(src: Path | str, dest: str):
    path = Path(src)
    if not path.is_absolute():
        path = PROJECT_DIR / path
    return [(str(path), dest)] if path.exists() else []


def add_file_if_exists(src: Path | str, dest: str):
    path = Path(src)
    if not path.is_absolute():
        path = PROJECT_DIR / path
    return [(str(path), dest)] if path.exists() else []


def add_tk_runtime():
    datas = []
    binaries = []
    stdlib_dir = Path(sysconfig.get_paths().get("stdlib", ""))
    tkinter_dir = stdlib_dir / "tkinter"
    datas += add_tree_if_exists(tkinter_dir, "tkinter")

    dll_dir = Path(sys.base_prefix) / "DLLs"
    for file_name in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll"):
        file_path = dll_dir / file_name
        if file_path.exists():
            binaries.append((str(file_path), "."))
    return datas, binaries


hidden_packages = [
    "cv2",
    "mss",
    "pynput",
    "pyautogui",
    "win32com",
]

data_packages = [
    "cv2",
    "mss",
    "pynput",
    "yaml",
    "PIL",
    "numpy",
    "pyautogui",
]

binary_packages = [
    "cv2",
    "numpy",
    "win32",
    "pywin32_system32",
]

if PACKAGE_ML:
    hidden_packages += [
        "ultralytics",
        "paddle",
        "paddleocr",
        "Cython",
    ]
    data_packages += [
        "torch",
        "torchvision",
        "ultralytics",
        "paddle",
        "paddleocr",
        "Cython",
    ]
    binary_packages += [
        "torch",
        "torchvision",
        "paddle",
        "paddleocr",
    ]

hiddenimports = [
    "base64",
    "ctypes",
    "json",
    "logging",
    "queue",
    "subprocess",
    "threading",
    "urllib",
    "cv2",
    "mss",
    "mss.windows",
    "numpy",
    "numpy.core._methods",
    "numpy.random",
    "PIL",
    "PIL.Image",
    "pynput",
    "pynput._util",
    "pynput.keyboard",
    "pynput.mouse",
    "pyautogui",
    "pythoncom",
    "pywintypes",
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.scrolledtext",
    "tkinter.ttk",
    "win32api",
    "win32con",
    "win32gui",
    "win32process",
    "win32ui",
    "yaml",
] + collect_many(collect_submodules, hidden_packages)

datas = []
datas += add_file_if_exists("config.yaml", ".")
datas += add_tree_if_exists("data", "data")
datas += add_tree_if_exists("tcl", "tcl")
_tk_datas, _tk_binaries = add_tk_runtime()
datas += _tk_datas

# Runtime YOLO assets only. Training images/labels are intentionally excluded so
# the installer carries the runnable app rather than the dataset used to train it.
for file_name in ("data.yaml", "menghuan_dataset.yaml"):
    datas += add_file_if_exists(Path("yolo_dataset") / file_name, "yolo_dataset")
for model_file in (PROJECT_DIR / "yolo_dataset").glob("yolov8*.pt"):
    datas += add_file_if_exists(model_file, "yolo_dataset")
for model_file in (PROJECT_DIR / "yolo_dataset" / "models").glob("*.pt"):
    datas += add_file_if_exists(model_file, str(Path("yolo_dataset") / "models"))
for weights_dir in (PROJECT_DIR / "yolo_dataset" / "runs").glob("detect/*/weights"):
    if weights_dir.exists():
        datas.append(
            (
                str(weights_dir),
                str(Path("yolo_dataset") / "runs" / "detect" / weights_dir.parent.name / "weights"),
            )
        )

datas += collect_many(collect_data_files, data_packages)

if PACKAGE_ML:
    # Paddle imports Cython utilities through paddle.utils.cpp_extension during
    # startup. Missing Cython/Utility/CppSupport.cpp caused the previous onefile
    # bundle to crash, so include this directory explicitly from any source that
    # exists in the current environment.
    datas += add_tree_if_exists(VENDOR_DIR / "Cython" / "Utility", "Cython/Utility")
    try:
        import Cython

        cython_utility = Path(Cython.__file__).resolve().parent / "Utility"
        datas += add_tree_if_exists(cython_utility, "Cython/Utility")
    except Exception:
        pass

binaries = collect_many(collect_dynamic_libs, binary_packages)
binaries += _tk_binaries

a = Analysis(
    ["bootstrap.py"],
    pathex=[str(PROJECT_DIR), str(VENDOR_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "jupyter",
        "matplotlib",
        "notebook",
        "numpy.tests",
        "pandas.tests",
        "PIL.ImageQt",
        "scipy",
        "setuptools.tests",
        "torch.testing",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MHXY_Assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/mhxy_icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MHXY_Assistant",
)

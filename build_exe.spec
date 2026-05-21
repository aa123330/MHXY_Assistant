# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — 打包为单个 exe

用法:
  pyinstaller build_exe.spec

输出:
  dist/梦幻西游AI辅助.exe
"""

import sys, os
from pathlib import Path

PROJECT_DIR = Path(os.getcwd())
VENDOR_DIR = PROJECT_DIR / "vendor"
PACKAGE_ML = os.environ.get("PACKAGE_ML", "0") != "0"
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

# PyInstaller 辅助：收集大型包的子模块、数据文件和动态库
try:
    from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs
except ImportError:
    def collect_submodules(pkg): return []
    def collect_data_files(pkg): return []
    def collect_dynamic_libs(pkg): return []

HIDDEN_PACKAGES = [
    "cv2",
    "mss",
    "pynput",
]

DATA_PACKAGES = [
    "cv2",
    "mss",
    "pynput",
    "yaml",
    "PIL",
    "numpy",
]

BINARY_PACKAGES = [
    "cv2",
    "numpy",
    "win32",
]

if PACKAGE_ML:
    HIDDEN_PACKAGES += ["ultralytics", "paddleocr"]
    DATA_PACKAGES += ["torch", "torchvision", "ultralytics", "paddle", "paddleocr", "Cython"]
    BINARY_PACKAGES += ["torch", "torchvision", "paddle", "paddleocr"]


def collect_many(fn, packages):
    items = []
    for pkg in packages:
        try:
            items += fn(pkg)
        except Exception:
            pass
    return items


def add_tree_if_exists(src: str, dest: str):
    path = PROJECT_DIR / src
    return [(str(path), dest)] if path.exists() else []


def add_file_if_exists(src: str, dest: str):
    path = PROJECT_DIR / src
    return [(str(path), dest)] if path.exists() else []


_hidden = collect_many(collect_submodules, HIDDEN_PACKAGES)
_data = collect_many(collect_data_files, DATA_PACKAGES)
_binaries = collect_many(collect_dynamic_libs, BINARY_PACKAGES)

excludes = [
    'matplotlib',
    'jupyter',
    'notebook',
    'numpy.tests',
    'numpy.core.tests',
    'numpy.f2py.tests',
    'numpy.lib.tests',
    'numpy.linalg.tests',
    'numpy.random.tests',
    'numpy.typing.tests',
    'PIL.ImageQt',
    'pandas.tests',
    'scipy',
]

if not PACKAGE_ML:
    excludes += [
        'Cython',
        'paddle',
        'paddleocr',
        'torch',
        'torchvision',
        'torchaudio',
        'ultralytics',
        'yolo_dataset.auto_label',
        'yolo_dataset.train_yolo',
    ]

# Paddle imports Cython utilities at runtime through cpp_extension. PyInstaller
# may miss these .cpp resources, causing FileNotFoundError for CppSupport.cpp.
if PACKAGE_ML:
    _data += add_tree_if_exists("vendor/Cython/Utility", "Cython/Utility")

_yolo_runtime_data = []
if PACKAGE_ML:
    # 运行版只打包必要的训练配置/默认权重，不打包 images/labels 训练集。
    for file_name in ("data.yaml", "menghuan_dataset.yaml"):
        _yolo_runtime_data += add_file_if_exists(f"yolo_dataset/{file_name}", "yolo_dataset")
    for model_file in (PROJECT_DIR / "yolo_dataset").glob("yolo*.pt"):
        _yolo_runtime_data += add_file_if_exists(model_file, "yolo_dataset")
    for model_file in (PROJECT_DIR / "yolo_dataset" / "models").glob("*.pt"):
        _yolo_runtime_data += add_file_if_exists(model_file, str(Path("yolo_dataset") / "models"))
    for weights_dir in (PROJECT_DIR / "yolo_dataset" / "runs").glob("detect/*/weights"):
        if weights_dir.exists():
            _yolo_runtime_data.append((str(weights_dir), str(Path("yolo_dataset") / "runs" / "detect" / weights_dir.parent.name / "weights")))

vendor_path = str(VENDOR_DIR)

a = Analysis(
    ['bootstrap.py'],
    pathex=[str(PROJECT_DIR), vendor_path],
    binaries=_binaries,
    datas=[
        # 默认配置随包提供；运行时 config.local.yaml/config.yaml 仍从 exe 同目录优先读取。
        ('config.yaml', '.'),
    ] + add_tree_if_exists("data", "data") + _yolo_runtime_data + _data,
    hiddenimports=[
        # OpenCV
        'cv2',
        # numpy
        'numpy',
        'numpy.core._methods',
        'numpy.random',
        # PIL
        'PIL',
        'PIL.Image',
        # mss
        'mss',
        'mss.windows',
        # pynput
        'pynput',
        'pynput.mouse',
        'pynput.keyboard',
        'pynput._util',
        # win32
        'win32gui',
        'win32ui',
        'win32con',
        'win32api',
        'win32process',
        'pythoncom',
        'pywintypes',
        # yaml
        'yaml',
        # tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        # 其它
        'queue',
        'threading',
        'json',
        'base64',
        'urllib',
        'subprocess',
        'logging',
    ] + _hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MHXY_Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime*.dll', 'python*.dll', 'torch*.dll', 'paddle*.dll'],
    runtime_tmpdir=None,
    console=False,                  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                      # 如需图标: icon='app.ico'
)

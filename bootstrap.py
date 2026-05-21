"""启动引导：将 vendor/ 加入 sys.path，然后启动主程序。

用法:
  python bootstrap.py          # 启动 UI
  pythonw bootstrap.py         # 启动 UI（无控制台窗口）
  python bootstrap.py --cli    # 启动命令行模式

PyInstaller 打包后:
  自动检测 sys._MEIPASS，从 exe 内部读取数据文件。
"""

import sys
import os
import warnings
import ctypes
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 必须在一切导入之前：抑制 libpng 警告
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "0")
warnings.filterwarnings("ignore", category=UserWarning)
# libpng iCCP 警告来自 cv2.imread，通过重定向 stderr 或设置环境变量抑制
try:
    import cv2
    try:
        cv2.setLogLevel(3)
    except AttributeError:
        pass  # 旧版 opencv 没有 setLogLevel
except ImportError:
    pass

# 处理 PyInstaller 打包路径
if getattr(sys, 'frozen', False):
    SOURCE_DIR = Path(sys._MEIPASS)
    USER_DIR = Path(sys.executable).parent
else:
    SOURCE_DIR = Path(__file__).parent
    USER_DIR = SOURCE_DIR


def setup_tcl_runtime(base_dir: Path = SOURCE_DIR) -> None:
    """Use bundled Tcl/Tk runtime when present.

    Some local Python installs have a broken Tcl registry/path even when the
    files exist. Pointing Tkinter to our bundled runtime also makes the EXE
    independent from the target machine's Python installation.
    """
    tcl_dir = base_dir / "tcl" / "tcl8.6"
    tk_dir = base_dir / "tcl" / "tk8.6"
    if tcl_dir.exists() and tk_dir.exists():
        os.environ["TCL_LIBRARY"] = str(tcl_dir)
        os.environ["TK_LIBRARY"] = str(tk_dir)


setup_tcl_runtime()

# 源码目录加入 sys.path（core.paths 等模块从此加载）
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

# vendor 只在开发模式使用（打包时 PyInstaller 已收集所有依赖）
VENDOR_DIR = SOURCE_DIR / "vendor" if not getattr(sys, 'frozen', False) else None


def setup_vendor():
    """将 vendor 目录加入 Python 搜索路径。"""
    if VENDOR_DIR is None:
        return False  # PyInstaller 打包模式，依赖已内置
    if VENDOR_DIR.exists():
        vendor_str = str(VENDOR_DIR)
        if vendor_str not in sys.path:
            sys.path.insert(0, vendor_str)

        for pth_file in VENDOR_DIR.glob("*.pth"):
            try:
                with open(pth_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            p = VENDOR_DIR / line
                            if p.exists() and str(p) not in sys.path:
                                sys.path.insert(0, str(p))
            except Exception:
                pass
        return True
    return False


def vendor_status() -> dict:
    """检查 vendor 中各关键包是否可用。"""
    packages = {
        "opencv-python": "cv2",
        "numpy": "numpy",
        "Pillow": "PIL",
        "mss": "mss",
        "pynput": "pynput",
        "pywin32": "win32gui",
        "PyYAML": "yaml",
        "ultralytics": "ultralytics",
        "paddleocr": "paddleocr",
        "torch": "torch",
        "pyautogui": "pyautogui",
    }
    status = {}
    for name, module in packages.items():
        try:
            __import__(module)
            status[name] = True
        except ImportError:
            status[name] = False
    return status


if __name__ == "__main__":
    setup_vendor()

    # 早期检查：pywin32 是否可用
    try:
        import win32gui  # noqa: F401
    except ImportError:
        print("=" * 50)
        print("  错误：pywin32 未安装")
        print("  请先运行: pip install pywin32")
        print("  或运行: setup_deps.bat")
        print("=" * 50)
        sys.exit(1)

    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        from main import main
        main()
    else:
        from main import Assistant, load_config

        config = load_config()
        app = Assistant(config)
        from ui.panel import ControlPanel
        panel = ControlPanel(app)
        panel.run()

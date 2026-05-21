#!/usr/bin/env python3
"""梦幻西游 AI 自动辅助 — 入口

启动方式:
  launcher.bat          # 双击启动 UI 面板（推荐）
  python bootstrap.py   # UI 模式
  python main.py        # CLI 交互模式

融合开源项目:
  - GDXY2: 资源解析参考
  - JCXY: 游戏架构参考
  - menghuanxiyou: YOLO检测 + 场景识别 + 师门实战
"""

import sys
import os
import time
import threading
import argparse
import ctypes
from pathlib import Path
from importlib import import_module


def _enable_dpi_awareness() -> None:
    """尽早启用 DPI 感知，保持截图像素和输入坐标一致。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _setup_source_and_vendor() -> tuple[Path, Path]:
    """允许直接 python main.py 时也能找到源码目录和 vendor 依赖。"""
    if getattr(sys, "frozen", False):
        source_dir = Path(sys._MEIPASS)
        user_dir = Path(sys.executable).parent
    else:
        source_dir = Path(__file__).resolve().parent
        user_dir = source_dir
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

    vendor_dir = source_dir / "vendor"
    if vendor_dir.exists() and str(vendor_dir) not in sys.path:
        sys.path.insert(0, str(vendor_dir))
        for pth_file in vendor_dir.glob("*.pth"):
            try:
                for line in pth_file.read_text(encoding="utf-8").splitlines():
                    rel = line.strip()
                    if rel and not rel.startswith("#"):
                        p = vendor_dir / rel
                        if p.exists() and str(p) not in sys.path:
                            sys.path.insert(0, str(p))
            except Exception:
                pass
    return source_dir, user_dir


_enable_dpi_awareness()
_BOOT_SOURCE_DIR, _BOOT_USER_DIR = _setup_source_and_vendor()

from core.paths import get_source_dir, get_user_dir, ensure_dirs
SOURCE_DIR = get_source_dir()
USER_DIR = get_user_dir()

# 启动时确保用户数据目录存在
ensure_dirs("data/templates/npc", "data/templates/ui", "data/templates/scenes",
           "data/templates/battle", "data/maps", "data/quests", "debug",
           "yolo_dataset/images/train", "yolo_dataset/images/val",
           "yolo_dataset/labels/train", "yolo_dataset/labels/val")

# ==================== 依赖检查 ====================

_IMPORT_CACHE = {}


def _safe_import(module_path: str, attr: str = None):
    """安全导入，失败返回 None 而不是崩溃。"""
    cache_key = f"{module_path}:{attr}"
    if cache_key in _IMPORT_CACHE:
        return _IMPORT_CACHE[cache_key]

    try:
        mod = import_module(module_path)
        val = getattr(mod, attr) if attr else mod
        _IMPORT_CACHE[cache_key] = val
        return val
    except ImportError as e:
        _IMPORT_CACHE[cache_key] = None
        return None


def _import_core():
    """安全导入 core 模块。"""
    return _safe_import("core")


def _import_game():
    return _safe_import("game")


def _import_tasks():
    return _safe_import("tasks")


def _import_yaml():
    return _safe_import("yaml")


def load_config(path: str = None) -> dict:
    yaml = _import_yaml()
    if yaml is None:
        print("PyYAML 未安装，使用默认配置")
        return _default_config()

    if path:
        paths = [Path(path)]
    else:
        # 优先用户目录（可覆盖内置配置），再查源码目录
        paths = [
            USER_DIR / "config.local.yaml",
            USER_DIR / "config.yaml",
            SOURCE_DIR / "config.yaml",
        ]

    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            continue

    return _default_config()


def _resolve_project_path(path_value: str | None) -> str:
    """把配置中的相对路径解析到用户目录/源码目录。"""
    if not path_value:
        return ""
    p = Path(os.path.expandvars(os.path.expanduser(path_value)))
    if p.is_absolute():
        return str(p)
    for base in (USER_DIR, SOURCE_DIR):
        candidate = base / p
        if candidate.exists():
            return str(candidate)
    return str(USER_DIR / p)


def _default_config() -> dict:
    return {
        "game": {"window_title": "梦幻西游", "window_title_pattern": "梦幻西游 ONLINE.*",
                 "window_size": [800, 600], "auto_move_window": False},
        "ai": {"enabled": False},
        "yolo": {"enabled": False},
        "scene_detection": {"enabled": False},
        "ocr": {"confidence_threshold": 0.7},
        "battle": {"default_action": "attack", "use_yolo_verify": False},
        "pathfinding": {"grid_size": 8, "click_variance": 3, "move_timeout": 60, "stuck_threshold": 5},
        "tasks": {"shimen": {"max_rounds": 20}, "zhuogui": {"max_rounds": 10}},
    }


# ==================== Assistant 主控 ====================

class Assistant:
    """AI 辅助主控类。"""

    def __init__(self, config: dict):
        self.config = config
        self.running = False
        self._thread: threading.Thread | None = None
        self.hwnd = None
        self.win_rect = None
        self.client_rect = None
        self.yolo = None
        self.ai_model = None
        self.scene_detector = None
        self.state_detector = None
        self.minimap_tracker = None
        self.battle_handler = None
        self.npc_interaction = None
        self.current_task = None
        self._yolo_preview = None

    # ---------- 初始化 ----------

    def init(self) -> bool:
        core = _import_core()
        if core is None:
            print("core 模块导入失败，请检查依赖")
            return False
        if not self._find_window(core):
            return False
        self._init_ai_model()
        self._init_yolo()
        self._init_scene_detector()
        self._init_state_detector()
        self._init_battle()
        self._init_npc()
        return True

    def _find_window(self, core) -> bool:
        pattern = self.config["game"].get("window_title_pattern", "梦幻西游 ONLINE.*")
        self.hwnd = core.find_window_regex(pattern)
        if not self.hwnd:
            title = self.config["game"]["window_title"]
            self.hwnd = core.find_window(title)
        if not self.hwnd:
            return False
        return self._apply_window(core)

    def set_window(self, hwnd: int) -> bool:
        """手动指定游戏窗口句柄。"""
        core = _import_core()
        if core is None:
            return False
        self.hwnd = hwnd
        return self._apply_window(core)

    def _apply_window(self, core) -> bool:
        """根据 self.hwnd 设置窗口位置、激活、移动。"""
        self.win_rect = core.get_window_rect(self.hwnd)
        self.client_rect = core.get_client_rect(self.hwnd)
        core.activate_window(self.hwnd)
        if self.config["game"].get("auto_move_window", False):
            core.move_window(self.hwnd, 0, 0)
            self.win_rect = core.get_window_rect(self.hwnd)
            self.client_rect = core.get_client_rect(self.hwnd)
        return True

    def _refresh_window_rects(self, core) -> bool:
        if not self.hwnd:
            return False
        try:
            self.win_rect = core.get_window_rect(self.hwnd)
            self.client_rect = core.get_client_rect(self.hwnd)
            return True
        except Exception:
            return False

    def _game_rect(self, core) -> tuple[int, int, int, int] | None:
        if not self._refresh_window_rects(core):
            return None
        return self.client_rect or self.win_rect

    def _init_ai_model(self):
        ai_cfg = self.config.get("ai", {})
        if not ai_cfg.get("enabled", False):
            return
        try:
            ai_mod = _safe_import("core.ai_model")
            if ai_mod:
                self.ai_model = ai_mod.create_ai_model(ai_cfg)
        except Exception:
            pass

    def _init_yolo(self):
        yolo_cfg = self.config.get("yolo", {})
        if not yolo_cfg.get("enabled", False):
            return
        try:
            detector_mod = _safe_import("core.detector")
            if detector_mod is None:
                return
            model_path = _resolve_project_path(yolo_cfg.get("model_path", ""))
            self.yolo = detector_mod.YOLODetector(
                model_path=model_path,
                conf_threshold=yolo_cfg.get("conf_threshold", 0.5),
                device=yolo_cfg.get("device", "cuda"),
            )
        except Exception as e:
            print(f"[YOLO] 初始化失败: {e}")

    def _init_scene_detector(self):
        scene_cfg = self.config.get("scene_detection", {})
        if not scene_cfg.get("enabled", False):
            return
        try:
            scene_mod = _safe_import("core.scene")
            if scene_mod is None:
                return
            self.scene_detector = scene_mod.SceneDetector(
                template_dir=scene_cfg.get("template_dir", "data/templates/scenes"),
                match_threshold=scene_cfg.get("match_threshold", 0.7),
            )
        except Exception:
            pass

    def _init_state_detector(self):
        game = _import_game()
        if game:
            self.state_detector = game.StateDetector(
                scene_detector=self.scene_detector,
                yolo_detector=self.yolo,
            )

    def _init_battle(self):
        game = _import_game()
        if game is None:
            return
        self.battle_handler = game.BattleHandler(
            capture_fn=self._capture,
            input_click_fn=self._click_game,
            input_hotkey_fn=self._hotkey,
            ocr_fn=self._ocr_game,
            config=self.config.get("battle", {}),
            yolo_detector=self.yolo,
        )

    def _init_npc(self):
        game = _import_game()
        if game is None:
            return
        self.npc_interaction = game.NPCInteraction(
            capture_fn=self._capture,
            click_fn=self._click_game,
            ocr_fn=self._ocr_game,
            match_fn=self._match_game,
        )

    # ---------- 游戏上下文 ----------

    @property
    def game_context(self) -> dict:
        return {
            "config": self.config,
            "capture": self._capture,
            "click": self._click_game,
            "input_hotkey": self._hotkey,
            "ocr": self._ocr_game,
            "template_match": self._match_game,
            "ai_model": self.ai_model,
            "yolo_detector": self.yolo,
            "scene_detector": self.scene_detector,
            "state_detector": self.state_detector,
            "battle_handler": self.battle_handler,
            "npc": self.npc_interaction,
            "navigator": self,
        }

    def _capture(self, region: tuple | None = None):
        core = _import_core()
        if core is None:
            return None
        rect = self._game_rect(core)
        if rect is None:
            return None
        if region:
            x1, y1, x2, y2 = map(int, region)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            x1 = max(0, min(x1, width))
            y1 = max(0, min(y1, height))
            x2 = max(0, min(x2, width))
            y2 = max(0, min(y2, height))
            if x2 <= x1 or y2 <= y1:
                return None
            left = rect[0] + x1
            top = rect[1] + y1
            w = x2 - x1
            h = y2 - y1
            return core.capture_region(left, top, w, h)
        return core.capture_region(
            rect[0], rect[1],
            rect[2] - rect[0],
            rect[3] - rect[1],
        )

    def _click_game(self, x: int, y: int, **kwargs) -> bool:
        core = _import_core()
        if core is None:
            return False

        rect = self._game_rect(core)
        if rect is None:
            return False

        left, top, right, bottom = rect
        screen_x = left + int(x)
        screen_y = top + int(y)
        if not (left <= screen_x < right and top <= screen_y < bottom):
            print(f"[点击] 坐标越界: game=({x},{y}) screen=({screen_x},{screen_y}) rect={rect}")
            return False

        try:
            if not core.verify_click_window(screen_x, screen_y, self.hwnd):
                core.activate_window(self.hwnd)
                time.sleep(0.15)
                if not core.verify_click_window(screen_x, screen_y, self.hwnd):
                    print(f"[点击] 目标点不在游戏窗口内: ({screen_x},{screen_y})")
                    return False
        except Exception as e:
            print(f"[点击] 窗口校验失败: {e}")
            return False

        return bool(core.click(screen_x, screen_y, **kwargs))

    def _hotkey(self, *keys):
        core = _import_core()
        if core:
            core.hotkey(*keys)

    def _ocr_game(self, image):
        ocr_mod = _safe_import("core.ocr")
        if ocr_mod and hasattr(ocr_mod, "ocr_region"):
            return ocr_mod.ocr_region(
                image, self.config.get("ocr", {}).get("confidence_threshold", 0.7)
            )
        return []

    def _match_game(self, image, template_name: str, category: str = ""):
        core = _import_core()
        if core and hasattr(core, "match_template"):
            tmpl = core.load_template(template_name, category)
            return core.match_template(image, tmpl)
        return None

    # ---------- 导航 ----------

    def go_to_location(self, location: str) -> bool:
        print(f"[导航] 前往: {location}")
        return True

    def patrol_area(self, area: str, steps: int = 5) -> bool:
        print(f"[巡逻] 区域: {area}, 步数: {steps}")
        return True

    # ---------- 任务控制 ----------

    def run_task(self, task_name: str) -> None:
        tasks_mod = _import_tasks()
        if tasks_mod is None:
            print("tasks 模块导入失败")
            return

        # 优先从注册表查找，回退到硬编码映射
        from tasks.base import get_task
        task = get_task(task_name, self.game_context)
        if task is None:
            task_map = {
                "shimen": tasks_mod.ShimenTask,
                "zhuogui": tasks_mod.ZhuoguiTask,
                "patrol": tasks_mod.PatrolTask,
                "plot": tasks_mod.PlotTask,
                "escort": getattr(tasks_mod, "EscortTask", None),
            }
            task_cls = task_map.get(task_name)
            if not task_cls:
                print(f"未知任务: {task_name}")
                return
            task = task_cls(self.game_context)

        self.current_task = task
        self.running = True
        self._thread = threading.Thread(target=self._task_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        if self.current_task:
            self.current_task.cancel()

    def _task_loop(self) -> None:
        task = self.current_task
        task.start()
        while self.running:
            state = task.tick()
            if state.value in ("completed", "error", "cancelled"):
                break
            time.sleep(0.1)

    # ---------- 调试 ----------

    def start_yolo_preview(self):
        if not self.yolo:
            print("YOLO 未启用")
            return None
        detector_mod = _safe_import("core.detector")
        if detector_mod:
            preview = detector_mod.YOLODetectionWindow(self.yolo, self._capture)
            self._yolo_preview = preview  # 必须在 start() 之前赋值，否则面板无法停止
            preview.start()
            self._yolo_preview = None
            return preview
        return None


# ==================== 入口 ====================

def main():
    parser = argparse.ArgumentParser(description="梦幻西游 AI 自动辅助")
    parser.add_argument("--task", choices=["shimen", "zhuogui", "patrol", "plot", "escort"])
    parser.add_argument("--config", default=None)
    parser.add_argument("--ui", action="store_true", default=True,
                       help="启动 UI 面板（默认）")
    parser.add_argument("--no-ui", action="store_true", help="使用命令行模式")
    args = parser.parse_args()

    config = load_config(args.config)
    assistant = Assistant(config)

    # UI 模式
    if args.ui and not args.no_ui:
        # 检查 tkinter 是否可用
        try:
            ui_mod = _safe_import("ui.panel")
            if ui_mod:
                panel = ui_mod.ControlPanel(assistant)
                panel.run()
                return
        except Exception:
            pass

    # CLI 模式
    if not assistant.init():
        print("未找到游戏窗口！")
        sys.exit(1)

    if args.task:
        assistant.run_task(args.task)
        try:
            while assistant.running:
                time.sleep(1)
        except KeyboardInterrupt:
            assistant.stop()
        return

    # 交互 CLI
    print("\n" + "=" * 50)
    print("  梦幻西游 AI 自动辅助 v2")
    print("=" * 50)
    print("  1. 师门  2. 捉鬼  3. 剧情  4. 巡逻  0. 退出")
    print("-" * 50)
    try:
        while True:
            cmd = input("\n> ").strip()
            if cmd == "1": assistant.run_task("shimen")
            elif cmd == "2": assistant.run_task("zhuogui")
            elif cmd == "3": assistant.run_task("plot")
            elif cmd == "4": assistant.run_task("patrol")
            elif cmd == "0": break
    except KeyboardInterrupt:
        pass
    assistant.stop()
    print("\n已退出")


if __name__ == "__main__":
    main()

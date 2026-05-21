"""梦幻西游 AI 辅助 — 图形控制面板 (tkinter)。

纯 UI 操作，不需要命令行交互。
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import queue
import os
import sys
from pathlib import Path
from datetime import datetime

from core.paths import get_source_dir, get_user_dir, ensure_dirs
SOURCE_DIR = get_source_dir()
USER_DIR = get_user_dir()
DATASET_DIR = USER_DIR / "yolo_dataset"
# 确保 yolo 数据集目录存在
ensure_dirs("yolo_dataset/images/train", "yolo_dataset/images/val",
           "yolo_dataset/labels/train", "yolo_dataset/labels/val")


# ==================== 控制面板 ====================

class ControlPanel:
    """AI 辅助控制面板。"""

    def __init__(self, assistant):
        self.assistant = assistant
        self.log_queue = queue.Queue()
        self._poll_id = None
        self._log_after_id = None
        self._train_window = None

        self.root = tk.Tk()
        self.root.title("梦幻西游 AI 自动辅助 v2")
        self.root.geometry("500x680")
        self.root.resizable(True, True)
        self.root.minsize(440, 560)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._set_style()
        self._build_ui()
        self._start_log_consumer()

    def _set_style(self):
        self.root.configure(bg="#f0f0f0")
        self.root.option_add("*Font", ("微软雅黑", 9))

    # ==================== UI 构建 ====================

    def _build_ui(self):
        # 标题栏
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=50)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="梦幻西游 AI 自动辅助",
                font=("微软雅黑", 14, "bold"), fg="white", bg="#2c3e50").pack(pady=10)

        # 连接状态
        self._build_status_bar()
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10)

        # 任务区
        self._build_task_buttons()
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10)

        # AI 工具区
        self._build_ai_tools()
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10)

        # 调试工具区
        self._build_debug_tools()
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10)

        # 进度条
        self._build_progress()

        # 日志区
        self._build_log_area()

    def _build_status_bar(self):
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        self.conn_indicator = tk.Label(frame, text="○", font=("", 12),
                                       fg="red", bg="#f0f0f0")
        self.conn_indicator.pack(side="left")
        self.conn_label = tk.Label(frame, text="未连接", bg="#f0f0f0")
        self.conn_label.pack(side="left", padx=(2, 20))

        tk.Label(frame, text="场景:", bg="#f0f0f0").pack(side="left")
        self.scene_label = tk.Label(frame, text="--", fg="#2980b9", bg="#f0f0f0")
        self.scene_label.pack(side="left", padx=(2, 20))

        tk.Label(frame, text="状态:", bg="#f0f0f0").pack(side="left")
        self.status_label = tk.Label(frame, text="就绪", fg="#27ae60", bg="#f0f0f0")
        self.status_label.pack(side="left", padx=2)

    def _build_task_buttons(self):
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        tk.Label(frame, text="任务选择", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        btn_frame = tk.Frame(frame, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="师门任务",
                  command=lambda: self._start_task("shimen"),
                  width=10).pack(side="left", padx=(0, 3))
        ttk.Button(btn_frame, text="捉鬼任务",
                  command=lambda: self._start_task("zhuogui"),
                  width=10).pack(side="left", padx=(0, 3))
        ttk.Button(btn_frame, text="押镖任务",
                  command=lambda: self._start_task("escort"),
                  width=10).pack(side="left", padx=(0, 3))
        ttk.Button(btn_frame, text="剧情任务",
                  command=lambda: self._start_task("plot"),
                  width=10).pack(side="left", padx=(0, 3))
        ttk.Button(btn_frame, text="自动巡逻",
                  command=lambda: self._start_task("patrol"),
                  width=10).pack(side="left")

        # 停止 + 退出按钮行
        ctrl_frame = tk.Frame(frame, bg="#f0f0f0")
        ctrl_frame.pack(fill="x", pady=5)
        ttk.Button(ctrl_frame, text="■ 停止当前任务",
                  command=self._stop_task, width=18).pack(side="left", padx=(0, 8))
        ttk.Button(ctrl_frame, text="✕ 退出程序",
                  command=self._on_close, width=14).pack(side="left")

    def _build_ai_tools(self):
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        tk.Label(frame, text="AI 模型", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        desc_frame = tk.Frame(frame, bg="#f0f0f0")
        desc_frame.pack(fill="x")
        tk.Label(desc_frame, text="训练 YOLO 模型以识别游戏中的 NPC、怪物、按钮等元素",
                font=("微软雅黑", 8), fg="#7f8c8d", bg="#f0f0f0").pack(anchor="w")

        btn_frame = tk.Frame(frame, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="训练 YOLO",
                  command=self._open_train_dialog, width=12).pack(side="left", padx=(0, 3))
        ttk.Button(btn_frame, text="AI 助手",
                  command=self._open_ai_assistant, width=12).pack(side="left", padx=(0, 3))
        ttk.Button(btn_frame, text="AI 设置",
                  command=self._open_ai_settings, width=12).pack(side="left", padx=(0, 3))
        self._yolo_preview_btn = ttk.Button(btn_frame, text="YOLO 预览",
                  command=self._toggle_yolo_preview, width=12)
        self._yolo_preview_btn.pack(side="left")

        # 模型状态
        status_frame = tk.Frame(frame, bg="#f0f0f0")
        status_frame.pack(fill="x", pady=(3, 0))
        tk.Label(status_frame, text="当前模型:", font=("微软雅黑", 8),
                fg="#7f8c8d", bg="#f0f0f0").pack(side="left")
        model_path = self.assistant.config.get("yolo", {}).get("model_path", "未配置")
        self.model_label = tk.Label(status_frame, text=model_path,
                                    font=("微软雅黑", 8), fg="#2980b9", bg="#f0f0f0")
        self.model_label.pack(side="left", padx=4)

        # AI 模型状态
        ai_frame = tk.Frame(frame, bg="#f0f0f0")
        ai_frame.pack(fill="x", pady=(2, 0))
        tk.Label(ai_frame, text="AI 模型:", font=("微软雅黑", 8),
                fg="#7f8c8d", bg="#f0f0f0").pack(side="left")
        ai_info = self.assistant.ai_model
        if ai_info:
            ai_text = f"{ai_info.name} ({getattr(ai_info, 'model', '?')})"
            ai_color = "#27ae60"
        else:
            ai_text = "未启用"
            ai_color = "#e67e22"
        self.ai_label = tk.Label(ai_frame, text=ai_text,
                                 font=("微软雅黑", 8), fg=ai_color, bg="#f0f0f0")
        self.ai_label.pack(side="left", padx=4)

    def _build_debug_tools(self):
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        tk.Label(frame, text="调试工具", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        # 横向滚动容器
        canvas = tk.Canvas(frame, bg="#f0f0f0", height=36,
                          highlightthickness=0)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=hbar.set)

        btn_frame = tk.Frame(canvas, bg="#f0f0f0")
        btn_win = canvas.create_window((0, 0), window=btn_frame, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        btn_frame.bind("<Configure>", _on_configure)

        # 可横向滚动的按钮栏
        buttons = [
            ("截取当前画面", self._capture_debug),
            ("采集场景模板", self._capture_scene_template),
            ("采集哈希模板", self._capture_hash),
            ("重新定位窗口", self._relocate_window),
            ("打开截图目录", lambda: os.startfile(str(USER_DIR / "debug"))),
        ]
        for text, cmd in buttons:
            ttk.Button(btn_frame, text=text, command=cmd, width=14).pack(
                side="left", padx=(0, 6))

        hbar.pack(fill="x", pady=0)
        canvas.pack(fill="x", pady=0)

    def _build_progress(self):
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=4)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(frame, variable=self.progress_var,
                                            maximum=1.0)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.progress_label = tk.Label(frame, text="--", bg="#f0f0f0", width=10)
        self.progress_label.pack(side="right")

    def _build_log_area(self):
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill="both", expand=True, padx=15, pady=(4, 10))

        tk.Label(frame, text="运行日志", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            frame, height=10, width=55, state="disabled",
            font=("Consolas", 8), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white",
        )
        self.log_text.pack(fill="both", expand=True, pady=3)

        ttk.Button(frame, text="清空日志", command=self._clear_log,
                  width=10).pack(anchor="e")

    # ==================== 日志系统 ====================

    def log(self, message: str, level: str = "info"):
        self.log_queue.put((datetime.now(), level, message))

    def _start_log_consumer(self):
        self._consume_log()

    def _consume_log(self):
        try:
            while True:
                ts, level, msg = self.log_queue.get_nowait()
                self._append_log(ts, level, msg)
        except queue.Empty:
            pass
        self._log_after_id = self.root.after(200, self._consume_log)

    def _append_log(self, ts: datetime, level: str, msg: str):
        self.log_text.configure(state="normal")
        time_str = ts.strftime("%H:%M:%S")
        if level == "error":
            tag = "error"
        elif level == "warn":
            tag = "warn"
        elif level == "task":
            tag = "task"
        elif level == "train":
            tag = "train"
        else:
            tag = "info"
        self.log_text.insert("end", f"[{time_str}] ", "time")
        self.log_text.insert("end", f"{msg}\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.log_text.tag_configure("time", foreground="#808080")
        self.log_text.tag_configure("error", foreground="#e74c3c")
        self.log_text.tag_configure("warn", foreground="#f39c12")
        self.log_text.tag_configure("task", foreground="#2ecc71")
        self.log_text.tag_configure("train", foreground="#3498db")
        self.log_text.tag_configure("info", foreground="#d4d4d4")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ==================== 状态刷新 ====================

    def _start_polling(self):
        self._poll_status()

    def _poll_status(self):
        if self.assistant.hwnd:
            self.conn_indicator.configure(text="●", fg="#27ae60")
            self.conn_label.configure(text="已连接")
        else:
            self.conn_indicator.configure(text="○", fg="red")
            self.conn_label.configure(text="未连接")

        if self.assistant.scene_detector is not None:
            # 每 10 次轮询（~5秒）做一次实际检测
            if not hasattr(self, "_scene_poll_count"):
                self._scene_poll_count = 0
            self._scene_poll_count += 1
            if self._scene_poll_count % 10 == 1:
                try:
                    img = self.assistant._capture()
                    if img is not None:
                        self.assistant.scene_detector.detect(img)
                except Exception:
                    pass
            self.scene_label.configure(text=self.assistant.scene_detector.scene)
        else:
            self.scene_label.configure(text="未启用")

        task = self.assistant.current_task
        if task:
            self.status_label.configure(
                text=f"{task.current_step_name} ({task.progress:.0%})", fg="#2980b9")
            self.progress_var.set(task.progress)
            self.progress_label.configure(text=f"{task.progress:.0%}")
            if task.state.value == "completed":
                self.status_label.configure(text="完成", fg="#27ae60")
                self.progress_var.set(1.0)
                self.progress_label.configure(text="100%")
            elif task.state.value == "error":
                self.status_label.configure(text="出错", fg="#e74c3c")
        else:
            self.status_label.configure(text="就绪", fg="#27ae60")
            self.progress_var.set(0)
            self.progress_label.configure(text="--")

        self._poll_id = self.root.after(500, self._poll_status)

    # ==================== 任务操作 ====================

    def _start_task(self, name: str):
        if self.assistant.current_task and \
           self.assistant.current_task.state.value == "running":
            messagebox.showwarning("任务运行中", "请先停止当前任务再启动新任务。")
            return
        names = {"shimen": "师门任务", "zhuogui": "捉鬼任务", "escort": "押镖任务",
                 "patrol": "自动巡逻", "plot": "剧情任务"}
        display = names.get(name, name)
        self.log(f"任务将在 2 秒后启动: {display}（请松开鼠标键盘）", "task")
        self.status_label.configure(text=f"准备执行 {display}...", fg="#f39c12")
        # 延迟 2 秒再启动，给用户时间松手
        self.root.after(2000, lambda: self._do_start_task(name, display))

    def _do_start_task(self, name: str, display: str):
        self.assistant.run_task(name)
        self.log(f"任务已启动: {display}", "task")
        if not self._poll_id:
            self._start_polling()

    def _stop_task(self):
        if self.assistant.current_task:
            self.assistant.stop()
            self.log("任务已手动停止", "warn")
        else:
            messagebox.showinfo("提示", "当前没有运行中的任务。")

    # ==================== 工具操作 ====================

    def _toggle_yolo_preview(self):
        # 如果正在预览，则停止
        preview = self.assistant._yolo_preview
        if preview is not None and preview.running:
            self._stop_yolo_preview()
            return

        if not self.assistant.yolo:
            messagebox.showwarning("YOLO 未启用",
                                   "YOLO 模型未加载，请先训练或配置模型路径。")
            return

        self.log("启动 YOLO 检测预览...", "info")
        self._yolo_preview_btn.configure(text="停止预览")

        def _run():
            self.assistant.start_yolo_preview()
            # 预览窗口关闭后（Q键/X按钮/stop），恢复按钮文字
            self.root.after(0, lambda: self._yolo_preview_btn.configure(text="YOLO 预览"))

        threading.Thread(target=_run, daemon=True).start()

    def _stop_yolo_preview(self):
        """停止 YOLO 预览。"""
        self.log("停止 YOLO 检测预览", "info")
        preview = self.assistant._yolo_preview
        if preview is not None:
            preview.stop()
            # assistant._yolo_preview 在 start_yolo_preview 返回后自动清为 None
        self._yolo_preview_btn.configure(text="YOLO 预览")

    def _capture_debug(self):
        img = self.assistant._capture()
        if img is not None:
            import cv2
            debug_dir = USER_DIR / "debug"
            debug_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = debug_dir / f"screenshot_{ts}.png"
            cv2.imwrite(str(path), img)
            self.log(f"截图已保存: {path}", "info")
            messagebox.showinfo("截图完成", f"已保存到 {path}")
        else:
            self.log("截图失败：无法获取游戏画面", "error")

    def _capture_hash(self):
        """截取全屏并注册为感知哈希模板。"""
        from tkinter import simpledialog
        name = simpledialog.askstring("哈希模板名称",
            "输入模板名称（如 battle_cmd, dialog_next）：\n"
            "用于快速检测 UI 是否出现。\n\n"
            "提示：请在 data/hashes/ 目录手动替换为\n"
            "对应 UI 区域的小截图效果更好。")
        if not name:
            return
        img = self.assistant._capture()
        if img is not None:
            try:
                from core.hasher import get_hasher
                get_hasher().register(name, img)
                self.log(f"哈希模板已注册: {name}", "task")
                messagebox.showinfo("注册成功",
                    f"模板 '{name}' 已保存到 data/hashes/{name}.hash")
            except Exception as e:
                self.log(f"注册失败: {e}", "error")

    def _capture_scene_template(self):
        """OCR + AI 自动识别当前场景并保存为模板。"""
        img = self.assistant._capture()
        if img is None:
            self.log("截图失败：无法获取游戏画面", "error")
            messagebox.showwarning("截图失败", "请先连接游戏窗口")
            return

        self.log("正在分析当前场景...", "info")
        import cv2
        from tkinter import simpledialog

        # 1. OCR 识别画面中的关键文字
        ocr_hints = []
        ocr_result = self.assistant._ocr_game(img)
        if ocr_result:
            texts = [r["text"] for r in ocr_result if len(r["text"]) >= 2]
            ocr_hints = texts[:15]  # 取前15条

        # 2. AI 分析（如果可用）
        ai_suggestion = ""
        ai = self.assistant.ai_model
        if ai and ai.supports_vision:
            try:
                ocr_context = ", ".join(ocr_hints) if ocr_hints else "无"
                prompt = f"""分析这张梦幻西游游戏截图，判断当前所处的场景/状态。

画面中的 OCR 文字: {ocr_context}

请用简短的中文词回答（只返回一个词，如：战斗、对话、登录、地图、师门、摆摊、商城、背包、队伍、捉鬼、跑商、押镖、打图、挖宝、其他）。
如果无法确定，回答"未知"。

只回答场景名称，不要加任何解释。"""
                ai_suggestion = ai.analyze_image(img, prompt).strip()
            except Exception as e:
                self.log(f"AI 分析场景失败: {e}", "warn")

        # 3. 组装建议名称
        suggested = ai_suggestion or ""
        if not suggested:
            if ocr_hints:
                # 用 OCR 关键词做 fallback
                ocr_joined = " ".join(ocr_hints)
                if "战斗" in ocr_joined:
                    suggested = "battle"
                elif "对话" in ocr_joined or "下一步" in ocr_joined:
                    suggested = "dialog"
                else:
                    suggested = ""
            if not suggested:
                suggested = ""

        # 4. 弹窗让用户确认
        hint_text = ""
        if ocr_hints:
            hint_text = f"OCR 识别文字: {', '.join(ocr_hints[:8])}\n\n"
        prompt_msg = (
            f"{hint_text}"
            f"AI 建议: {suggested if suggested else '（无法自动识别）'}\n\n"
            f"请输入场景名称（英文，如: battle, dialog, login, map, master）："
        )
        name = simpledialog.askstring("采集场景模板", prompt_msg, parent=self.root,
                                       initialvalue=suggested)
        if not name or not name.strip():
            return
        name = name.strip()

        # 5. 保存模板
        try:
            if self.assistant.scene_detector:
                self.assistant.scene_detector.add_template(name, img)
            else:
                # 手动保存到文件
                tmpl_dir = SOURCE_DIR / "data" / "templates" / "scenes"
                tmpl_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(tmpl_dir / f"{name}.png"), img)
            self.log(f"场景模板已保存: {name}", "task")
            messagebox.showinfo("采集完成",
                                f"场景模板 '{name}' 已保存到 data/templates/scenes/{name}.png\n\n"
                                f"下次检测时将自动匹配此场景。")
        except Exception as e:
            self.log(f"保存场景模板失败: {e}", "error")

    def _relocate_window(self):
        """手动选择游戏窗口（先尝试自动匹配，失败则弹出窗口列表）。"""
        self.log("搜索游戏窗口...", "info")

        # 先尝试自动匹配
        from main import _import_core
        core = _import_core()
        if core and self.assistant._find_window(core):
            self._on_window_connected()
            return

        # 自动匹配失败 → 弹出窗口选择对话框
        if core is None:
            self.log("core 模块未加载，无法列出窗口", "error")
            return

        windows = core.list_all_windows()
        if not windows:
            self.log("未找到任何可见窗口", "error")
            messagebox.showwarning("未找到窗口", "系统中没有可见窗口。\n请确保游戏已启动。")
            return

        # 创建选择对话框
        picker = tk.Toplevel(self.root)
        picker.title("选择游戏窗口")
        picker.geometry("520x400")
        picker.resizable(True, True)
        picker.minsize(400, 250)
        picker.configure(bg="#f0f0f0")

        tk.Label(picker, text="请选择梦幻西游的窗口（可按标题搜索）",
                font=("微软雅黑", 10, "bold"), bg="#f0f0f0").pack(pady=(10, 2))

        # 搜索框
        search_frame = tk.Frame(picker, bg="#f0f0f0")
        search_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(search_frame, text="搜索:", bg="#f0f0f0").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side="left", padx=4, fill="x", expand=True)
        search_entry.focus_set()

        # 窗口列表
        list_frame = tk.Frame(picker, bg="#f0f0f0")
        list_frame.pack(fill="both", expand=True, padx=12, pady=4)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                            font=("微软雅黑", 9), activestyle="dotbox",
                            exportselection=False)
        scrollbar.configure(command=listbox.yview)
        listbox.pack(fill="both", expand=True)

        _hwnd_map: dict[str, int] = {}

        def _fill_all():
            _hwnd_map.clear()
            listbox.delete(0, "end")
            pattern_lower = search_var.get().lower()
            for hwnd, title in windows:
                if not pattern_lower or pattern_lower in title.lower():
                    listbox.insert("end", title)
                    _hwnd_map[title] = hwnd

        _fill_all()

        search_var.trace_add("write", lambda *_: _fill_all())

        # 双击选中
        def _on_select(_event=None):
            sel = listbox.curselection()
            if not sel:
                return
            title = listbox.get(sel[0])
            hwnd = _hwnd_map.get(title)
            if hwnd is None:
                return
            if self.assistant.set_window(hwnd):
                picker.destroy()
                self._on_window_connected()
            else:
                messagebox.showerror("错误", "无法连接到所选窗口")

        listbox.bind("<Double-Button-1>", _on_select)
        search_entry.bind("<Return>", _on_select)

        # 选择按钮
        btn_frame = tk.Frame(picker, bg="#f0f0f0")
        btn_frame.pack(fill="x", padx=12, pady=(4, 10))
        ttk.Button(btn_frame, text="选择窗口", command=_on_select).pack(side="left", padx=(0, 6))
        ttk.Button(btn_frame, text="取消", command=picker.destroy).pack(side="left")

        listbox.bind("<Return>", _on_select)

    def _on_window_connected(self):
        """窗口连接成功后的统一处理。"""
        self.log(f"已连接: {self.assistant.win_rect}", "task")
        self.conn_indicator.configure(text="●", fg="#27ae60")
        self.conn_label.configure(text="已连接")

    def _auto_label(self):
        """自动标注：用当前模型对截图目录做推理。"""
        if not self.assistant.yolo:
            messagebox.showwarning("无模型", "请先训练或配置 YOLO 模型。")
            return

        image_dir = filedialog.askdirectory(title="选择待标注截图目录")
        if not image_dir:
            return

        import subprocess
        self.log("开始自动标注...", "train")
        threading.Thread(
            target=lambda: self._run_auto_label(image_dir),
            daemon=True,
        ).start()

    def _run_auto_label(self, image_dir: str):
        import subprocess
        script = SOURCE_DIR / "yolo_dataset" / "auto_label.py"
        model = self.assistant.config["yolo"]["model_path"]
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--model", model, "--images", image_dir],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
            )
            for line in result.stdout.splitlines():
                self.log(f"[标注] {line}", "info")
            if result.returncode == 0:
                self.log("自动标注完成，请检查修正后放入 yolo_dataset/labels/train/", "train")
            else:
                self.log(f"标注失败: {result.stderr}", "error")
        except Exception as e:
            self.log(f"标注异常: {e}", "error")

    # ==================== 生命周期 ====================

    def run(self):
        """启动 UI 主循环。"""
        if self.assistant.init():
            self._on_window_connected()
            self.log("AI 辅助初始化完成", "task")
            yolo_status = "已启用" if self.assistant.yolo else "未启用(回退模板匹配)"
            self.log(f"  YOLO: {yolo_status}", "info")
            scene_status = "已启用" if self.assistant.scene_detector else "未启用"
            self.log(f"  场景检测: {scene_status}", "info")
        else:
            self.log("未找到游戏窗口，请点击 [重新定位窗口] 手动选择", "warn")
        self.root.mainloop()

    def _on_close(self):
        """关闭窗口 — 确保进程完全退出。"""
        try:
            # 关闭子窗口
            for attr in ('_train_window', '_ai_assist_win'):
                win = getattr(self, attr, None)
                if win:
                    try:
                        # AIAssistantDialog 用 .win, YOLOTrainDialog 用 .win
                        actual_win = getattr(win, 'win', win)
                        if actual_win.winfo_exists():
                            actual_win.destroy()
                    except Exception:
                        pass

            # 停止 YOLO 预览
            if self.assistant._yolo_preview is not None and self.assistant._yolo_preview.running:
                self.assistant._yolo_preview.stop()

            # 停止运行中的任务
            if self.assistant.current_task and \
               getattr(self.assistant.current_task, 'state', None) and \
               self.assistant.current_task.state.value == "running":
                if messagebox.askyesno("Confirm Exit",
                                       "A task is still running. Are you sure you want to exit?"):
                    self.assistant.stop()
                else:
                    return

            # 取消定时器
            if self._poll_id:
                self.root.after_cancel(self._poll_id)
            if self._log_after_id:
                self.root.after_cancel(self._log_after_id)
        except Exception:
            pass
        finally:
            self.root.destroy()
            # 强制退出，确保 pythonw 进程结束
            import os as _os
            _os._exit(0)

    def _open_ai_assistant(self):
        """打开 AI 助手对话框。"""
        if hasattr(self, '_ai_assist_win') and self._ai_assist_win:
            try:
                if self._ai_assist_win.win.winfo_exists():
                    self._ai_assist_win.win.lift()
                    return
            except Exception:
                pass
        self._ai_assist_win = AIAssistantDialog(self.root, self)

    def _open_ai_settings(self):
        """打开 AI 助手并展开设置面板。"""
        self._open_ai_assistant()
        if self._ai_assist_win:
            self._ai_assist_win._toggle_settings()

    # ==================== YOLO 训练 ====================

    def _open_train_dialog(self):
        """打开 YOLO 训练对话框。"""
        if self._train_window:
            try:
                if self._train_window.win.winfo_exists():
                    self._train_window.win.lift()
                    return
            except Exception:
                pass
        self._train_window = YOLOTrainDialog(self.root, self)


# ==================== AI 助手对话框 ====================

class AIAssistantDialog:
    """AI 助手对话框 — 通用 AI 辅助功能 + 内置设置面板。"""

    PROVIDERS = ["openai", "anthropic", "ollama", "custom"]

    def __init__(self, parent, panel: "ControlPanel"):
        self.panel = panel
        self._history: list[dict] = []
        self._settings_visible = False
        self._settings_frame = None

        self.win = tk.Toplevel(parent)
        self.win.title("AI 助手")
        self.win.geometry("500x600")
        self.win.resizable(True, True)
        self.win.minsize(420, 480)
        self.win.configure(bg="#f0f0f0")

        self._build()

    def _build(self):
        # 标题栏 + 设置按钮
        title_frame = tk.Frame(self.win, bg="#2c3e50", height=38)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="AI 助手", font=("微软雅黑", 13, "bold"),
                fg="white", bg="#2c3e50").pack(side="left", padx=15, pady=6)
        ttk.Button(title_frame, text="⚙ 设置",
                  command=self._toggle_settings, width=8).pack(side="right", padx=15, pady=4)

        # AI 状态
        status_frame = tk.Frame(self.win, bg="#f0f0f0")
        status_frame.pack(fill="x", padx=15, pady=6)
        self._refresh_status_label(status_frame)

        # ====== 设置面板（默认隐藏）======
        self._settings_frame = tk.Frame(self.win, bg="#fafafa",
                                        highlightbackground="#ddd", highlightthickness=1)
        self._build_settings(self._settings_frame)
        # 先 pack 再 forget — 让 tkinter 建立父子关系
        self._settings_frame.pack(fill="x", padx=15, pady=4)
        self._settings_frame.pack_forget()

        ttk.Separator(self.win, orient="horizontal").pack(fill="x", padx=15, pady=2)

        # 快捷操作
        act_frame = tk.Frame(self.win, bg="#f0f0f0")
        act_frame.pack(fill="x", padx=15, pady=4)
        tk.Label(act_frame, text="快捷操作", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        btn_row = tk.Frame(act_frame, bg="#f0f0f0")
        btn_row.pack(fill="x", pady=4)

        ttk.Button(btn_row, text="分析当前画面",
                  command=self._analyze_screen, width=16).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="任务错误诊断",
                  command=self._diagnose_error, width=16).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="游戏策略建议",
                  command=self._strategy_advice, width=16).pack(side="left")

        ttk.Separator(self.win, orient="horizontal").pack(fill="x", padx=15, pady=4)

        # 对话区
        chat_frame = tk.Frame(self.win, bg="#f0f0f0")
        chat_frame.pack(fill="both", expand=True, padx=15, pady=(0, 4))

        tk.Label(chat_frame, text="AI 对话", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        self.chat_log = scrolledtext.ScrolledText(
            chat_frame, height=10, width=55, state="disabled",
            font=("Consolas", 8), bg="#1e1e1e", fg="#d4d4d4",
            wrap="word",
        )
        self.chat_log.pack(fill="both", expand=True, pady=2)

        # 输入区
        input_frame = tk.Frame(self.win, bg="#f0f0f0")
        input_frame.pack(fill="x", padx=15, pady=(0, 8))

        self.input_var = tk.StringVar()
        input_row = tk.Frame(input_frame, bg="#f0f0f0")
        input_row.pack(fill="x")
        self.input_entry = ttk.Entry(input_row, textvariable=self.input_var, width=45)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", lambda e: self._send_message())
        ttk.Button(input_row, text="发送", command=self._send_message, width=8).pack(side="right")

        self.loading_lbl = tk.Label(input_frame, text="", fg="#7f8c8d",
                                    bg="#f0f0f0", font=("微软雅黑", 8))
        self.loading_lbl.pack(anchor="w", pady=(2, 0))

    # ====== 设置面板 ======

    def _build_settings(self, parent):
        """构建设置面板内容。"""
        cfg = self.panel.assistant.config.get("ai", {})

        pad = {"padx": 8, "pady": 2}

        # 启用开关
        row0 = tk.Frame(parent, bg="#fafafa")
        row0.pack(fill="x", **pad)
        tk.Label(row0, text="启用 AI", bg="#fafafa", width=10, anchor="w").pack(side="left")
        self.cfg_enabled = tk.BooleanVar(value=cfg.get("enabled", False))
        ttk.Checkbutton(row0, variable=self.cfg_enabled).pack(side="left")

        # 提供商
        row1 = tk.Frame(parent, bg="#fafafa")
        row1.pack(fill="x", **pad)
        tk.Label(row1, text="提供商", bg="#fafafa", width=10, anchor="w").pack(side="left")
        self.cfg_provider = tk.StringVar(value=cfg.get("provider", "openai"))
        cb = ttk.Combobox(row1, textvariable=self.cfg_provider,
                         values=self.PROVIDERS, state="readonly", width=15)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_provider_change())

        # API Key
        row2 = tk.Frame(parent, bg="#fafafa")
        row2.pack(fill="x", **pad)
        tk.Label(row2, text="API Key", bg="#fafafa", width=10, anchor="w").pack(side="left")
        self.cfg_api_key = tk.StringVar()
        self.cfg_api_key_entry = ttk.Entry(row2, textvariable=self.cfg_api_key, width=35, show="*")
        self.cfg_api_key_entry.pack(side="left", padx=(0, 5))
        # 显示/隐藏切换
        self._show_key = False
        ttk.Button(row2, text="👁", command=self._toggle_key_visibility, width=3).pack(side="left")

        # 模型
        row3 = tk.Frame(parent, bg="#fafafa")
        row3.pack(fill="x", **pad)
        tk.Label(row3, text="模型", bg="#fafafa", width=10, anchor="w").pack(side="left")
        self.cfg_model = tk.StringVar()
        self.cfg_model_entry = ttk.Entry(row3, textvariable=self.cfg_model, width=35)
        self.cfg_model_entry.pack(side="left")

        # 端点 URL
        row4 = tk.Frame(parent, bg="#fafafa")
        row4.pack(fill="x", **pad)
        tk.Label(row4, text="API 地址", bg="#fafafa", width=10, anchor="w").pack(side="left")
        self.cfg_base_url = tk.StringVar()
        self.cfg_base_url_entry = ttk.Entry(row4, textvariable=self.cfg_base_url, width=35)
        self.cfg_base_url_entry.pack(side="left")

        # 操作按钮
        btn_row = tk.Frame(parent, bg="#fafafa")
        btn_row.pack(fill="x", padx=8, pady=6)
        ttk.Button(btn_row, text="保存配置", command=self._save_config, width=12).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="测试连接", command=self._test_connection, width=12).pack(side="left")

        self._apply_config_to_fields(cfg)

    def _apply_config_to_fields(self, cfg: dict):
        """将配置值填入表单。"""
        provider = cfg.get("provider", "openai")
        provider_cfg = cfg.get(provider, {})

        self.cfg_enabled.set(cfg.get("enabled", False))
        self.cfg_provider.set(provider)

        # 解析 API key（支持 ${ENV} 格式）
        api_key = provider_cfg.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            self.cfg_api_key.set("")  # 环境变量不显示
        else:
            self.cfg_api_key.set(api_key)

        self.cfg_model.set(provider_cfg.get("model", ""))
        self.cfg_base_url.set(provider_cfg.get("base_url", provider_cfg.get("endpoint", "")))

    def _on_provider_change(self):
        """切换提供商时刷新表单。"""
        provider = self.cfg_provider.get()
        defaults = {
            "openai":   {"model": "gpt-4o", "base_url": "https://api.openai.com/v1"},
            "anthropic":{"model": "claude-sonnet-4-6", "base_url": ""},
            "ollama":   {"model": "llama3.2-vision", "base_url": "http://localhost:11434"},
            "custom":   {"model": "", "base_url": ""},
        }
        d = defaults.get(provider, {})
        self.cfg_model.set(d.get("model", ""))
        self.cfg_base_url.set(d.get("base_url", ""))
        self.cfg_api_key.set("")

    def _toggle_key_visibility(self):
        self._show_key = not self._show_key
        self.cfg_api_key_entry.configure(show="" if self._show_key else "*")

    def _toggle_settings(self):
        if self._settings_visible:
            self._settings_frame.pack_forget()
            self._settings_visible = False
        else:
            self._settings_frame.pack(fill="x", padx=15, pady=4)
            self._settings_visible = True

    def _save_config(self):
        """保存 AI 配置到 config.yaml 并重新初始化。"""
        try:
            import yaml

            provider = self.cfg_provider.get()
            api_key = self.cfg_api_key.get().strip()
            model = self.cfg_model.get().strip()
            base_url = self.cfg_base_url.get().strip()

            # 读取现有配置
            config_path = USER_DIR / "config.yaml"
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # 更新 AI 配置
            config.setdefault("ai", {})
            config["ai"]["enabled"] = self.cfg_enabled.get()
            config["ai"]["provider"] = provider
            config["ai"].setdefault(provider, {})
            config["ai"][provider]["api_key"] = api_key if api_key else config["ai"][provider].get("api_key", "")
            config["ai"][provider]["model"] = model
            if provider in ("openai", "ollama") and base_url:
                config["ai"][provider]["base_url"] = base_url
            elif provider == "custom" and base_url:
                config["ai"][provider]["endpoint"] = base_url

            # 写入
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            # 重新加载配置
            self.panel.assistant.config = config
            self.panel.assistant._init_ai_model()

            # 刷新状态
            self._refresh_status_label(self.win.winfo_children()[1])
            self._refresh_main_panel_ai_label()

            self._append_msg("system", "配置已保存并生效")

        except Exception as e:
            messagebox.showerror("保存失败", f"写入配置文件失败:\n{e}")

    def _test_connection(self):
        """测试 AI 连接。"""
        self._append_msg("system", "正在测试连接...")

        def _run():
            try:
                # 临时创建一个模型实例测试
                from core.ai_model import OpenAIModel, ClaudeModel, OllamaModel

                provider = self.cfg_provider.get()
                api_key = self.cfg_api_key.get().strip()
                model_name = self.cfg_model.get().strip()
                base_url = self.cfg_base_url.get().strip()

                if provider == "openai":
                    m = OpenAIModel(api_key=api_key, model=model_name, base_url=base_url or "https://api.openai.com/v1")
                elif provider == "anthropic":
                    m = ClaudeModel(api_key=api_key, model=model_name)
                elif provider == "ollama":
                    m = OllamaModel(base_url=base_url or "http://localhost:11434", model=model_name)
                elif provider == "custom":
                    m = OpenAIModel(api_key=api_key, model=model_name, base_url=base_url)
                else:
                    self._append_msg("error", f"不支持的提供商: {provider}")
                    return

                reply = m.chat([{"role": "user", "content": "Hi, reply with just 'ok'."}])
                self._append_msg("system", f"连接成功！响应: {reply[:100]}")
            except Exception as e:
                self._append_msg("error", f"连接失败: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _refresh_status_label(self, frame):
        """刷新状态标签。"""
        for w in frame.winfo_children():
            w.destroy()
        ai = self.panel.assistant.ai_model
        if ai:
            st = f"状态: {ai.name} / {getattr(ai, 'model', '?')}"
            color = "#27ae60"
        else:
            st = "状态: 未连接"
            color = "#e67e22"
        self.status_lbl = tk.Label(frame, text=st, fg=color, bg="#f0f0f0")
        self.status_lbl.pack(side="left")

    def _refresh_main_panel_ai_label(self):
        """刷新主面板的 AI 标签。"""
        ai = self.panel.assistant.ai_model
        if hasattr(self.panel, 'ai_label'):
            if ai:
                self.panel.ai_label.configure(
                    text=f"{ai.name} ({getattr(ai, 'model', '?')})",
                    fg="#27ae60")
            else:
                self.panel.ai_label.configure(text="未启用", fg="#e67e22")

    # ---------- AI 操作 ----------

    def _check_ai(self) -> bool:
        if self.panel.assistant.ai_model is None:
            self._append_msg("system", "AI 未启用。请在 config.yaml 中配置 AI 模型。")
            return False
        return True

    def _send_message(self):
        text = self.input_var.get().strip()
        if not text or not self._check_ai():
            return
        self.input_var.set("")
        self._append_msg("user", text)

        self.loading_lbl.configure(text="AI 思考中...")
        threading.Thread(target=self._do_chat, args=(text,), daemon=True).start()

    def _do_chat(self, text: str):
        try:
            self._history.append({"role": "user", "content": text})
            reply = self.panel.assistant.ai_model.chat(self._history)
            self._history.append({"role": "assistant", "content": reply})
            self._append_msg("ai", reply)
        except Exception as e:
            self._append_msg("error", f"AI 调用失败: {e}")
        finally:
            self.win.after(0, lambda: self.loading_lbl.configure(text=""))

    def _analyze_screen(self):
        if not self._check_ai():
            return
        ai = self.panel.assistant.ai_model
        if not ai.supports_vision:
            self._append_msg("system", "当前模型不支持视觉分析")
            return

        img = self.panel.assistant._capture()
        if img is None:
            self._append_msg("system", "截图失败，请确认游戏窗口已连接")
            return

        self._append_msg("user", "[分析当前游戏画面]")
        self.loading_lbl.configure(text="AI 分析画面中...")

        def _run():
            try:
                prompt = """分析这张梦幻西游游戏截图，请告诉我:
1. 当前在什么场景/地图
2. 有哪些可见的 NPC 或交互对象
3. 当前可能的任务状态
4. 建议的下一步操作"""
                result = ai.analyze_image(img, prompt)
                self._append_msg("ai", result)
            except Exception as e:
                self._append_msg("error", f"分析失败: {e}")
            finally:
                self.win.after(0, lambda: self.loading_lbl.configure(text=""))

        threading.Thread(target=_run, daemon=True).start()

    def _diagnose_error(self):
        if not self._check_ai():
            return
        task = self.panel.assistant.current_task
        img = self.panel.assistant._capture()

        context = ""
        if task:
            context = f"当前任务: {task.name} | 步骤: {task.current_step_name} | 状态: {task.state.value}"

        self._append_msg("user", f"[任务错误诊断] {context}")
        self.loading_lbl.configure(text="AI 诊断中...")

        def _run():
            try:
                prompt = f"""游戏自动化任务出现了问题。
{context}
请分析截图，判断:
1. 任务为什么卡住了
2. 当前游戏画面显示了什么
3. 建议如何恢复或重试"""
                result = self.panel.assistant.ai_model.analyze_image(img, prompt)
                self._append_msg("ai", result)
            except Exception as e:
                msg = f"诊断需要视觉模型，当前模型不支持: {e}"
                self._append_msg("error", msg)
            finally:
                self.win.after(0, lambda: self.loading_lbl.configure(text=""))

        if self.panel.assistant.ai_model.supports_vision and img is not None:
            threading.Thread(target=_run, daemon=True).start()
        else:
            self._append_msg("system", "诊断需要视觉模型，且需游戏窗口已连接")

    def _strategy_advice(self):
        if not self._check_ai():
            return

        task = self.panel.assistant.current_task
        task_info = f"当前: {task.name} / {task.current_step_name}" if task else "无运行中任务"
        self._append_msg("user", f"[游戏策略建议] {task_info}")
        self.loading_lbl.configure(text="AI 思考中...")

        def _run():
            try:
                prompt = f"""你是梦幻西游游戏策略专家。
{task_info}
请给出:
1. 当前任务的最佳执行策略
2. 效率优化建议
3. 常见注意事项"""
                reply = self.panel.assistant.ai_model.chat([
                    {"role": "user", "content": prompt},
                ])
                self._append_msg("ai", reply)
            except Exception as e:
                self._append_msg("error", f"AI 调用失败: {e}")
            finally:
                self.win.after(0, lambda: self.loading_lbl.configure(text=""))

        threading.Thread(target=_run, daemon=True).start()

    # ---------- 消息显示 ----------

    def _append_msg(self, role: str, text: str):
        def _do():
            self.chat_log.configure(state="normal")
            if role == "user":
                prefix = "▼ 你"
                tag = "user_tag"
            elif role == "ai":
                prefix = "▲ AI"
                tag = "ai_tag"
            elif role == "error":
                prefix = "✗ 错误"
                tag = "error_tag"
            elif role == "system":
                prefix = "● 系统"
                tag = "sys_tag"
            else:
                prefix = ""
                tag = ""

            self.chat_log.insert("end", f"{prefix}\n", tag)
            self.chat_log.insert("end", f"{text}\n\n", "msg")
            self.chat_log.see("end")
            self.chat_log.configure(state="disabled")

            self.chat_log.tag_configure("user_tag", foreground="#3498db", font=("Consolas", 8, "bold"))
            self.chat_log.tag_configure("ai_tag", foreground="#2ecc71", font=("Consolas", 8, "bold"))
            self.chat_log.tag_configure("error_tag", foreground="#e74c3c", font=("Consolas", 8, "bold"))
            self.chat_log.tag_configure("sys_tag", foreground="#f39c12", font=("Consolas", 8, "bold"))
            self.chat_log.tag_configure("msg", foreground="#d4d4d4")

        self.win.after(0, _do)


# ==================== YOLO 训练对话框 ====================

class YOLOTrainDialog:
    """YOLO 模型训练对话框。"""

    BASE_MODELS = {
        "YOLOv8 Nano (最快)": "yolov8n.pt",
        "YOLOv8 Small (推荐)": "yolov8s.pt",
        "YOLOv8 Medium (更准)": "yolov8m.pt",
    }

    def __init__(self, parent, panel: ControlPanel):
        self.panel = panel
        self.training = False
        self._train_thread = None

        self.win = tk.Toplevel(parent)
        self.win.title("训练 YOLO 模型")
        self.win.geometry("520x620")
        self.win.resizable(True, True)
        self.win.minsize(480, 480)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.win.configure(bg="#f0f0f0")

        # 标题栏（固定在顶部）
        tk.Label(self.win, text="YOLO 模型训练",
                font=("微软雅黑", 13, "bold"), fg="white", bg="#2c3e50",
                height=2).pack(fill="x")

        # 可滚动区域
        canvas_frame = tk.Frame(self.win, bg="#f0f0f0")
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(canvas_frame, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self._canvas.yview)
        self._scroll_frame = tk.Frame(self._canvas, bg="#f0f0f0")

        self._scroll_frame.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_frame_id = self._canvas.create_window(
            (0, 0), window=self._scroll_frame, anchor="nw")

        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮支持
        def _on_mousewheel(event):
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.win.bind("<Destroy>",
            lambda e: self._canvas.unbind_all("<MouseWheel>") if e.widget == self.win else None)

        # 宽度同步
        def _on_canvas_configure(event):
            self._canvas.itemconfig(self._canvas_frame_id, width=event.width)
        self._canvas.bind("<Configure>", _on_canvas_configure)

        self._build()
        self._refresh_dataset_stats()

    def _build(self):
        """构建所有 UI 区域到可滚动 frame 中。"""
        w = self._scroll_frame  # 所有子控件都 pack 到这个可滚动容器

        # 数据集信息
        self._build_dataset_section(w)
        ttk.Separator(w, orient="horizontal").pack(fill="x", padx=15, pady=5)

        # 类别管理
        self._build_class_section(w)
        ttk.Separator(w, orient="horizontal").pack(fill="x", padx=15, pady=5)

        # 云端训练
        self._build_cloud_section(w)
        ttk.Separator(w, orient="horizontal").pack(fill="x", padx=15, pady=5)

        # 训练参数
        self._build_params_section(w)
        ttk.Separator(w, orient="horizontal").pack(fill="x", padx=15, pady=5)

        # AI 辅助
        self._build_ai_assist_section(w)
        ttk.Separator(w, orient="horizontal").pack(fill="x", padx=15, pady=5)

        # 操作按钮
        self._build_action_section(w)

        # 训练进度
        self._build_progress_section(w)

    def _build_dataset_section(self, parent):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        tk.Label(frame, text="数据集状态", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        info_frame = tk.Frame(frame, bg="#f0f0f0")
        info_frame.pack(fill="x", pady=3)

        self.ds_train_label = tk.Label(info_frame, text="训练集: --",
                                       bg="#f0f0f0")
        self.ds_train_label.pack(side="left", padx=(0, 20))
        self.ds_val_label = tk.Label(info_frame, text="验证集: --", bg="#f0f0f0")
        self.ds_val_label.pack(side="left", padx=(0, 20))
        self.ds_class_label = tk.Label(info_frame, text="类别数: --", bg="#f0f0f0")
        self.ds_class_label.pack(side="left")

        btn_row = tk.Frame(frame, bg="#f0f0f0")
        btn_row.pack(fill="x", pady=3)
        ttk.Button(btn_row, text="打开数据集目录",
                  command=self._open_dataset_dir, width=18).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="截图并加入训练集",
                  command=self._capture_for_dataset, width=18).pack(side="left")

    def _build_class_section(self, parent):
        """类别管理：添加/删除 YOLO 检测类别（场景、NPC、怪物等）。"""
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        tk.Label(frame, text="类别管理", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        desc = tk.Label(frame, text="定义要检测的目标类别，会同步写入 data.yaml",
                       font=("微软雅黑", 7), fg="#7f8c8d", bg="#f0f0f0")
        desc.pack(anchor="w")

        # 列表 + 操作行
        list_row = tk.Frame(frame, bg="#f0f0f0")
        list_row.pack(fill="both", expand=True, pady=3)

        # 类别列表
        list_frame = tk.Frame(list_row, bg="#f0f0f0")
        list_frame.pack(side="left", fill="both", expand=True)
        class_scroll = ttk.Scrollbar(list_frame)
        class_scroll.pack(side="right", fill="y")
        self.class_listbox = tk.Listbox(
            list_frame, yscrollcommand=class_scroll.set,
            font=("微软雅黑", 9), height=5, exportselection=False,
            activestyle="dotbox",
        )
        class_scroll.configure(command=self.class_listbox.yview)
        self.class_listbox.pack(fill="both", expand=True)

        # 操作按钮
        btn_col = tk.Frame(list_row, bg="#f0f0f0")
        btn_col.pack(side="right", padx=(6, 0))
        ttk.Button(btn_col, text="＋ 添加", command=self._add_class,
                  width=10).pack(pady=(0, 3))
        ttk.Button(btn_col, text="－ 删除", command=self._remove_class,
                  width=10).pack(pady=(0, 3))
        ttk.Button(btn_col, text="✎ 改名", command=self._rename_class,
                  width=10).pack()

        # 添加输入行
        add_row = tk.Frame(frame, bg="#f0f0f0")
        add_row.pack(fill="x", pady=(3, 0))
        tk.Label(add_row, text="新类别名:", bg="#f0f0f0",
                font=("微软雅黑", 8)).pack(side="left")
        self.new_class_var = tk.StringVar()
        self.new_class_entry = ttk.Entry(add_row, textvariable=self.new_class_var, width=20)
        self.new_class_entry.pack(side="left", padx=4)
        self.new_class_entry.bind("<Return>", lambda e: self._add_class())
        ttk.Button(add_row, text="添加", command=self._add_class, width=6).pack(side="left")

        self._refresh_class_list()

    # ---------- 类别管理方法 ----------

    def _load_classes(self) -> dict:
        """从 data.yaml 加载类别，返回 {id: name} 字典."""
        data_yaml = DATASET_DIR / "data.yaml"
        if data_yaml.exists():
            try:
                import yaml
                with open(data_yaml, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                raw = cfg.get("names", {})
                if isinstance(raw, list):
                    return {i: n for i, n in enumerate(raw)}
                if isinstance(raw, dict):
                    return {int(k): v for k, v in raw.items()}
            except Exception:
                pass
        return {}

    def _save_classes(self, classes: dict):
        """将类别保存到 data.yaml。"""
        import yaml
        data_yaml = DATASET_DIR / "data.yaml"
        cfg = {}
        if data_yaml.exists():
            try:
                with open(data_yaml, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
            except Exception:
                pass
        classes = dict(sorted(classes.items()))
        cfg["names"] = classes
        cfg["nc"] = len(classes)
        with open(data_yaml, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
        self._refresh_class_list()
        self._refresh_dataset_stats()

    def _refresh_class_list(self):
        """刷新类别列表显示。"""
        classes = self._load_classes()
        self.class_listbox.delete(0, "end")
        if not classes:
            self.class_listbox.insert("end", "（尚未定义类别）")
        else:
            for cid, cname in classes.items():
                self.class_listbox.insert("end", f"  [{cid}] {cname}")

    def _add_class(self):
        """添加一个类别。"""
        name = self.new_class_var.get().strip()
        if not name:
            messagebox.showwarning("名称不能为空", "请输入类别名称，如: monster, button, portal")
            return
        classes = self._load_classes()
        if name in classes.values():
            messagebox.showwarning("名称重复", f"类别 '{name}' 已存在")
            return
        new_id = max(classes.keys(), default=-1) + 1
        classes[new_id] = name
        self._save_classes(classes)
        self.new_class_var.set("")
        self.panel.log(f"YOLO 类别已添加: [{new_id}] {name}", "train")

    def _remove_class(self):
        """删除选中的类别。"""
        sel = self.class_listbox.curselection()
        if not sel:
            messagebox.showwarning("未选择", "请先在列表中选择一个类别")
            return
        text = self.class_listbox.get(sel[0])
        if "[" not in text:
            return
        cid_str = text.split("]")[0].split("[")[1]
        cid = int(cid_str)
        classes = self._load_classes()
        if cid not in classes:
            return
        name = classes[cid]
        if not messagebox.askyesno("确认删除",
                                   f"删除类别 [{cid}] {name}？\n\n"
                                   f"⚠ 已有的标注文件不会自动更新，需要手动调整 label 中的 class id。"):
            return
        del classes[cid]
        self._save_classes(classes)
        self.panel.log(f"YOLO 类别已删除: [{cid}] {name}", "train")

    def _rename_class(self):
        """重命名选中的类别。"""
        sel = self.class_listbox.curselection()
        if not sel:
            messagebox.showwarning("未选择", "请先在列表中选择一个类别")
            return
        text = self.class_listbox.get(sel[0])
        if "[" not in text:
            return
        cid_str = text.split("]")[0].split("[")[1]
        cid = int(cid_str)
        classes = self._load_classes()
        if cid not in classes:
            return
        old_name = classes[cid]
        from tkinter import simpledialog
        new_name = simpledialog.askstring(
            "重命名类别", f"请输入 [{cid}] {old_name} 的新名称:",
            parent=self.win,
        )
        if new_name and new_name.strip() and new_name.strip() != old_name:
            classes[cid] = new_name.strip()
            self._save_classes(classes)
            self.panel.log(f"YOLO 类别已重命名: [{cid}] {old_name} → {new_name.strip()}", "train")

    def _build_params_section(self, parent):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        tk.Label(frame, text="训练参数", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        # 基础模型
        row1 = tk.Frame(frame, bg="#f0f0f0")
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="基础模型:", bg="#f0f0f0", width=10, anchor="w").pack(side="left")
        self.base_var = tk.StringVar(value="YOLOv8 Small (推荐)")
        base_cb = ttk.Combobox(row1, textvariable=self.base_var,
                               values=list(self.BASE_MODELS.keys()),
                               state="readonly", width=22)
        base_cb.pack(side="left")

        # 训练轮数
        row2 = tk.Frame(frame, bg="#f0f0f0")
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="训练轮数:", bg="#f0f0f0", width=10, anchor="w").pack(side="left")
        self.epochs_var = tk.IntVar(value=100)
        ttk.Spinbox(row2, from_=10, to=500, increment=10,
                   textvariable=self.epochs_var, width=8).pack(side="left")
        tk.Label(row2, text="(推荐 50-200)", font=("微软雅黑", 8),
                fg="#7f8c8d", bg="#f0f0f0").pack(side="left", padx=4)

        # 批大小
        row3 = tk.Frame(frame, bg="#f0f0f0")
        row3.pack(fill="x", pady=2)
        tk.Label(row3, text="批大小:", bg="#f0f0f0", width=10, anchor="w").pack(side="left")
        self.batch_var = tk.IntVar(value=8)
        ttk.Spinbox(row3, from_=1, to=64, increment=2,
                   textvariable=self.batch_var, width=8).pack(side="left")
        tk.Label(row3, text="(显存不足时减小)", font=("微软雅黑", 8),
                fg="#7f8c8d", bg="#f0f0f0").pack(side="left", padx=4)

        # 图像尺寸
        row4 = tk.Frame(frame, bg="#f0f0f0")
        row4.pack(fill="x", pady=2)
        tk.Label(row4, text="图像尺寸:", bg="#f0f0f0", width=10, anchor="w").pack(side="left")
        self.imgsz_var = tk.IntVar(value=640)
        ttk.Spinbox(row4, from_=320, to=1280, increment=32,
                   textvariable=self.imgsz_var, width=8).pack(side="left")

        # 设备
        row5 = tk.Frame(frame, bg="#f0f0f0")
        row5.pack(fill="x", pady=2)
        tk.Label(row5, text="训练设备:", bg="#f0f0f0", width=10, anchor="w").pack(side="left")
        self.device_var = tk.StringVar(value="cuda")
        device_frame = tk.Frame(row5, bg="#f0f0f0")
        device_frame.pack(side="left")
        ttk.Radiobutton(device_frame, text="GPU (CUDA)", variable=self.device_var,
                       value="cuda").pack(side="left", padx=(0, 8))
        ttk.Radiobutton(device_frame, text="CPU", variable=self.device_var,
                       value="cpu").pack(side="left")

    def _build_ai_assist_section(self, parent):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        header = tk.Frame(frame, bg="#f0f0f0")
        header.pack(fill="x")
        tk.Label(header, text="AI 辅助标注", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(side="left")

        # AI 状态显示
        ai = self.panel.assistant.ai_model
        if ai:
            ai_status = f"已连接 ({ai.name} / {getattr(ai, 'model', '?')})"
            ai_color = "#27ae60"
        else:
            ai_status = "未启用 (去 config.yaml 开启 ai.enabled)"
            ai_color = "#e67e22"
        self.ai_status_label = tk.Label(header, text=ai_status,
                                        font=("微软雅黑", 8), fg=ai_color, bg="#f0f0f0")
        self.ai_status_label.pack(side="left", padx=8)

        # 功能说明
        desc = tk.Frame(frame, bg="#f0f0f0")
        desc.pack(fill="x")
        tk.Label(desc, text="AI 可分析截图自动建议标注目标，辅助构建训练数据集",
                font=("微软雅黑", 8), fg="#7f8c8d", bg="#f0f0f0").pack(anchor="w")

        # 按钮行 1
        btn1 = tk.Frame(frame, bg="#f0f0f0")
        btn1.pack(fill="x", pady=3)

        ttk.Button(btn1, text="AI 分析当前画面",
                  command=self._ai_analyze_screen, width=20).pack(side="left", padx=(0, 8))
        ttk.Button(btn1, text="AI 建议类别定义",
                  command=self._ai_suggest_classes, width=20).pack(side="left", padx=(0, 8))
        ttk.Button(btn1, text="AI 验证标注质量",
                  command=self._ai_validate_labels, width=20).pack(side="left")

        # AI 分析结果输出
        self.ai_result_text = tk.Text(
            frame, height=4, width=50, state="disabled",
            font=("Consolas", 8), bg="#fafafa", fg="#2c3e50",
            wrap="word",
        )
        self.ai_result_text.pack(fill="x", pady=4)

    def _ai_analyze_screen(self):
        """AI 分析当前游戏截图。"""
        if not self._check_ai():
            return

        assistant = self.panel.assistant
        img = assistant._capture()
        if img is None:
            messagebox.showwarning("截图失败", "无法获取游戏画面")
            return

        data_yaml = DATASET_DIR / "data.yaml"
        existing = None
        if data_yaml.exists():
            try:
                import yaml
                with open(data_yaml) as f:
                    existing = yaml.safe_load(f).get("names", [])
            except Exception:
                pass

        self._set_ai_result("AI 正在分析截图...")
        self.panel.log("AI 分析当前画面...", "train")

        def _run():
            try:
                result = assistant.ai_model.suggest_labels(img, existing)
                self._show_ai_result(result)
                if "error" not in result:
                    self.panel.log("AI 分析完成", "train")
            except Exception as e:
                self._set_ai_result(f"分析失败: {e}")
                self.panel.log(f"AI 分析失败: {e}", "error")

        threading.Thread(target=_run, daemon=True).start()

    def _ai_suggest_classes(self):
        """AI 分析数据集并建议类别定义。"""
        if not self._check_ai():
            return

        train_img = DATASET_DIR / "images" / "train"
        screenshots = list(train_img.glob("*"))
        if not screenshots:
            messagebox.showwarning("无截图", "请先在训练集中添加截图")
            return

        data_yaml = DATASET_DIR / "data.yaml"
        existing = None
        if data_yaml.exists():
            try:
                import yaml
                with open(data_yaml) as f:
                    existing = yaml.safe_load(f).get("names", [])
            except Exception:
                pass

        self._set_ai_result("AI 正在分析数据集...")
        self.panel.log("AI 分析数据集建议类别...", "train")

        def _run():
            try:
                result = self.panel.assistant.ai_model.auto_describe_dataset(
                    [str(p) for p in screenshots], existing)
                self._show_ai_result(result)
                self.panel.log("AI 类别建议完成", "train")
            except Exception as e:
                self._set_ai_result(f"分析失败: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _ai_validate_labels(self):
        """AI 验证标注质量。"""
        if not self._check_ai():
            return

        # 选择一个标注文件
        label_dir = DATASET_DIR / "labels" / "train"
        img_dir = DATASET_DIR / "images" / "train"
        label_files = list(label_dir.glob("*.txt")) if label_dir.exists() else []
        if not label_files:
            messagebox.showwarning("无标注", "请先用 labelImg 标注一些图片")
            return

        # 随机选一个
        import random
        lf = random.choice(label_files)
        img_name = lf.stem
        img_path = None
        for ext in (".jpg", ".png", ".jpeg"):
            candidate = img_dir / (img_name + ext)
            if candidate.exists():
                img_path = str(candidate)
                break
        if not img_path:
            self._set_ai_result("找不到对应图片")
            return

        labels = lf.read_text().strip().split("\n")
        class_ids = set()
        for line in labels:
            if line.strip():
                cls_id = line.split()[0] if line.split() else ""
                class_ids.add(cls_id)

        self._set_ai_result(f"AI 正在验证: {lf.name} (类别IDs: {class_ids})...")

        def _run():
            try:
                result = self.panel.assistant.ai_model.validate_labels(
                    img_path, list(class_ids))
                self._show_ai_result(result)
                self.panel.log(f"AI 标注验证: {lf.name}", "train")
            except Exception as e:
                self._set_ai_result(f"验证失败: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _check_ai(self) -> bool:
        """检查 AI 模型是否可用。"""
        ai = self.panel.assistant.ai_model
        if ai is None:
            messagebox.showwarning("AI 未启用",
                                   "AI 模型未配置。\n\n请在 config.yaml 中设置:\n"
                                   "  ai.enabled: true\n"
                                   "  ai.provider: openai (或 ollama)\n"
                                   "  并填写对应的 api_key")
            return False
        if not ai.supports_vision:
            messagebox.showwarning("模型不支持", f"{ai.name} 不支持视觉分析")
            return False
        return True

    def _set_ai_result(self, text: str):
        def _set():
            self.ai_result_text.configure(state="normal")
            self.ai_result_text.delete("1.0", "end")
            self.ai_result_text.insert("1.0", text)
            self.ai_result_text.configure(state="disabled")
        self.win.after(0, _set)

    def _show_ai_result(self, result: dict):
        if "error" in result:
            text = f"✗ 分析失败: {result['error']}"
        else:
            import json
            text = json.dumps(result, ensure_ascii=False, indent=2)
        self._set_ai_result(text)

    def _build_action_section(self, parent):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)

        btn_frame = tk.Frame(frame, bg="#f0f0f0")
        btn_frame.pack(fill="x")

        self.train_btn = ttk.Button(btn_frame, text="开始训练",
                                    command=self._start_training, width=16)
        self.train_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ttk.Button(btn_frame, text="停止训练",
                                   command=self._stop_training, width=16,
                                   state="disabled")
        self.stop_btn.pack(side="left")

    def _build_progress_section(self, parent):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="both", expand=True, padx=15, pady=(4, 10))

        tk.Label(frame, text="训练进度", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(anchor="w")

        # 总体进度条
        pframe = tk.Frame(frame, bg="#f0f0f0")
        pframe.pack(fill="x", pady=2)
        self.train_progress = ttk.Progressbar(pframe, length=300)
        self.train_progress.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.train_progress_label = tk.Label(pframe, text="--",
                                             bg="#f0f0f0", width=10)
        self.train_progress_label.pack(side="right")

        # 训练日志
        self.train_log = scrolledtext.ScrolledText(
            frame, height=8, width=55, state="disabled",
            font=("Consolas", 8), bg="#1e1e1e", fg="#d4d4d4",
        )
        self.train_log.pack(fill="both", expand=True, pady=3)

        # ====== 云端存储 ======

    def _build_cloud_section(self, parent):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", padx=15, pady=8)
        header = tk.Frame(frame, bg="#f0f0f0")
        header.pack(fill="x")
        tk.Label(header, text="云端存储", font=("微软雅黑", 10, "bold"),
                bg="#f0f0f0").pack(side="left")
        cfg = self.panel.assistant.config.get("cloud_train", {})
        ttk.Button(header, text="保存配置",
                  command=self._cloud_save_config, width=10).pack(side="right")
        url_row = tk.Frame(frame, bg="#f0f0f0")
        url_row.pack(fill="x", pady=2)
        tk.Label(url_row, text="服务器:", bg="#f0f0f0", width=6, anchor="w").pack(side="left")
        self.cloud_url_var = tk.StringVar(value=cfg.get("server_url", "http://127.0.0.1:9527"))
        ttk.Entry(url_row, textvariable=self.cloud_url_var, width=36).pack(side="left", padx=4)
        ttk.Button(url_row, text="测试", command=self._cloud_test, width=6).pack(side="left")

        ds_label = tk.Label(frame, text="数据集", font=("微软雅黑", 9, "bold"), bg="#f0f0f0")
        ds_label.pack(anchor="w", pady=(5, 1))
        btn1 = tk.Frame(frame, bg="#f0f0f0")
        btn1.pack(fill="x")
        ttk.Button(btn1, text="上传到云端", command=self._cloud_upload_ds, width=14).pack(side="left", padx=(0, 5))
        ttk.Button(btn1, text="从云端下载", command=self._cloud_download_ds, width=14).pack(side="left", padx=(0, 5))
        ttk.Button(btn1, text="云端文件列表", command=self._cloud_list, width=14).pack(side="left")

        mdl_label = tk.Label(frame, text="模型", font=("微软雅黑", 9, "bold"), bg="#f0f0f0")
        mdl_label.pack(anchor="w", pady=(5, 1))
        btn2 = tk.Frame(frame, bg="#f0f0f0")
        btn2.pack(fill="x")
        ttk.Button(btn2, text="上传模型", command=self._cloud_upload_model, width=14).pack(side="left", padx=(0, 5))
        ttk.Button(btn2, text="下载模型", command=self._cloud_download_model, width=14).pack(side="left", padx=(0, 5))
        ttk.Button(btn2, text="删除云端文件", command=self._cloud_delete_file, width=14).pack(side="left")

        self.cloud_status_label = tk.Label(frame, text="", fg="#7f8c8d", bg="#f0f0f0", font=("微软雅黑", 8))
        self.cloud_status_label.pack(anchor="w", pady=(4, 0))

    def _cloud_save_config(self):
        try:
            import yaml
            config_path = USER_DIR / "config.yaml"
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            config.setdefault("cloud_train", {})
            config["cloud_train"]["server_url"] = self.cloud_url_var.get().strip()
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            self.panel.assistant.config = config
            self.panel.log("云端配置已保存", "task")
            self.cloud_status_label.configure(text="配置已保存")
        except Exception as e:
            self.cloud_status_label.configure(text=f"保存失败: {e}")

    def _cloud_test(self):
        cloud = self._get_cloud()
        if cloud:
            result = cloud.check_health()
            self.cloud_status_label.configure(
                text=f"连接成功 ({result.get('files', '?')} 个文件)" if result.get("ok") else "连接失败")
        else:
            self.cloud_status_label.configure(text="连接失败")

    def _get_cloud(self):
        try:
            from core.cloud import CloudStorage
            return CloudStorage(self.cloud_url_var.get().strip())
        except Exception as e:
            messagebox.showerror("云端连接失败", str(e))
            return None

    def _cloud_upload_ds(self):
        cloud = self._get_cloud()
        if not cloud: return
        self.cloud_status_label.configure(text="打包上传中...")
        def _run():
            r = cloud.upload_dataset(str(DATASET_DIR))
            msg = f"上传完成: {r.get('name','?')} ({r.get('size_mb',0)}MB)" if r.get("ok") else f"失败: {r.get('error')}"
            self.win.after(0, lambda: self.cloud_status_label.configure(text=msg))
            self.panel.log(msg, "train")
        threading.Thread(target=_run, daemon=True).start()

    def _cloud_download_ds(self):
        cloud = self._get_cloud()
        if not cloud: return
        files = cloud.list_files()
        datasets = [f for f in files if f["name"].startswith("dataset")]
        if not datasets:
            self.cloud_status_label.configure(text="云端没有数据集")
            return
        latest = datasets[0]
        self.cloud_status_label.configure(text=f"下载中: {latest['name']}")
        def _run():
            path = cloud.download(latest["name"], str(DATASET_DIR.parent))
            msg = f"已下载: {path}" if path else "下载失败"
            self.win.after(0, lambda: self.cloud_status_label.configure(text=msg))
            self.panel.log(msg, "train")
        threading.Thread(target=_run, daemon=True).start()

    def _cloud_upload_model(self):
        cloud = self._get_cloud()
        if not cloud: return
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="选择模型文件", filetypes=[("PyTorch model", "*.pt")])
        if not path: return
        self.cloud_status_label.configure(text="上传模型中...")
        def _run():
            r = cloud.upload(path)
            msg = f"上传完成: {r.get('name','?')}" if r.get("ok") else f"失败: {r.get('error')}"
            self.win.after(0, lambda: self.cloud_status_label.configure(text=msg))
            self.panel.log(msg, "train")
        threading.Thread(target=_run, daemon=True).start()

    def _cloud_download_model(self):
        cloud = self._get_cloud()
        if not cloud: return
        models = cloud.list_models()
        if not models:
            self.cloud_status_label.configure(text="云端没有模型")
            return
        latest = models[0]
        self.cloud_status_label.configure(text=f"下载中: {latest['name']}")
        def _run():
            save_dir = DATASET_DIR / "runs"
            save_dir.mkdir(parents=True, exist_ok=True)
            path = cloud.download(latest["name"], str(save_dir))
            msg = f"模型已保存: {path}" if path else "下载失败"
            self.win.after(0, lambda: self.cloud_status_label.configure(text=msg))
            if path:
                self.panel.log(msg, "task")
                self.win.after(0, lambda: self._update_config_model(path))
        threading.Thread(target=_run, daemon=True).start()

    def _cloud_list(self):
        cloud = self._get_cloud()
        if not cloud: return
        files = cloud.list_files()
        if not files:
            self.cloud_status_label.configure(text="云端没有文件")
            return
        lines = [f"{f['name']} ({f['size_mb']}MB, {f['date']})" for f in files[:10]]
        self.panel.log("云端文件:\n  " + "\n  ".join(lines), "train")
        self.cloud_status_label.configure(text=f"共 {len(files)} 个文件，详情见日志")

    def _cloud_delete_file(self):
        cloud = self._get_cloud()
        if not cloud: return
        files = cloud.list_files()
        if not files:
            self.cloud_status_label.configure(text="云端没有文件")
            return
        from tkinter import simpledialog
        names = [f["name"] for f in files]
        choice = simpledialog.askstring("删除文件", "输入要删除的文件名:\n" + "\n".join(names[:10]))
        if not choice: return
        r = cloud.delete(choice)
        msg = "删除成功" if r.get("ok") else f"失败: {r.get('error')}"
        self.cloud_status_label.configure(text=msg)
        self.panel.log(msg, "train")


# ==================== 数据集操作 ====================

    def _refresh_dataset_stats(self):
        """刷新数据集统计。"""
        train_img = DATASET_DIR / "images" / "train"
        val_img = DATASET_DIR / "images" / "val"
        data_yaml = DATASET_DIR / "data.yaml"

        train_count = len(list(train_img.glob("*"))) if train_img.exists() else 0
        val_count = len(list(val_img.glob("*"))) if val_img.exists() else 0

        self.ds_train_label.configure(text=f"训练集: {train_count} 张")
        self.ds_val_label.configure(text=f"验证集: {val_count} 张")

        # 读取类别数
        if data_yaml.exists():
            try:
                import yaml
                with open(data_yaml, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                nc = cfg.get("nc", 0)
                raw_names = cfg.get("names", [])
                # 兼容 dict 格式 {0: 'cursor', 1: 'npc'} 和 list 格式 ['cursor', 'npc']
                if isinstance(raw_names, dict):
                    names = list(raw_names.values())
                else:
                    names = raw_names
                self.ds_class_label.configure(
                    text=f"类别: {nc} ({', '.join(names) if names else '未定义'})")
            except Exception as e:
                self.ds_class_label.configure(text=f"类别: 读取失败 ({e})")

        # 如果数据集为空，提示
        if train_count == 0:
            self._append_train_log("⚠ 训练集为空！请先采集截图并标注。\n")
            self._append_train_log("  1. 点击 [截图并加入训练集] 采集游戏画面\n")
            self._append_train_log("  2. 用标注工具(labelImg)标注后放入 labels/train/\n")

    def _open_dataset_dir(self):
        os.makedirs(DATASET_DIR, exist_ok=True)
        os.startfile(str(DATASET_DIR))

    def _capture_for_dataset(self):
        """截取当前游戏画面并加入训练集。会提示选择对应的类别。"""
        assistant = self.panel.assistant
        img = assistant._capture()
        if img is None:
            messagebox.showwarning("截图失败", "无法获取游戏画面，请确保游戏窗口已连接。")
            return

        import cv2
        from tkinter import simpledialog

        # 询问截图类别
        classes = self._load_classes()
        if classes:
            labels = [f"[{cid}] {cname}" for cid, cname in classes.items()]
            labels.append("（不指定类别）")
            choice = simpledialog.askstring(
                "选择类别",
                f"当前类别:\n" + "\n".join(labels) + "\n\n"
                f"输入类别 ID 数字或名称关键词来标记这张截图。\n"
                f"直接回车 = 不指定类别",
                parent=self.win,
            )
            class_tag = ""
            if choice and choice.strip():
                choice = choice.strip()
                # 尝试匹配类别 ID
                try:
                    cid = int(choice)
                    if cid in classes:
                        class_tag = f"_{classes[cid]}"
                except ValueError:
                    # 尝试模糊匹配名称
                    for cname in classes.values():
                        if cname.lower() in choice.lower():
                            class_tag = f"_{cname}"
                            break
                    if not class_tag:
                        class_tag = f"_{choice}"
        else:
            class_tag = ""

        train_img_dir = DATASET_DIR / "images" / "train"
        train_img_dir.mkdir(parents=True, exist_ok=True)

        existing = list(train_img_dir.glob("*.jpg")) + list(train_img_dir.glob("*.png"))
        idx = len(existing) + 1
        name = f"{idx:04d}{class_tag}.jpg"
        path = train_img_dir / name
        cv2.imwrite(str(path), img)

        msg = f"截图已加入训练集: {name} (共 {idx} 张)"
        if class_tag:
            msg += f" — 类别: {class_tag[1:]}"
        self.panel.log(msg, "train")
        self._append_train_log(f"✓ 已添加: {name}\n")
        self._refresh_dataset_stats()

    # ==================== 训练控制 ====================

    def _start_training(self):
        train_img = DATASET_DIR / "images" / "train"
        if not train_img.exists() or len(list(train_img.glob("*"))) == 0:
            messagebox.showwarning("数据集为空",
                                   "训练集没有图片！\n\n请先点击 [截图并加入训练集] 采集游戏画面，\n然后用标注工具标注后放入 labels/train/。")
            return

        # 检查 GPU 可用性
        device = self.device_var.get()
        if device != "cpu":
            try:
                import torch
                if not torch.cuda.is_available():
                    if not messagebox.askyesno(
                        "GPU 不可用",
                        f"PyTorch 未检测到 CUDA GPU。\n\n"
                        f"当前 PyTorch 版本: {torch.__version__}\n"
                        f"{'⚠ 这是 CPU 版本，不支持 GPU 训练' if '+cpu' in torch.__version__ else '⚠ CUDA 不可用'}\n\n"
                        f"修复方法:\n"
                        f"  1. 卸载 CPU 版本: pip uninstall torch torchvision -y\n"
                        f"  2. 安装 CUDA 版本:\n"
                        f"     pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124\n\n"
                        f"是否临时使用 CPU 继续训练？\n"
                        f"(CPU 训练会慢很多，但不需要 GPU)"
                    ):
                        return
                    self.device_var.set("cpu")
            except ImportError:
                pass

        self.training = True
        self.train_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.train_progress["value"] = 0
        self.train_progress_label.configure(text="准备中...")
        self.train_log.configure(state="normal")
        self.train_log.delete("1.0", "end")
        self.train_log.configure(state="disabled")

        self.panel.log("开始 YOLO 模型训练...", "train")
        self._append_train_log("=" * 50 + "\n")
        self._append_train_log("  YOLO 模型训练\n")
        self._append_train_log("=" * 50 + "\n")

        self._train_thread = threading.Thread(target=self._do_training, daemon=True)
        self._train_thread.start()

    def _stop_training(self):
        if self.training:
            self.training = False
            self._append_train_log("\n⚠ 训练已手动停止\n")
            self.panel.log("训练已手动停止", "warn")
            self.train_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    def _do_training(self):
        """在后台线程中执行训练。"""
        try:
            import subprocess
            import yaml

            base_name = self.BASE_MODELS[self.base_var.get()]
            epochs = self.epochs_var.get()
            batch = self.batch_var.get()
            imgsz = self.imgsz_var.get()
            device = self.device_var.get()
            name = f"mhxy_train_{datetime.now().strftime('%Y%m%d_%H%M')}"

            self._append_train_log(f"基础模型: {base_name}\n")
            self._append_train_log(f"训练轮数: {epochs}\n")
            self._append_train_log(f"批大小:   {batch}\n")
            self._append_train_log(f"图像尺寸: {imgsz}\n")
            self._append_train_log(f"设备:     {device}\n")
            self._append_train_log(f"任务名:   {name}\n\n")

            # 检查基础模型是否存在
            base_path = DATASET_DIR / base_name
            if not base_path.exists():
                self._append_train_log(f"下载基础模型 {base_name}...\n")
                self.win.after(0, lambda: self.train_progress_label.configure(
                    text="下载模型中..."))

            script = DATASET_DIR / "train_yolo.py"
            cmd = [
                sys.executable, str(script),
                "--base", str(base_path) if base_path.exists() else base_name,
                "--epochs", str(epochs),
                "--batch", str(batch),
                "--imgsz", str(imgsz),
                "--device", device,
                "--name", name,
            ]

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"  # 防止子进程 GBK 编码错误

            self._append_train_log("开始训练...\n\n")

            # Ultralytics 自定义 TQDM 用 \r（而非 \n）更新进度条，
            # 所以不能用 for line in process.stdout（只认 \n）。
            # 另开线程读管道，主循环用 Queue 轮询，确保手动停止能被及时响应。
            process = subprocess.Popen(
                cmd, cwd=str(DATASET_DIR), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )

            import queue as _queue

            chunk_queue: _queue.Queue = _queue.Queue()

            def _read_stdout():
                try:
                    while True:
                        chunk = process.stdout.read(4096)
                        if not chunk:
                            chunk_queue.put(None)
                            break
                        chunk_queue.put(chunk)
                except Exception:
                    chunk_queue.put(None)

            reader = threading.Thread(target=_read_stdout, daemon=True)
            reader.start()

            buf = ""
            eof = False
            while not eof:
                try:
                    chunk = chunk_queue.get(timeout=0.3)
                except _queue.Empty:
                    if not self.training:
                        process.terminate()
                        process.wait()
                        break
                    continue

                if chunk is None:
                    eof = True
                    if buf.strip():
                        self._parse_training_line(buf.strip())
                    break

                text = chunk.decode("utf-8", errors="replace")
                buf += text

                # 按 \r 或 \n 分割
                while True:
                    pos = min(
                        (i for i, c in enumerate(buf) if c in "\r\n"),
                        default=-1,
                    )
                    if pos < 0:
                        break
                    line = buf[:pos]
                    sep = buf[pos]
                    buf = buf[pos + 1:]
                    if sep == "\r" and buf.startswith("\n"):
                        buf = buf[1:]  # \r\n → 跳过一个 \n
                    line = line.strip()
                    if line:
                        self._parse_training_line(line)
                        self._append_train_log(line + "\n")

            if self.training:
                process.wait()

            if self.training:
                # 训练成功
                best_pt = DATASET_DIR / "runs" / "detect" / name / "weights" / "best.pt"
                if best_pt.exists():
                    self._append_train_log(f"\n✓ 训练完成！模型已保存: {best_pt}\n")
                    self.panel.log(f"训练完成: {best_pt}", "task")

                    # 自动更新 config.yaml
                    self._update_config_model(str(best_pt))

                    self.win.after(0, lambda: self.train_progress_label.configure(
                        text="100%"))
                    self.win.after(0, lambda: self.train_progress.configure(value=100))
                else:
                    self._append_train_log("\n✗ 训练异常：模型文件未生成\n")
            else:
                self._append_train_log("\n训练已取消\n")

        except subprocess.TimeoutExpired:
            self._append_train_log("\n✗ 训练超时\n")
        except Exception as e:
            self._append_train_log(f"\n✗ 训练异常: {e}\n")
            self.panel.log(f"训练异常: {e}", "error")
        finally:
            self.training = False
            self.win.after(0, lambda: self.train_btn.configure(state="normal"))
            self.win.after(0, lambda: self.stop_btn.configure(state="disabled"))

    def _parse_training_line(self, line: str):
        """解析 YOLO 训练输出行，提取进度信息。

        Ultralytics 8.x 输出格式示例:
              1/100      0G      1.23      2.34      1.45          8        640: 100%|█| 20/20 [00:15<00:00,  1.33it/s]
              1/100      0G      1.18      2.29      1.41         16        640: 100%|█| 10/10 [00:08<00:00,  1.25it/s]

        旧版格式:
              Epoch 5/100  ──── 12s 4.5s/iter ...
        """
        import re
        line = line.strip()
        if not line:
            return

        # 匹配行首的 epoch 进度，如 "1/100" 或 "  1/100"
        m = re.match(r"(\d+)/(\d+)\s", line)
        if m:
            cur, total = m.group(1), m.group(2)
            try:
                cur_i, total_i = int(cur), int(total)
                pct = cur_i / total_i * 100
                self.win.after(0, lambda p=pct: self.train_progress.configure(value=p))
                self.win.after(0, lambda c=cur, t=total:
                    self.train_progress_label.configure(text=f"Epoch {c}/{t}"))
            except (ValueError, ZeroDivisionError):
                pass
            return

        # 兼容旧版 "Epoch 5/100" 格式
        if line.startswith("Epoch"):
            parts = line.split()
            if len(parts) >= 2:
                epoch_info = parts[1]
                if "/" in epoch_info:
                    cur, total = epoch_info.split("/")
                    try:
                        pct = int(cur) / int(total) * 100
                        self.win.after(0, lambda p=pct: self.train_progress.configure(value=p))
                        self.win.after(0, lambda c=cur, t=total:
                            self.train_progress_label.configure(text=f"Epoch {c}/{t}"))
                    except (ValueError, ZeroDivisionError):
                        pass

    def _append_train_log(self, text: str):
        """线程安全地追加训练日志。"""
        def _append():
            self.train_log.configure(state="normal")
            self.train_log.insert("end", text)
            self.train_log.see("end")
            self.train_log.configure(state="disabled")
        self.win.after(0, _append)

    def _update_config_model(self, model_path: str):
        """更新 config.yaml 中的模型路径。"""
        try:
            config_path = USER_DIR / "config.yaml"
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            config["yolo"]["model_path"] = model_path

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            self.panel.model_label.configure(text=model_path)
            self.panel.log(f"已更新 config.yaml: yolo.model_path = {model_path}", "task")

            # 提示重新初始化
            if messagebox.askyesno("训练完成",
                                   f"模型已保存并更新配置。\n\n"
                                   f"是否重新加载 YOLO 模型？"):
                self.panel.assistant._init_yolo()
                self.panel.log("YOLO 模型已重新加载", "info")

        except Exception as e:
            self.panel.log(f"更新配置失败: {e}", "error")

    def _on_close(self):
        if self.training:
            if not messagebox.askyesno("训练进行中", "训练尚未完成，确定关闭吗？"):
                return
            self.training = False
        self.win.destroy()
        self.panel._train_window = None

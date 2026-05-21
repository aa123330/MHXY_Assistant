# 梦幻西游 AI 辅助 — 开发交接文档

## 2026-05-21 更新记录

### 直接更换框架决策

- 用户已确认：允许不保留 Python 能力层，但必须保留原项目全部功能。
- 主框架选型：**C#/.NET 8 WPF + OpenCvSharp + ONNX Runtime + Win32 P/Invoke**。
- 不选择 MaaFramework 纯资源项目作为主框架：
  - Maa 的 pipeline 思路适合借鉴，但无法完整承接当前 AI 助手、YOLO 训练、云端、诊断、复杂战斗状态机。
- 不选择 Tauri/Rust 作为第一阶段：
  - 包体可控，但 Windows 截图/输入/OCR/ONNX 维护成本高。
- 已新增 `src/` 新框架骨架：
  - `MhxyAssistant.Core`：窗口、输入、截图、视觉、任务接口。
  - `MhxyAssistant.App`：WPF 主窗口和任务入口。
- 已安装 .NET SDK 8.0.421；当前 shell 的 PATH 未刷新，使用 `C:\Program Files\dotnet\dotnet.exe` 可编译。
- 新框架已通过 `dotnet build src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release --no-restore`，0 警告 0 错误。
- 详细迁移方案见 `docs/framework-migration.md`。

### 追加参考项目优化

- 参考项目：
  - `huiyadanli/bettergi-docs`
  - `IrisRainbowNeko/genshin_autoplay_domain`
  - `infstellar/genshin_impact_assistant`
  - `1bananachicken/MaaNTE`
  - `daoqi/MintNTE`
  - `BnanZ0/ok-nte`
- 采纳方向：
  - 借鉴 BetterGI / Maa 系列的问题排查方式，新增诊断包导出。
  - 借鉴 `genshin_autoplay_domain` 的 YAML 动作脚本思想，新增轻量 `ActionScriptRunner`，但不引入 YOLOX/mmtracking/MAAFramework 等重依赖。
  - 借鉴这类项目对分辨率强约束的经验，窗口绑定后会提示客户区尺寸与 `config.yaml.game.window_size` 不一致的风险。
- 新增文件：
  - `core/diagnostics.py`：导出 `debug/diagnostics/diagnostics_*.zip`，包含脱敏配置、窗口信息、环境信息、MSS 截图样本、后台截图样本和黑屏比例。
  - `core/action_script.py`：支持 `click`、`hotkey/key`、`wait`、`until_template`、`ocr_contains`、`log` 等基础动作。
- UI 更新：
  - 调试工具栏新增“导出诊断包”按钮。
- 任务层更新：
  - `BaseTask.run_action_script(script_path)` 可直接执行 YAML 动作脚本，后续可把师门/抓鬼/押镖里的重复点击等待流程逐步迁移到 `data/scripts/*.yaml`。

### 本轮优化范围

- 仍以 **YOLOv8** 作为项目内置训练和推理路线；不内置 YOLO11，不提升依赖去追 YOLO11。
- `killbero/-YOLOv11-CS-` 只作为视觉辅助项目参考：借鉴鼠标 dead zone、闭环定位、DXGI/后台截图思路，不复用其 CS2 模型权重。
- 主截图路线保持“前台可见窗口 + 客户区 MSS 截图”；后台截图作为可选 fallback，不作为默认路径。

### 鼠标输入优化

- `core/input.py`
  - `click()` 新增 `bounds` 参数，随机偏移后的点击点会被限制在目标窗口客户区内，避免靠边按钮被 jitter 抖出窗口。
  - 新增 `_set_pos_precise()`：SendInput 移动后读取当前鼠标坐标，若偏差超过容忍值会做 1-2 次轻量修正。
  - `dead_zone` 改为按原始目标点计算，而不是按 jitter 后的随机点计算，减少不必要移动。
  - 保留 SendInput 主线，不引入 PyAutoGUI/PyDirectInput 作为新依赖。

### 窗口绑定和坐标优化

- `core/window.py`
  - 新增 `is_window_valid()`、`is_window_minimized()`、`get_foreground_window()`。
  - 新增 `client_to_screen()`、`screen_to_client()`、`is_point_in_client()`，明确客户区坐标与屏幕坐标边界。
  - `verify_click_window()` 现在会先确认窗口有效、未最小化，并确认点击点落在客户区内。
- `main.py`
  - `_refresh_window_rects()` 会在截图/点击前检查窗口句柄是否仍然有效，以及窗口是否最小化。
  - `_click_game()` 会把客户区屏幕边界传给输入层，约束随机点击偏移。

### 截图后端优化

- `core/capture.py`
  - 新增 `capture_window_client_bg(hwnd)`：优先 `PrintWindow(PW_CLIENTONLY | PW_RENDERFULLCONTENT)` 截客户区，失败后退回客户区偏移 BitBlt。
  - `capture_region()` 对非法宽高直接报错，避免传入 0 或负数区域。
- `config.yaml`
  - 新增：
    ```yaml
    capture:
      prefer_background: false
    ```
  - 默认仍使用 MSS 前台客户区截图；只有手动开启 `prefer_background` 时才优先尝试后台客户区截图。

### YOLO 和打包优化

- `core/detector.py`
  - 模型加载后会输出实际类别列表，并和 `config.yaml` 里的期望类别做比对。
  - 如果加载了外部模型但类别不匹配，会打印警告，避免“能加载但识别语义不对”的问题。
- `yolo_dataset/train_yolo.py`
  - 修复 UI 传入 `--device` 但训练脚本不接收的问题。
  - 默认基础模型保持 `yolov8s.pt`。
- `build_installer.spec` / `build_exe.spec`
  - 打包时自动收集 `yolo_dataset/yolov8*.pt`。
  - 支持把业务模型放在 `yolo_dataset/models/*.pt` 随包收集。
  - 修复 `build_exe.spec` 中 `PACKAGE_ML` 未定义的问题。
- `.gitignore`
  - 忽略 `yolo_dataset/models/*.pt`，避免大模型误提交。

### 2026-05-21 打包瘦身重构

- 参考项目：
  - `babalae/better-genshin-impact`
  - `1bananachicken/MaaNTE`
  - `daoqi/MintNTE`
- 结论：
  - 这些项目发布包较小，关键不是单纯压缩，而是把运行时、资源、模型、训练工具链拆开。
  - 本项目之前默认把 PaddleOCR/PaddlePaddle/Torch/Ultralytics/训练权重一起打进安装包，是 2GB+ 的主要原因。
- 已落地：
  - 默认依赖改为 Lite 运行时：截图、窗口、输入、模板、颜色、脚本、诊断。
  - 新增 `requirements-ml.txt`，OCR/YOLO/训练相关依赖改为可选。
  - `setup_deps.bat` 默认只安装基础依赖；`setup_deps.bat full` 才安装 PaddleOCR、Torch、Ultralytics。
  - `build_installer.bat` / `build_exe.bat` 默认构建 Lite 包；传入 `full` 或 `ml` 才构建完整 ML 包。
  - `build_installer.spec` / `build_exe.spec` 的 `PACKAGE_ML` 默认关闭。
  - Lite 包不再收集 `yolo_dataset/*.pt`、`runs/detect/*/weights`、Paddle/Torch/Cython 大型文件。
  - `core/__init__.py` 不再导入 `core.detector`，避免启动和 Lite 打包时误拉起 ultralytics/torch 导入链。
  - `tasks/zhuogui.py` 改用 `core.input.hotkey()`，移除默认 `pyautogui` 依赖。
  - Lite 打包时强制排除 `torch/torchvision/paddle/paddleocr/ultralytics/Cython`，避免 PyInstaller 从 UI/训练代码的可选导入误收集 ML 栈。
- 推荐发布策略：
  - 默认发 `MHXY_Assistant_Lite` 安装包。
  - 需要 YOLO/OCR/训练时，再发 `MHXY_Assistant_Full` 或后续做成 ML 扩展包。
  - 中长期参考 BetterGI 的资产包方案，为模板、脚本、模型增加 manifest 和版本号。
  - 中长期参考 MaaNTE/MintNTE，把稳定点击流程资源化，Python 只保留复杂识别和决策 Provider。
- 本轮 Lite 打包验证：
  - `dist/MHXY_Assistant`：约 255 MB。
  - `dist/installer/梦幻视觉辅助_Setup.exe`：约 57 MB。
  - 包内已无 `torch`、`paddle`、`ultralytics`、`Cython` 目录。

### 本轮验证

```bash
python -m py_compile core\input.py core\window.py core\capture.py core\__init__.py core\detector.py main.py ui\panel.py yolo_dataset\train_yolo.py build_exe.spec build_installer.spec
python yolo_dataset\train_yolo.py --help
```

## 一、项目概述

基于图像识别（截图 + OCR + 模板匹配 + 感知哈希 + YOLOv8）的梦幻西游 PC 版自动辅助工具。
不读写游戏内存，纯视觉方案。

| 项目 | 信息 |
|------|------|
| 语言 | Python 3.12（切勿用 3.14） |
| 架构 | 三层：core（底层能力）→ game（游戏理解）→ tasks（任务脚本） |
| GUI | tkinter（Python 自带） |
| 打包 | PyInstaller → 单文件 EXE |
| 云存储 | Flask 文件服务（119.91.225.128:9527） |

## 二、在新机器上搭建开发环境

### 2.1 安装 Python

1. 下载 Python 3.12：https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"
3. 验证：`py -3.12 --version`

### 2.2 拉取代码

```bash
git clone <repo-url>
cd mhxy_assistant
```

### 2.3 安装依赖

```bash
# 基础依赖（Lite 运行时，vendor 目录，开发+打包通用）
setup_deps.bat

# 可选：完整 ML 环境（OCR/YOLO/训练）
setup_deps.bat full

# 打包
py -3.12 -m pip install pyinstaller
```

### 2.4 启动

```bash
py -3.12 bootstrap.py        # UI 模式
py -3.12 bootstrap.py --cli  # 命令行模式
双击 launcher.vbs            # 无控制台窗口启动
```

## 三、目录结构

```
mhxy_assistant/
├── bootstrap.py          ← 启动入口（vendor 路径 + PyInstaller 兼容）
├── main.py               ← 主控引擎（Assistant 类）
├── config.yaml           ← 全局配置
│
├── core/                 ← 底层能力
│   ├── paths.py          #   路径工具（开发/打包双模式）
│   ├── window.py         #   窗口查找/激活/移动（win32gui + 正则匹配）
│   ├── capture.py        #   截图（mss 前屏 + win32 BitBlt 后台双模式）
│   ├── input.py          #   键鼠（pywin32 直连优先，拟人减速移动，点击后随机移开）
│   ├── template.py       #   OpenCV 模板匹配 + 6方法共识匹配
│   ├── hasher.py         #   感知哈希快速图像匹配（<1ms，借鉴 mhxy_fz）
│   ├── ocr.py            #   PaddleOCR 封装（懒加载，兼容 2.x 和 3.x API）
│   ├── detector.py       #   YOLOv8 目标检测（可降级，类型标注安全）
│   ├── scene.py          #   场景检测（多模板匹配）
│   ├── color_detect.py   # ★ 颜色像素快速检测（红字定位、战斗UI、对话框检测）
│   ├── ai_model.py       #   AI 模型抽象层（OpenAI/Claude/Ollama/Custom）
│   ├── cloud.py          #   云端存储客户端（上传/下载/列表/删除）
│   └── __init__.py       #   容错导入（★ detector 必须在 ocr 之前，避免 DLL 冲突）
│
├── game/                 ← 游戏理解层
│   ├── constants.py      #   常量（GameState、YOLO类映射、快捷键）
│   ├── state.py          #   状态机（哈希→YOLO→场景模板→像素 四级检测）
│   ├── battle.py         #   战斗（弹窗选人 + 6方法共识 + 智能目标选择）
│   ├── minimap.py        #   小地图→世界地图定位
│   ├── map.py            #   A* 寻路 + 路径简化
│   ├── npc.py            #   NPC 查找与对话
│   └── __init__.py
│
├── tasks/                ← 任务脚本
│   ├── base.py           #   任务基类（Step + BaseTask + 异常处理 + 注册表）
│   ├── shimen.py         # ★ 师门任务（6种类型识别 + 全流程）
│   ├── zhuogui.py        #   捉鬼任务
│   ├── plot.py           # ★ 剧情任务（颜色+OCR双重定位 + 螺旋修正点击）
│   ├── patrol.py         #   巡逻任务
│   ├── escort.py         # ★ 押镖任务（接镖→护送→交镖）
│   └── __init__.py
│
├── ui/                   ← 图形界面
│   ├── panel.py          #   主面板 + AI助手 + YOLO训练对话框 + 云端存储
│   └── __init__.py
│
├── server/               ← 云端存储服务
├── yolo_dataset/         ← YOLO 训练流水线
├── data/                 ← 数据（templates/hashes/maps/quests）
├── debug/                ← 调试截图
├── vendor/               ← pip 依赖（numpy 锁定 1.26.4）
├── dist/                 ← 打包输出
│
├── launcher.bat / .vbs   ← 启动（纯英文，避免编码问题）
├── setup_deps.bat        ← 依赖安装
├── debug_run.bat         ← 诊断
├── build_exe.bat / .spec ← 打包
└── DEVELOPMENT.md        ← 本文件
```

## 四、核心架构

### 4.1 启动流程

```
launcher.vbs → launcher.bat → py -3.12 bootstrap.py
  → setup_vendor()          # vendor/ → sys.path
  → cv2.setLogLevel 抑制    # try/except 保护
  → pywin32 预检             # 缺失时给出中文提示并退出
  → from main import Assistant
    → core/__init__.py      # detector(torch) 先于 ocr(paddle) 导入
    → 各子模块容错导入
  → from ui.panel import ControlPanel
    → 创建 tkinter 窗口
    → assistant.init()      # 查找窗口 → 初始化子系统
  → panel.run()             # tkinter 主循环
```

### 4.2 关键导入顺序

`core/__init__.py` 中 **detector (torch) 必须在 ocr (paddle) 之前导入**。
原因: PaddlePaddle 的 oneDNN/MKL DLL 会与 PyTorch 的 shm.dll 冲突。
先加载 torch 再加载 paddle 可避免 OSError 127。

### 4.3 状态检测（四级链）

```
感知哈希(1ms) → YOLO检测(50ms) → 场景模板(100ms) → 像素特征(20ms)
    ↑ 借鉴 mhxy_fz      ↑ menghuanxiyou        ↑            ↑ 兜底
```

新增: `core/color_detect.py` 提供更快颜色像素检测（<1ms），用于战斗UI/对话框/红字快速判断。

### 4.4 鼠标点击流程（融合 10 参考项目）

```
click(x, y, verify=check, dead_zone=10, human=True)
  → get_pos() 检测距离
  → dead_zone: 已在目标 10px 内则跳过移动 (YOLOv11-CS)
  → _move_bezier() 贝塞尔弧形移动 / 直连定位 (SimuTouch 增强)
  → sleep(0.3s) 等游戏响应 (mhxy-escort)
  → _click_si() SendInput ctypes left down+up (SimuTouch + AutoControl)
  → sleep(0.2s) 等注册
  → _move_away() 随机移开 25-50px (mhxy-escort 防悬停检测)
  → 如有 verify: 最多 retry 2 次 (hermes-agent closed-loop)
```

- **SendInput via ctypes**: INPUT/MOUSEINPUT 结构体 + 0-65535 绝对坐标映射 (SimuTouch + AutoControl + ScreenChangeShockDevice)
- **贝塞尔曲线移动**: 二阶贝塞尔 + 随机控制点偏移 (SimuTouch 增强, 100Hz 插值)
- **Dead zone**: 鼠标已在目标附近则跳过移动 (YOLOv11-CS)
- **verify 回调**: post-action 验证 + retry (hermes-agent)
- **GetMessageExtraInfo**: 点击事件注入自定义元数据 (AutoControl)
- **相对移动**: SendInput MOUSEEVENTF_MOVE (SimuTouch + YOLOv11-CS)
- **DPI 修正**: GetDpiForSystem 自动检测缩放 (hermes-agent)

### 4.5 像素变化检测（core/detect.py）

借鉴 ScreenChangeShockDevice 的 numpy diff 方案：

```
pixel_diff(img1, img2) → (changed, x, y)  # 第一处不同像素 (~0.05ms)
wait_for_change()      → 阻塞等待区域变化
wait_for_stable()       → 等待画面稳定（加载完成）
verify_disappeared()    → 验证 UI 是否已消失
```

### 4.6 窗口管理增强（core/window.py）

借鉴 windows-manager 的 Win32 窗口能力：

- `set_topmost(hwnd)` — SetWindowPos + HWND_TOPMOST
- `window_from_point(x, y)` — WindowFromPoint 点击位置验证
- `verify_click_window(x, y, hwnd)` — 验证点击是否落在目标窗口
- `enum_child_windows(hwnd)` — 枚举游戏子窗口
- `get_window_process_name(hwnd)` — 获取窗口进程名

### 4.7 任务调度系统（tasks/base.py）

- **TaskState 状态机**: IDLE → RUNNING → COMPLETED/ERROR/CANCELLED
- **@register_task 装饰器**: 全局任务注册表，自动发现任务
- **handle_anomalies()**: 每 tick 前置异常处理（借鉴 lua-touchsprite）
- **递增回退重试**: 每次重试间隔递增（0.5s, 1s, 1.5s）
- **连续错误保护**: MAX_CONSECUTIVE_ERRORS=5 上限

### 4.6 剧情任务点击策略（tasks/plot.py）

```
① 颜色检测优先: find_red_text_center() 找红色像素中心 (精确)
② OCR 辅助: PaddleOCR 获取文字内容
③ 螺旋修正点击:
   第1次 x@75% + y-2 → 第2次 x@70% + y-4 → 第3次 x@80% + y0
   → 第4次 x@65% + y-6 → 第5次 x@50% + y+2
④ 每次点击后验证: 重新OCR检查目标是否消失
```

### 4.7 路径系统

`core/paths.py` — 所有模块统一走此接口：

| 函数 | 开发模式 | EXE模式 |
|------|---------|---------|
| `get_source_dir()` | 项目根 | exe内部(只读) |
| `get_user_dir()` | 项目根 | exe旁边(可写) |
| `ensure_dirs(...)` | 创建目录 | 创建目录 |

### 4.8 云端存储

服务器（119.91.225.128:9527）部署 Flask 文件存储，API：
- `POST /api/upload` — 上传文件
- `GET /api/list` — 文件列表
- `GET /api/download/<name>` — 下载
- `DELETE /api/delete/<name>` — 删除

## 五、常见开发场景

### 加新任务
1. `tasks/xxx.py` 继承 `BaseTask`，实现 `build_steps()`
2. 加 `@register_task("xxx")` 装饰器自动注册
3. 在 `ui/panel.py` 加按钮 + `_start_task` names 映射

### 加新 AI 提供商
1. `core/ai_model.py` 继承 `BaseAIModel`，实现 `chat()` + `_vision_chat()`
2. 注册到 `create_ai_model()` 工厂函数

### 加新检测方法
1. `game/state.py` 的 `_detect()` 中加入新检测层
2. 按速度排序（快的在前）
3. 快速颜色检测可用 `core/color_detect.py`

### 添加场景模板
1. UI 上点"采集场景模板"按钮
2. 自动截图 → OCR + AI 分析场景 → 建议名称 → 保存到 `data/templates/scenes/`
3. 或手动放 PNG 文件到该目录，文件名即场景名

### 调试模块
```bash
py -3.12 -c "import sys; sys.path.insert(0,'vendor'); sys.path.insert(0,'.'); ..."
```
用 `debug_run.bat` 逐步检查依赖。

## 六、打包

```bash
# 确认 pyinstaller 安装在系统 Python 3.12
py -3.12 -m pip install pyinstaller pywin32

# 默认 Lite 安装包：不包含 Paddle/Torch/Ultralytics/YOLO 权重
build_installer.bat

# 完整 ML 安装包：包含 Paddle/Torch/Ultralytics 和运行权重
build_installer.bat full

# 单文件 Lite 调试包
build_exe.bat

# 单文件 Full 调试包，不推荐作为主发布形态
build_exe.bat full
```

主发布建议使用 `build_installer.spec` 的 onedir 安装包。Paddle/Torch 这类 native 依赖在 onefile 下容易变成超大 `_MEI` 解包目录，也更容易漏 Cython/Paddle 运行文件。

## 七、已知坑点速查

| 症状 | 原因 | 解决 |
|------|------|------|
| Lite 包找不到 YOLO/OCR | 默认包不再包含 ML 依赖 | 用 `setup_deps.bat full` + `build_installer.bat full` |
| `OSError 127 shm.dll` | paddle/torch DLL 冲突 | Full 包中保持 YOLO/OCR 懒加载，避免启动时同时加载 |
| `numpy.sctypes removed` | numpy 2.x 不兼容 PaddleOCR 2.x | vendor numpy 锁定 1.26.4 |
| `gbk codec can't decode` | Windows GBK 编码 ≠ Ultralytics Unicode 输出 | subprocess 显式 `encoding="utf-8", errors="replace"` |
| 训练进度条不动 | Ultralytics TQDM 用 `\r` 不分 `\n` | 二进制读管道手动切分 `\r`/`\n` |
| 停止训练进程残留 | `process.stdout.read()` 阻塞不可中断 | 独立线程读管道 + Queue 轮询 |
| PaddleOCR 3.x `predict() got unexpected keyword argument 'cls'` | API 不兼容 | 用 2.9.1，或 `core/ocr.py` 自动 try/except |
| 打包后 EXE 闪退 | pywin32 没装 OR numpy 版本冲突 | build_exe.bat 已含 pywin32；vendor numpy 锁 1.x |
| bat 中文乱码 | UTF-8 文件被 GBK CMD 解析 | 所有 bat 文件用纯英文 |
| 场景显示 "--" | 无场景模板 | 用"采集场景模板"按钮添加 |
| 点击位置偏右下 | OCR bbox 比实际红字宽 | 改颜色检测优先 + 螺旋修正 X+Y |
| 点击后不触发寻路 | 点击太快游戏没响应 | click() 等 0.3s 再点，点完等 0.2s |

## 八、参考项目（14 个）

| 项目 | 参考内容 |
|------|---------|
| YiFei-GitHub/menghuanxiyou | YOLO方案、场景检测、师门实战、GDI截图、模板匹配 |
| BestBurning/mhxy | 6方法投票匹配、CNN角色分类、弹窗选人 |
| haungwanjun/mhxy_fz | 感知哈希、win32api直连、极简轮询 |
| wuliangyue/mhxy-escort | A*地图寻路、NPC模板匹配、防检测弹窗处理、鼠标拟人移动 |
| WangQingye/lua-touchsprite-mhxy | 任务调度表、颜色多点检测UI、随机点击偏移、异常前置处理 |
| killbero/YOLOv11-CS | Dead zone、PID控制、DXGI GPU截屏、不瞎点 |
| xiao-fz/SimuTouch | SendInput ctypes、100Hz插值平滑移动、相对移动系统 |
| jiangxiao642-spec/hermes-agent | Two-tier视觉验证、closed-loop retry、DPI修正、SendInput PowerShell |
| autumnsj/AutoControl | SendInput(move)+mouse_event(click)混合、GetMessageExtraInfo |
| yx179971/ursa-frontend | 节点工作流理念 |
| Alone-zj/XYSpy | 全局热键坐标捕获 |
| DiurnalMoon256/windows-manager | WindowFromPoint、HWND_TOPMOST、EnumChildWindows |
| mojoin/ScreenChangeShockDevice | mss高速截图、numpy像素diff、SendInput绝对坐标 |
| DexYang/GDXY2 | 资源文件格式 |
| lvjincheng1998/JCXY | MMORPG架构参考 |
 
## 九、.NET 8 WPF 框架迁移进度

已按“直接更换框架、不保留 Python 能力层”的方向创建新工程：

- `src/MhxyAssistant.Core`：核心服务、窗口绑定、截图、输入、视觉检测、任务状态机
- `src/MhxyAssistant.App`：WPF 主程序壳、任务按钮、截图、诊断包入口
- `docs/framework-migration.md`：框架迁移路线图

当前技术栈：WPF、Win32 P/Invoke、OpenCvSharp、ONNX Runtime、Inno Setup。

本轮已迁移/补强：

- `TaskStep` 改为异步 Step runner，支持 `Next`、`Repeat`、`RestartFromFirst`、`CompleteTask`、`FailTask`
- Step 支持超时、重试、backoff、取消令牌，后续任务按 `Plot -> Escort -> Shimen` 迁移
- `ColorDetector` 迁移红字、对话框、战斗 UI、HSV 颜色比例检测
- 新增 `ImageHasher` 感知哈希
- 新增 `ScreenChangeDetector` 画面变化检测
- `TemplateMatcher.MatchAll` 改为真实多目标匹配，并做重叠抑制
- 诊断包导出修复 nullable struct 编译问题

验证命令：

```powershell
$env:DOTNET_CLI_HOME='F:\codex\mhxy_assistant\.dotnet_home'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:APPDATA='F:\codex\mhxy_assistant\.appdata'
$env:NUGET_PACKAGES='F:\codex\mhxy_assistant\.nuget\packages'
& 'C:\Program Files\dotnet\dotnet.exe' restore src\MhxyAssistant.App\MhxyAssistant.App.csproj -r win-x64
& 'C:\Program Files\dotnet\dotnet.exe' build src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release --no-restore
& 'C:\Program Files\dotnet\dotnet.exe' publish src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -p:PublishTrimmed=false -o dist\MHXY_Assistant_Net
ISCC installer\mhxy_assistant.iss
```

当前验证结果：

- Release build：0 warning / 0 error
- 干净 .NET 发布目录：`dist/MHXY_Assistant_Net`，约 268 MB
- Inno 安装包：`dist/installer/梦幻视觉辅助_Setup.exe`，约 77.5 MB
- 安装器支持选择安装路径、开始菜单/桌面快捷方式、卸载入口
- 快捷方式名称：`梦幻视觉辅助`
- 图标：`assets/mhxy_icon.ico`

注意：旧的 `dist/MHXY_Assistant` 可能残留 PyInstaller 产物，不能再作为新安装包输入目录。新安装包输入目录固定为 `dist/MHXY_Assistant_Net`，`build_dotnet_installer.bat` 会清理并重新发布该目录。

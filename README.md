# 梦幻视觉辅助

梦幻视觉辅助是面向梦幻西游 PC 版的 .NET 8 WPF 辅助工具。项目已经从旧 Python/Tkinter/PyInstaller 运行层迁移到 C#/.NET，主程序不再依赖 PaddleOCR、Torch、Ultralytics 或 Tcl/Tk，因此发布目录保持在约 268 MB。

## 当前状态

- 主程序：`src/MhxyAssistant.App`，WPF 桌面应用。
- 核心库：`src/MhxyAssistant.Core`，窗口绑定、截图、输入、视觉识别、任务状态机。
- 配置：`config.yaml`。
- 资源：`data/`、`assets/`。
- 安装器：`installer/mhxy_assistant.iss` + `build_dotnet_installer.bat`。
- 可选工具：`tools/ml` 用于 YOLO 训练/自动标注，`tools/cloud-server` 用于本地云端文件服务。

## 功能

- 窗口绑定与安全点击：绑定梦幻西游窗口，客户端坐标转换为屏幕坐标后再点击，防止误点其他窗口。
- 截图能力：前台截图、`PrintWindow` 后台截图和 BitBlt fallback。
- 视觉识别：Windows OCR、模板匹配、颜色检测、多点找色特征库、感知哈希、ONNX YOLO 推理接口。
- 任务：师门、捉鬼、剧情、巡逻、押镖已迁移为可重复推进的状态机。
- 战斗：基础攻击/技能/防御、弹窗选目标、YOLO/OCR/中心点兜底选怪。
- 工具窗口：AI 助手、YOLO 训练/自动标注、云端上传下载、诊断包导出。

## 开发环境

- Windows 10/11
- .NET 8 SDK
- 可选：Inno Setup 6，用于生成安装包
- 可选：Python 3.12 + ultralytics/opencv-python，用于 `tools/ml` 训练和自动标注

## 构建

```powershell
$env:DOTNET_CLI_HOME='F:\codex\mhxy_assistant\.dotnet_home'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:APPDATA='F:\codex\mhxy_assistant\.appdata'
$env:NUGET_PACKAGES='F:\codex\mhxy_assistant\.nuget\packages'
& 'C:\Program Files\dotnet\dotnet.exe' build src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release --no-restore
```

## 发布

```powershell
& 'C:\Program Files\dotnet\dotnet.exe' publish src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -p:PublishTrimmed=false -o dist\MHXY_Assistant_Net --no-restore
```

发布目录：`dist/MHXY_Assistant_Net`。

## 安装包

```bat
build_dotnet_installer.bat
```

安装包输出：`dist\installer\梦幻视觉辅助_Setup.exe`。
安装器支持选择安装路径、创建快捷方式和卸载。

## 使用

1. 打开梦幻西游 PC 版，并保持 800x600 窗口模式。
2. 启动 `MHXY_Assistant.exe`。
3. 点击“绑定窗口”。
4. 先用“截图”和“导出诊断”确认窗口、截图、OCR 状态正常。
5. 再逐个运行剧情、巡逻、师门、捉鬼、押镖任务。


## 轻量颜色特征识别

参考 `Asunxu/mhxy-automation-mac` 的思路，主程序现在支持非 YOLO 的多点找色特征库。配置项：

```yaml
vision_features:
  enabled: true
  feature_library_path: data/features/page.txt
```

特征库格式兼容常见触动/FreeGame 风格：

```text
feature_name={0xRRGGBB,"dx|dy|0xRRGGBB,dx|dy|0xRRGGBB",85,x1,y1,x2,y2};
```

常见按钮、弹窗关闭、继续/确定、NPC 或怪物入口可以优先用颜色特征识别。YOLO 仍保留为可选 ONNX 兜底，不再是主程序必须依赖。

建议使用流程：

1. 用主界面的“截图”保存当前游戏画面。
2. 从截图中取目标按钮的主颜色和 2-5 个偏移点颜色。
3. 将规则写入 `data/features/page.txt`。
4. 重新运行任务，让任务流先尝试颜色特征，再退回 OCR/模板/YOLO。

## YOLO 模型

主程序只加载 ONNX 模型：

```yaml
yolo:
  enabled: true
  model_path: models/yolo/best.onnx
```

`.pt` 模型只用于 `tools/ml` 训练，不会被 .NET 主程序加载。训练完成后请将模型导出为 ONNX，再放到 `models/yolo/best.onnx` 或修改 `config.yaml`。

## 可选工具

YOLO 训练：

```powershell
python tools/ml/train_yolo.py --base yolov8n.pt --epochs 100 --device cpu
```

自动标注：

```powershell
python tools/ml/auto_label.py --model path/to/best.pt --images debug/screenshots --conf 0.5
```

本地云端服务：

```powershell
pip install -r tools/cloud-server/requirements.txt
python tools/cloud-server/train_server.py
```

## 目录说明

```text
assets/                  图标等静态资源
config.yaml              主程序配置
data/                    模板、脚本、任务数据
docs/                    迁移和设计文档
installer/               Inno Setup 脚本
src/MhxyAssistant.App    WPF 应用
src/MhxyAssistant.Core   核心服务和任务逻辑
tools/ml                 可选 YOLO 训练/自动标注工具
tools/cloud-server       可选本地云端文件服务
```

## 清理说明

旧 Python 主运行层已经移除，包括 `core/`、`game/`、`tasks/`、`ui/`、`tcl/`、`main.py`、`bootstrap.py`、旧 PyInstaller 脚本和 vendor 依赖。当前仓库以 .NET/WPF 为唯一主程序。

## 已知限制

- Windows OCR 依赖系统 OCR 语言包，识别质量需要真实游戏画面校准。
- 师门、捉鬼、押镖跨地图细节仍需要实机日志和截图继续调参。
- `data/features/page.txt` 目前只提供格式模板，真实按钮和目标特征需要根据本机游戏截图补齐。
- ONNX YOLO 需要用户提供导出的 `.onnx` 模型并启用配置。

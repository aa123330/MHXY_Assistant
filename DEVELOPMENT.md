# DEVELOPMENT 交接文档

更新时间：2026-05-21

## 项目现状

项目已从旧 Python/Tkinter/PyInstaller 主运行层迁移到 C#/.NET 8 WPF。当前仓库以 .NET/WPF 为唯一主程序，旧 Python 主应用代码已经清理。

保留的 Python 文件仅作为可选工具：

- `tools/ml`：YOLO 训练和自动标注脚本。
- `tools/cloud-server`：本地云端文件服务。

主程序不再依赖 PaddleOCR、Torch、Ultralytics、Tcl/Tk 或 PyInstaller vendor 运行时。

## 当前目录

```text
assets/                  应用图标等静态资源
config.yaml              主配置
build_dotnet_installer.bat
                         发布并生成 Inno 安装包
data/                    模板、任务数据、动作脚本
docs/                    迁移设计文档
installer/               Inno Setup 脚本
src/Directory.Build.props
src/MhxyAssistant.App    WPF 应用层
src/MhxyAssistant.Core   核心服务、视觉识别、任务状态机
tools/ml                 可选 YOLO 训练/自动标注工具
tools/cloud-server       可选本地云端文件服务
```

已删除的旧运行层：

- `core/`
- `game/`
- `tasks/`
- `ui/`
- `tcl/`
- `vendor/`
- `main.py`
- `bootstrap.py`
- `launcher.bat` / `launcher.vbs`
- 旧 PyInstaller 打包脚本和 `requirements*.txt`

## 技术栈

- UI：.NET 8 WPF
- 窗口/输入：Win32 P/Invoke、SendInput
- 截图：CopyFromScreen、PrintWindow、BitBlt fallback
- 视觉：OpenCvSharp、模板匹配、颜色检测、多点找色、感知哈希、Windows OCR、ONNX Runtime
- 配置：YamlDotNet 加载 `config.yaml`
- 安装：dotnet publish + Inno Setup

## 已迁移功能

### 主程序

- WPF 主窗口、任务列表、日志区、截图、诊断包、AI、YOLO 训练、云端窗口。
- `AppConfigLoader` 加载 `config.yaml`，支持从输出目录、当前目录和父级目录查找。
- 发布目录与安装包链路已验证。

### 窗口、截图、鼠标

- `WindowService`：窗口标题/正则匹配、激活、客户区坐标、窗口有效性检测。
- `CaptureService`：客户区截图、后台截图、`PrintWindow -> BitBlt` fallback。
- `InputService`：SendInput 鼠标点击/热键，修复右下边界 clamp 越界。
- `TaskContext.ClickClient`：客户端坐标先转屏幕坐标，并验证点位仍在绑定窗口内。

### 视觉识别

### 轻量特征路线

已参考 `Asunxu/mhxy-automation-mac` 的核心思路接入多点找色：

- `MultiColorFeatureDetector` 解析 `data/features/page.txt`。
- `ColorFeatureRule` / `ColorFeatureMatch` 作为统一模型。
- `TaskContext.ColorFeatures` 暴露给任务流。
- `TaskFlow.TryClickFeature` 在部分流程中优先尝试颜色特征，再退回 OCR/模板/YOLO。

这条路线适合弹窗关闭、固定 UI 按钮、继续/确定、任务列表项等稳定目标，优点是无需模型文件、启动快、发布体积低。后续应基于真实截图补齐 `page.txt` 特征点。

交接注意：

- `data/features/page.txt` 已放入格式模板，当前未填真实游戏特征点。
- 特征命名建议直接使用任务流关键词，例如 `继续`、`确定`、`交付`、`npc`、`ghost`、`button`，这样 `TaskFlow.TryClickFeature` 能自动优先命中。
- 采集特征时优先选固定 UI 元素和高对比度边缘，避免选动态光效、人物遮挡区域和半透明阴影。
- 如果颜色特征误点，先收紧搜索区域，再提高 similarity，最后再增加偏移点数量。

- `WindowsOcrService`：Windows OCR，支持 `ocr.lang`，失败时降级为空 OCR。
- `YoloOnnxDetector`：ONNX Runtime 推理、letterbox、NMS、类别映射。
- `StateDetector`：hash/dialog/battle/template/yolo fallback。
- `TemplateMatcher`、`ColorDetector`、`ImageHasher`、`ScreenChangeDetector` 已迁移。

### 任务和战斗

- 师门、捉鬼、剧情、巡逻、押镖已迁移为 `StepTaskBase` 状态机。
- 任务共享 `TaskFlow`：任务追踪红字/OCR 点击、模板路径解析、对话推进、交付、巡逻辅助。
- `BasicBattleHandler`：弹窗选目标、默认攻击/技能/防御、YOLO/OCR/屏幕中心兜底选怪、失败后键盘兜底。

### 工具窗口

- AI 助手：OpenAI-compatible `/models` 连接测试和 `/chat/completions` 聊天测试。
- YOLO 训练/自动标注：通过外部 Python 进程运行 `tools/ml` 脚本，流式日志，支持停止。
- 云端：`HttpCloudStorage` 支持 health/list/upload/download/delete，并兼容旧 Flask 服务 `size_mb/date` 字段。

## YOLO 策略

主程序只加载 ONNX：

```yaml
yolo:
  enabled: true
  model_path: models/yolo/best.onnx
```

`.pt` 只用于 `tools/ml` 训练，不会被 WPF 主程序加载。当前默认配置为：

```yaml
yolo:
  enabled: false
  model_path: models/yolo/best.onnx
```

这样可以避免把 Python/Ultralytics/Torch/Paddle 重新打进主安装包。

## 构建验证

推荐使用固定 .NET 路径：

```powershell
$env:DOTNET_CLI_HOME='F:\codex\mhxy_assistant\.dotnet_home'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:APPDATA='F:\codex\mhxy_assistant\.appdata'
$env:NUGET_PACKAGES='F:\codex\mhxy_assistant\.nuget\packages'
& 'C:\Program Files\dotnet\dotnet.exe' build src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release --no-restore
```

当前验证结果：

- Build：0 errors。
- 仅有 `NU1900` 警告，原因是当前环境无法访问 NuGet 漏洞元数据。

## 发布和安装包

发布：

```powershell
& 'C:\Program Files\dotnet\dotnet.exe' publish src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -p:PublishTrimmed=false -o dist\MHXY_Assistant_Net --no-restore
```

安装包：

```bat
build_dotnet_installer.bat
```

当前发布目录约 268 MB。安装包输出到 `dist/installer/梦幻视觉辅助_Setup.exe`，支持选择安装路径、创建快捷方式和卸载。

## 清理记录

本次清理完成：

- 删除旧 Python 主应用层和 Tcl/Tk 运行时。
- 删除旧 PyInstaller 打包脚本、vendor 依赖、Python 缓存。
- 将 `yolo_dataset` 整理为 `tools/ml`。
- 将 `server` 整理为 `tools/cloud-server`。
- 更新 WPF 默认工具路径到 `tools/ml`。
- 更新 README 和交接文档为 .NET/WPF 结构。

## 仍需实机验证

这些不是编译问题，而是需要真实游戏窗口、截图和日志校准：

- Windows OCR 在游戏字体下的命中率。
- `data/features/page.txt` 真实特征库采集和命中率验证。
- 任务追踪区域、模板阈值、红字点击偏移。
- 师门、捉鬼、押镖跨地图推进细节。
- 战斗弹窗模板、YOLO 类名和目标选择策略。
- ONNX 模型导出后与 `YoloOnnxDetector` 输出格式的兼容性。

## 下一步建议

1. 打开游戏，先用截图和诊断包确认窗口绑定、前后台截图、OCR 结果。
2. 依次跑剧情、巡逻、战斗、师门、捉鬼、押镖。
3. 每个失败点保存诊断包和日志，再调模板、区域、OCR 关键词和点击偏移。
4. 优先补齐 `data/features/page.txt` 的稳定按钮/弹窗/目标特征。
5. 训练或导出 ONNX YOLO 后，把 `config.yaml` 的 `yolo.enabled` 改为 `true` 并实测。

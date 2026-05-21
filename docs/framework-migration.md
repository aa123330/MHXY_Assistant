# 框架迁移方案

目标是从 Python/Tkinter/PyInstaller 迁移到 C#/.NET 8 WPF。新框架不保留 Python 能力层，旧 Python 代码只作为功能对照与回归参考。

## 目标技术栈

- UI：WPF
- 窗口/输入：Win32 P/Invoke、SendInput
- 截图：CopyFromScreen、PrintWindow，后续可补 Windows Graphics Capture
- 模板/颜色：OpenCvSharp
- OCR：PP-OCR/RapidOCR ONNX 或 Windows OCR，通过 `IOcrService` 封装
- YOLO：YOLOv8 导出 ONNX，通过 ONNX Runtime 推理
- 安装：dotnet publish + Inno Setup

## 当前完成

- 新建 `src/MhxyAssistant.Core` 和 `src/MhxyAssistant.App`
- WPF 主窗口、任务注册表、窗口绑定、截图、输入服务已落地
- 任务 Step runner 已支持超时、重试、取消和流程跳转
- 颜色检测、红字定位、对话框检测、战斗 UI 检测已迁移
- 模板多目标匹配和重叠抑制已实现
- 感知哈希与画面变化检测已实现
- 诊断包导出已接入 WPF
- .NET 发布目录与 Inno 安装包已验证

## 下一步迁移顺序

1. 继续迁移 `PlotTask`：任务追踪栏扫描、点击目标、等待对话/战斗/到达。
2. 迁移 `EscortTask`：接镖、护送、返回、轮次重启。
3. 迁移 `ShimenTask`：20 轮循环、OCR 分类、任务 handler 分发。
4. 新增 `StateDetector`：hash quick check、YOLO、模板、颜色 fallback。
5. 新增 `BattleHandler`：战斗检测、普通攻击闭环、弹窗选人。
6. 接入 ONNX OCR/YOLO 推理。
7. 迁移 AI 助手、YOLO 数据集管理和云端模型下载。

## 打包

推荐使用：

```bat
build_dotnet_installer.bat
```

脚本会：

1. 清理 `dist\MHXY_Assistant_Net`
2. `dotnet publish` 生成 win-x64 自包含发布目录
3. 调用 Inno Setup 生成 `dist\installer\梦幻视觉辅助_Setup.exe`

当前验证：

- 发布目录约 268 MB
- 安装包约 77.5 MB
- 安装后快捷方式名称为 `梦幻视觉辅助`
- 安装包使用 `assets\mhxy_icon.ico`

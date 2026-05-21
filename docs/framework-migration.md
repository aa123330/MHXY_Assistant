# 框架迁移记录

项目已完成从旧 Python/Tkinter/PyInstaller 主运行层到 C#/.NET 8 WPF 的框架迁移。当前主程序位于 `src/MhxyAssistant.App`，核心能力位于 `src/MhxyAssistant.Core`。

## 迁移后的架构

- `MhxyAssistant.App`：WPF UI、窗口入口、工具窗、设置保存。
- `MhxyAssistant.Core`：窗口绑定、截图、输入、视觉识别、任务状态机、云端客户端。
- `data/`：模板、任务数据、动作脚本。
- `tools/ml`：可选 YOLO 训练/自动标注工具。
- `tools/cloud-server`：可选本地云端文件服务。

## 关键取舍

- 不保留 Python 主运行层，减少包体和运行时复杂度。
- 不再打包 PaddleOCR、Torch、Ultralytics、Tcl/Tk、PyInstaller vendor。
- OCR 默认使用 Windows OCR，后续如需要可扩展 ONNX/RapidOCR 实现。
- YOLO 推理只接受 ONNX 模型；`.pt` 只用于训练工具。
- 安装包使用 dotnet publish + Inno Setup。

## 已完成

- WPF 主界面和工具窗口。
- 配置加载、窗口绑定、截图、鼠标输入安全入口。
- 模板匹配、颜色检测、多点找色特征库、感知哈希、Windows OCR、ONNX YOLO detector。
- 状态检测、基础战斗处理。
- 师门、捉鬼、剧情、巡逻、押镖任务状态机。
- AI 助手、YOLO 训练/自动标注、云端 UI 接入。
- 发布目录和安装包构建验证。

## 当前限制

- 需要真实游戏环境继续调 OCR、模板阈值、点击偏移和任务流程。
- `data/features/page.txt` 已接入多点找色解析和任务流优先点击，但真实特征点仍需按本机截图采集。
- ONNX YOLO 需要用户提供导出后的模型；稳定 UI 目标优先建议用 `data/features/page.txt` 多点找色降低模型依赖。
- `tools/ml` 和 `tools/cloud-server` 是可选开发/训练工具，不属于主程序运行依赖。

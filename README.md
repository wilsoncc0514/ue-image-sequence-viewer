# 图形序列查看器（UE）

一款基于 Python、Tkinter 和 Pillow 的图像帧序列质检工具，支持序列浏览、Tag 标注、CSV 导入导出、异步渲染与帧预加载。

当前版本：**v3.6.1**

## 功能

- 按目录和文件名前缀组织图像序列。
- 使用键盘、滑块快速浏览连续帧。
- 记录光影问题、构图问题、质检状态和重新渲染要求。
- 导入、导出带 BOM 的 UTF-8 CSV 文件。
- 异步渲染与邻近帧预加载，降低大序列浏览延迟。
- 后台目录扫描支持进度、取消和资源上限。
- CSV 采用事务式导入与原子导出，失败时保留旧状态和旧文件。
- 兼容 PNG、JPEG、TIFF、BMP 和 WebP。

## 环境要求

- Python 3.10 或更高版本
- Tkinter（通常随 Python 一同安装）
- Pillow 12.3.0（已在 `requirements.txt` 固定）

## 安装与运行

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 图形序列查看器/main.py
```

如果项目所在路径包含冒号 `:`，Python `venv` 会拒绝在该路径创建环境。请将虚拟环境放到不含冒号的位置，例如：

```bash
python3 -m venv /tmp/ue-viewer-venv
source /tmp/ue-viewer-venv/bin/activate
python3 -m pip install -r requirements.txt
```

Windows 激活虚拟环境：

```powershell
.venv\Scripts\activate
```

如需关闭非必要动效（例如远程桌面、性能较弱的设备或自动化测试）：

```bash
UE_VIEWER_REDUCE_MOTION=1 python3 图形序列查看器/main.py
```

Windows PowerShell：

```powershell
$env:UE_VIEWER_REDUCE_MOTION = "1"
python 图形序列查看器/main.py
```

运行时也可在「设置 → 减少动态效果」中切换，macOS 快捷键为 `⌘,`，其他平台为 `Ctrl+,`。该菜单选项仅对当前运行会话生效；环境变量启用时会强制减少动态效果，菜单中不可关闭。

## 测试

```bash
cd 图形序列查看器
python3 -m unittest discover -s tests -v
```

## 项目结构

```text
图形序列查看器/
├── config/     # 配置及性能参数
├── core/       # CSV、渲染、序列状态与 Tag 规则
├── models/     # Tag 定义
├── tests/      # 单元测试
├── tools/      # 发布打包工具
├── ui/         # Tkinter 界面
├── utils/      # 日志、异常和通用辅助函数
└── main.py     # 程序入口
```

版本变化见 [CHANGELOG.md](CHANGELOG.md)。

## 兼容性与限制

- GitHub Actions 已配置 Python 3.10、3.12 和 3.14/Linux 矩阵；发布前以实际 CI 结果为准。
- macOS 为主要开发平台；Windows GUI 仍需每个重要版本进行实机验收。
- 默认拒绝超过 16 MiB 的 CSV、超过 20 万行的 CSV、超过 20 万目录项目的扫描，以及超过 2 亿像素的单张图片；可在 `config/settings.py` 调整。
- 本工具不是色彩管理审片器，目前不支持 EXR、OCIO/ACES 或视频容器。

发布流程和 GUI 验收项见 [发布检查清单](docs/RELEASE_CHECKLIST.md) 与 [GUI 验收记录](docs/GUI_ACCEPTANCE.md)。

## 许可证

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)：

- 允许为非商业目的使用、复制、修改和分发本软件。
- 分发原版或修改版时，必须同时保留许可证及版权声明。
- 不允许任何预期商业应用；商业使用必须事先取得版权所有者的书面授权。

由于包含非商业限制，本项目属于“源码公开（source-available）”，而不是 OSI 定义下的开源软件。

Copyright 2026 wilsoncc0514.

### License summary (English)

Licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). You may use, copy, modify, and distribute this software for noncommercial purposes. Commercial use requires prior written permission from the copyright holder. The license file and required copyright notice must be preserved when redistributing original or modified copies.

# 图形序列查看器（UE）

一款基于 Python、Tkinter 和 Pillow 的图像帧序列质检工具，支持序列浏览、Tag 标注、CSV 导入导出、异步渲染与帧预加载。

当前版本：**v3.6**

## 功能

- 按目录和文件名前缀组织图像序列。
- 使用键盘、滑块快速浏览连续帧。
- 记录光影问题、构图问题、质检状态和重新渲染要求。
- 导入、导出带 BOM 的 UTF-8 CSV 文件。
- 异步渲染与邻近帧预加载，降低大序列浏览延迟。
- 兼容 PNG、JPEG、TIFF、BMP 和 WebP。

## 环境要求

- Python 3.10 或更高版本
- Tkinter（通常随 Python 一同安装）
- Pillow 10.0 或更高版本

## 安装与运行

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 图形序列查看器_v3.6/main.py
```

Windows 激活虚拟环境：

```powershell
.venv\Scripts\activate
```

## 测试

```bash
cd 图形序列查看器_v3.6
python3 -m unittest discover -s tests -v
```

## 项目结构

```text
图形序列查看器_v3.6/
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

## 许可证

本项目目前未以开源许可证授权。未经版权所有者明确书面许可，不得复制、修改、分发或用于商业用途，详见 [LICENSE](LICENSE)。


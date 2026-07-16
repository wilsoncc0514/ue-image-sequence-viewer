# 图形序列查看器 v3.6

模块化 Tkinter/Pillow 图像序列质检工具，支持序列浏览、Tag 标注、CSV 导入导出、异步渲染预加载和 macOS 深色界面。

## 运行

```bash
cd 图形序列查看器_v3.6
python3 main.py
```

## v3.6 修复与优化

- 修正“漏光”的标签分类，使其能从 CSV 的“光影问题”列正确导入和导出。
- CSV 导入兼容缺失或空单元格，避免对 `None` 调用字符串方法而中断整次导入。
- CSV 导入无论成功或异常都会恢复原加载状态，避免后续 Tag 回调失效。
- 图片与画布尺寸增加有效性检查，异常输入转为明确错误并由渲染层安全处理。
- 修正版本元数据和测试断言，新增相关边界回归测试。

## v3.4 代码质量收敛

- `core/tag_logic.py` 进一步瘦身，仅保留 Tk 变量回调和 UI 桥接。
- 新增 `core/tag_engine.py`，集中维护 Tag 自动判定、重新渲染触发和旧值兼容规则。
- 新增 `utils/filename_parser.py`，将文件名自动提取规则从 UI Mixin 中移出。
- `core/render_controller.py` 增加渲染结果轮询自适应降频，减少空队列时的 Tk event loop 压力。
- `core/csv_io.py` 增强 Tag 字符串解析，按 Tag 名长度降序匹配，避免短 Tag 名误匹配长 Tag 名。
- `ui/app.py` 将初始化逻辑拆分为 runtime / render / tree / navigation / tag / ui 分组方法。
- `ui/styles.py` 将 ttk 状态映射整理为描述性常量，降低维护成本。
- 新增单元测试覆盖文件名解析、Tag 规则引擎、CSV Tag 解析、预加载索引边界。

## 目录

```text
config/     配置与性能参数
core/       CSV、渲染、seq 状态、Tag 规则
models/     Tag 定义
ui/         界面、组件、弹窗、样式
utils/      日志、错误处理、通用工具
tests/      单元测试
tools/      发布打包脚本
```

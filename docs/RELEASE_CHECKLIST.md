# 发布检查清单

v3.7.1 本地验证记录：2026-10-12。下列远端发布步骤由对应提交的 Actions 和正式 Release 页面记录实际完成状态；创建 Tag 前必须检查发布提交的 CI 结果。

## 版本与内容

- [x] `config/settings.py`、`pyproject.toml`、README、CHANGELOG 与发布包版本一致。
- [x] 已记录兼容范围、已知限制和未验证平台。
- [x] 上一稳定 Tag `v3.7.0` 与本地历史 ZIP 可用；回滚不覆盖已有 CSV。

## 自动检查

- [x] `python -m compileall -q 图形序列查看器`
- [x] `python 图形序列查看器/main.py --smoke-test`
- [x] `RUN_GUI_TESTS=1 python -m unittest tests.test_gui_smoke -v`
- [x] `python -m unittest discover -s 图形序列查看器/tests -v`
- [x] `ruff check .`
- [x] `mypy`
- [x] `pip-audit -r requirements.txt`
- 远端门禁：Linux 3.10/3.12/3.14 单测、静态检查与审计；Linux 3.14/Xvfb 和 Windows 真实 Tk 回归；Windows 启动器退出码故障注入。结果以 Release 中链接的发布提交 CI 为准。

## GUI 与文件流程

- [x] `docs/GUI_ACCEPTANCE.md` 记录本地适用检查及未验证项。
- [x] CSV 导入失败不改变旧状态，导出失败不破坏旧文件。
- [x] 中文/空格路径、损坏图片、输入资源限制、取消及构建失败路径有回归覆盖。

## 发布包

- [x] 发布包不含缓存、日志、虚拟环境、测试、工具、客户素材、凭据和本机路径。
- [x] 在干净临时目录解压并完成启动检查。
- [x] 生成 SHA-256。
- 正式发布步骤：从通过门禁的 main 提交创建 annotated Tag 和非草稿/非预发布 Release，上传 ZIP 与校验文件并核对 digest；完成证据见该版本 GitHub Release。

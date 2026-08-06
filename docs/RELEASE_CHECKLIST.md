# 发布检查清单

## 版本与内容

- [x] `config/settings.py`、`pyproject.toml`、README、CHANGELOG 与发布包版本一致。
- [x] 已记录兼容范围、已知限制和未验证平台。
- [ ] 上一稳定 Tag 与回滚方式可用。

## 自动检查

- [x] `python -m compileall -q 图形序列查看器`
- [x] `python 图形序列查看器/main.py --smoke-test`
- [x] `RUN_GUI_TESTS=1 python -m unittest tests.test_gui_smoke -v`
- [x] `python -m unittest discover -s 图形序列查看器/tests -v`
- [x] `ruff check .`
- [x] `mypy`
- [x] `pip-audit -r requirements.txt`
- [ ] GitHub Actions 全部通过。

## GUI 与文件流程

- [ ] 按 `docs/GUI_ACCEPTANCE.md` 完成适用项目。
- [ ] CSV 导入失败不改变旧状态，导出失败不破坏旧文件。
- [ ] 中文/空格路径、空目录、损坏图片、超大输入和取消路径已验证。

## 发布包

- [x] 发布包不含缓存、日志、虚拟环境、测试、工具、客户素材、凭据和本机路径。
- [x] 在干净临时目录解压并完成启动检查。
- [x] 生成 SHA-256。
- [ ] 创建 Git Tag 和 GitHub Release，上传 ZIP 与校验文件。

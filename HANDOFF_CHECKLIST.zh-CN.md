# 交接检查清单

[English](HANDOFF_CHECKLIST.md) | 简体中文

> V8.4.23 历史交接检查清单。当前 V8.6.5 工作流请使用
> `CODEX_START_HERE.md`。

## 包完整性

- [ ] 解包时保留目录结构。
- [ ] 如有需要，核验 `SHA256SUMS.txt`。
- [ ] 阅读 `CODEX_START_HERE.md` 与 `AGENTS.md`。
- [ ] 编辑前对冻结的 V8.4.23 做标记/副本。

## 基线复现

- [ ] 运行便携构建助手或生成器。
- [ ] 确认未改动的 V8.4.23 的 EXE SHA-256 为
      `50fdb51c28a90f9457d61761c923cd54f668de040e81941d99030fc42f2f2f4f`。
- [ ] 运行 `tools/inspect_pe.py`。
- [ ] 为 GUI 测试记录 Windows 版本/DPI/主题。

## 复现已知 P0 问题

- [ ] Preview 大纲导航跳到文档末尾。
- [ ] 自定义大纲滚动条滑块缺失/不可拖动。

## 稳定化工作

- [ ] 实现 ViewController 单一状态所有权。
- [ ] 修复基于规范 source offset 的大纲导航。
- [ ] 整合 OutlineScrollState 与几何。
- [ ] 添加调试插桩选项。
- [ ] 运行完整回归套件。

## 文档

- [ ] 修复后更新当前审计。
- [ ] 记录新的二进制/源码哈希。
- [ ] 更新版本历史与决策日志。
- [ ] 不要删除失败方法的历史记录；它防止回归考古信息丢失。

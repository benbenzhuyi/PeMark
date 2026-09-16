# 参与贡献

[English](CONTRIBUTING.md) | 简体中文

修改生成器前，请先阅读 `AGENTS.md`、`docs/WIN64_ABI_RULES.md`、
`docs/ARCHITECTURE_V8_5_TARGET.md` 和 `docs/FAILED_APPROACHES.md`。

生产版 EXE 必须由 Python 生成器直接产生。不得在生产链中引入编译器、汇编器、
链接器、托管运行时或解释器打包器。

每项修改需要：

1. 保持文档、视图、布局和滚动条状态各自只有一个所有者；
2. 假定每个 Win64 API 调用都会破坏全部易失寄存器；
3. 增加或更新确定性的机器码回归测试；
4. 运行 `python tools/build_current.py`；
5. 运行 `python tools/test_v8_5_1.py
   src/current/generate_markdown_editor_v8_5_4.py`；
6. GUI 修改必须在 Windows 上运行 `python tools/smoke_test_v8_5_1.py`；
7. 更新变更记录和受影响的架构文档。

Pull Request 应保持范围集中，并说明修改的机器码不变量、触发问题和验证结果。

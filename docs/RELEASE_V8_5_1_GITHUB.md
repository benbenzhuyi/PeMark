# PeMark · 码记 V8.5.1 Preview

PeMark V8.5.1 is the first public V8.5 baseline of this native Windows x64
Markdown editor. Its Python generator emits the PE32+ image and AMD64 machine
code directly, without a compiler, assembler, or linker.

This preview fixes clean shutdown, unifies source/preview state and Markdown
scanning, preserves fenced-code whitespace, makes word-wrap reconstruction
safer, bounds large-document formatting to the viewport, and shares cached
scrollbar geometry across painting and input.

Validation completed:

- 12/12 emitted-machine-code behavior groups;
- 210/210 scrollbar boundary combinations;
- 17/17 Windows GUI smoke checks;
- 5/5 ordinary close runs with exit code 0;
- deterministic consecutive builds.

Asset: `pemark_x64_v8_5_1.exe`

SHA-256: `b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`

See the full [English release notes](RELEASE_V8_5_1_PREVIEW.md).

---

PeMark · 码记 V8.5.1 是这款 Windows x64 原生 Markdown 编辑器首个公开的
V8.5 基线。Python 生成器直接写出 PE32+ 映像与 AMD64 机器码，不使用编译器、
汇编器或链接器。

此预览版修复了关闭崩溃，统一了源码/预览状态和 Markdown 扫描，保留围栏代码块
空白，提高自动换行控件重建安全性，将大文档格式化限制在视口范围内，并让绘制与
输入共享滚动条几何缓存。

已完成验证：

- 12/12 组机器码行为测试；
- 210/210 组滚动条边界组合；
- 17/17 项 Windows GUI 冒烟检查；
- 5/5 次普通关闭均返回退出码 0；
- 连续构建结果完全一致。

附件：`pemark_x64_v8_5_1.exe`

SHA-256：`b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`

完整内容请参阅[中文发布说明](RELEASE_V8_5_1_PREVIEW.zh-CN.md)。

## Preview limitations / 预览版限制

Atomic saving, short-write recovery, unsaved-change protection, legacy encoding
fallback, all capacity boundaries, code signing, ASLR, and separated PE section
permissions are not yet certified. Keep backups of important documents.

原子保存、短写恢复、未保存内容保护、旧编码回退、全部容量边界、代码签名、ASLR
和 PE 权限分节尚未完成认证。请为重要文档保留备份。

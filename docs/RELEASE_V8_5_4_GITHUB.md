# PeMark · 码记 V8.5.4

PeMark V8.5.4 is the **first stable release** of this native Windows x64
Markdown editor. Its Python generator still emits the PE32+ image and AMD64
machine code directly, without a compiler, assembler, or linker.

Stable here means the properties a user depends on are measured rather than
intended: saving is transactional and preserves the previous file on every
tested failure path, unsaved work is protected by revision-derived dirty state,
no fixed buffer silently truncates content any more, repeated open/parse/close
cycles reach a stable memory plateau, and the image enforces W^X with ASLR
enabled across six separately permissioned sections.

Highlights since the V8.5.1 preview:

- transactional save with staging file, complete-write loop and atomic replace;
- shared Save / Discard / Cancel protection for close, New and Open;
- strict UTF-8 / UTF-8 BOM / UTF-16LE BOM with preserved line endings;
- dynamic arenas replace every fixed document-sized buffer (virtual BSS 119.5 MB
  → 8 KB);
- six sections with separated permissions, no writable-and-executable page;
- base relocations and ASLR, verified against the loaded image;
- unwind metadata for all non-leaf routines.

Validation completed:

- 13/13 emitted-machine-code behavior groups;
- 17/17 Windows GUI smoke checks and 5/5 clean exits;
- Open/encoding transaction matrix and eight atomic-save fault modes;
- destructive-transition and revision-ownership matrices;
- allocation-failure injection for every dynamic arena;
- 2600-heading, 140,000-span and 1.2 MB capacity cases;
- memory plateau with zero handle growth;
- deterministic builds reproduced on an independent machine.

Asset: `pemark_x64_v8_5_4.exe`

SHA-256: `aa8de9cda9ed90a2cf66a3a93e021dc91cc192073078a90c53fa9669f478c5cc`

See the full [English release notes](RELEASE_V8_5_4.md).

---

PeMark · 码记 V8.5.4 是这款 Windows x64 原生 Markdown 编辑器的**首个稳定版**。
Python 生成器仍然直接写出 PE32+ 映像与 AMD64 机器码，不使用编译器、汇编器或
链接器。

这里的"稳定"意味着用户依赖的性质已被测量证明：保存是事务性的，所有已测试的
失败路径都保留原文件；未保存内容由 revision 推导的脏状态保护；不再有固定缓冲区
静默截断内容；重复打开/解析/关闭后内存达到稳定平台；映像在六个权限分离的节上
强制 W^X 并启用 ASLR。

相对 V8.5.1 预览版的要点：

- 事务化保存：暂存文件 + 完整写入循环 + 原子替换；
- 关闭、新建、打开共用保存/放弃/取消保护；
- 严格 UTF-8 / UTF-8 BOM / UTF-16LE BOM，并保留换行风格；
- 动态 arena 取代全部固定文档规模缓冲区（虚拟 BSS 119.5 MB → 8 KB）；
- 六节权限分离，不存在同时可写且可执行的页；
- 启用基址重定位与 ASLR，并在已加载映像上验证；
- 为全部非叶例程生成栈回溯元数据。

已完成验证：13/13 组机器码测试；17/17 项 GUI 冒烟与 5/5 次干净退出；打开/编码
事务矩阵与八种原子保存故障模式；破坏性转换与 revision 矩阵；全部动态 arena 的
分配失败注入；2600 标题、140000 跨度与 1.2 MB 容量用例；句柄零增长的内存平台
测量；独立机器复现确定性构建。

附件：`pemark_x64_v8_5_4.exe`

SHA-256：`aa8de9cda9ed90a2cf66a3a93e021dc91cc192073078a90c53fa9669f478c5cc`

完整内容请参阅[中文发布说明](RELEASE_V8_5_4.zh-CN.md)。

## Known limitations / 已知限制

The executable is unsigned, so Windows SmartScreen may warn; verify the SHA-256
before running. The 4 MiB input policy is still a compile-time bound and
oversized files are rejected explicitly. Legacy code pages are not accepted as a
fallback. Full cross-frame stack unwinding is not demonstrated (metadata is
valid and resolvable, but a debugger does not continue past our first frame);
the code raises no exceptions, so behaviour is unaffected. Workspace, advanced
editing and AI features are not part of this release.

EXE 未签名，Windows SmartScreen 可能提示；运行前请核对 SHA-256。4 MiB 输入政策
仍是编译期上界，超限文件被显式拒绝。旧代码页不作为回退。完整跨帧栈回溯尚未
证明（元数据合法且可解析，但调试器未从我们的第一帧继续向上）；代码不使用异常，
行为不受影响。工作区、高级编辑与 AI 功能不在本版本内。

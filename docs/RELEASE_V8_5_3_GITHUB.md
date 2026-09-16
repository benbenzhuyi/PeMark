# PeMark · 码记 V8.5.3 Preview

PeMark V8.5.3 is the dynamic-capacity release of this native Windows x64
Markdown editor. Its Python generator still emits the PE32+ image and AMD64
machine code directly, without a compiler, assembler, or linker.

This release removes the last document-sized fixed buffers. The document text,
position map and render text, style spans, Outline tables, decode scratch and
file-byte buffer are now arenas sized by the actual document, while every V8.5.2
document-safety guarantee and the 4 MiB input policy stay unchanged.

Virtual BSS drops from 119,508,992 bytes to 8,192 bytes and the PE virtual size
from 121,159,680 to 86,016 bytes, so the writable region that blocked section
separation is gone.

Validation completed:

- 13/13 emitted-machine-code behavior groups;
- 17/17 Windows GUI smoke checks;
- 5/5 ordinary close runs with exit code 0;
- Open/encoding transaction matrix and eight atomic-save fault modes;
- allocation-failure injection for every dynamic arena;
- 2600-heading, 140,000-span and 1.2 MB capacity cases;
- memory plateau over 12 Open + Preview + New cycles with zero handle growth;
- deterministic consecutive builds.

Asset: `pemark_x64_v8_5_3.exe`

SHA-256: `6ad87c6dcb3b9d3a35041d1bc37e5792f3cfd16cb79046088a3426200d0bb7d0`

See the full [English release notes](RELEASE_V8_5_3_PREVIEW.md).

---

PeMark · 码记 V8.5.3 是这款 Windows x64 原生 Markdown 编辑器的动态容量版本。
Python 生成器仍然直接写出 PE32+ 映像与 AMD64 机器码，不使用编译器、汇编器或
链接器。

此版本移除了最后一批按文档规模固定的缓冲区：document 文本、位置映射与渲染
文本、样式跨度、大纲表、解码 scratch 与文件字节缓冲区，现在都按实际文档规模
分配；V8.5.2 的全部文档安全保证与 4 MiB 输入政策保持不变。

虚拟 BSS 从 119,508,992 字节降到 8,192 字节，PE 虚拟尺寸从 121,159,680 降到
86,016 字节，阻碍 PE 分节的巨大可写区域已经消失。

已完成验证：

- 13/13 组机器码行为测试；
- 17/17 项 Windows GUI 冒烟检查；
- 5/5 次普通关闭返回退出码 0；
- 打开/编码事务矩阵与八种原子保存故障模式；
- 每个动态 arena 的分配失败注入；
- 2600 标题、140000 跨度与 1.2 MB 文档容量用例；
- 12 轮"打开 + 预览 + 新建"内存平台测量，句柄零增长；
- 连续构建结果完全一致。

附件：`pemark_x64_v8_5_3.exe`

SHA-256：`6ad87c6dcb3b9d3a35041d1bc37e5792f3cfd16cb79046088a3426200d0bb7d0`

完整内容请参阅[中文发布说明](RELEASE_V8_5_3_PREVIEW.zh-CN.md)。

## Preview limitations / 预览版限制

The 4 MiB input policy is still a compile-time bound although its buffers are now
dynamic. Legacy code pages are not accepted as a fallback. The image is still a
single read/write/execute section, unsigned, without ASLR or unwind metadata.
Workspace, advanced editing and AI features are not part of this release. Keep
backups of important documents.

4 MiB 输入政策仍是编译期上界，尽管其缓冲区已动态化。旧代码页仍不作为回退。
映像仍是单一可读可写可执行节，未签名，也没有 ASLR 与 unwind 元数据。工作区、
高级编辑与 AI 功能不在本版本内。请为重要文档保留备份。

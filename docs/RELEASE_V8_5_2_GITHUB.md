# PeMark · 码记 V8.5.2 Preview

PeMark V8.5.2 is the document-safety release of this native Windows x64
Markdown editor. Its Python generator still emits the PE32+ image and AMD64
machine code directly, without a compiler, assembler, or linker.

This preview makes editing safe to lose work from: unsaved changes are derived
from document revisions, New/Open/Exit/close share one Save / Discard / Cancel
controller, saving is atomic through a sibling staging file, and opening is
transactional with strict UTF-8, UTF-8 BOM and UTF-16LE BOM handling. The 2048
Outline and 131072 style caps are retired in favour of dynamic arenas.

Validation completed:

- 13/13 emitted-machine-code behavior groups, including 210/210 scrollbar
  boundary combinations;
- 17/17 Windows GUI smoke checks;
- 5/5 ordinary close runs with exit code 0;
- Open/encoding transaction matrix and atomic-save fault injection;
- successful and failed arena allocation coverage;
- deterministic consecutive builds.

Asset: `pemark_x64_v8_5_2.exe`

SHA-256: `2c105660dbac96b7de18614f43753073b3b5613e22bba160ceb8058646040e30`

See the full [English release notes](RELEASE_V8_5_2_PREVIEW.md).

---

PeMark · 码记 V8.5.2 是这款 Windows x64 原生 Markdown 编辑器的文档安全版本。
Python 生成器仍然直接写出 PE32+ 映像与 AMD64 机器码，不使用编译器、汇编器或
链接器。

此版本让编辑不再有丢失工作的风险：未保存状态由文档 revision 推导，新建、打开、
退出与关闭窗口共用一个保存/放弃/取消控制器，保存通过同级暂存文件原子替换，
打开采用事务式提交并严格处理 UTF-8、UTF-8 BOM 与 UTF-16LE BOM。2048 项大纲
上限与 131072 项样式上限已由动态 arena 取代。

已完成验证：

- 13/13 组机器码行为测试，含 210/210 组滚动条边界组合；
- 17/17 项 Windows GUI 冒烟检查；
- 5/5 次普通关闭均返回退出码 0；
- 打开/编码事务矩阵与原子保存故障注入；
- arena 分配成功与失败两类覆盖；
- 连续构建结果完全一致。

附件：`pemark_x64_v8_5_2.exe`

SHA-256：`2c105660dbac96b7de18614f43753073b3b5613e22bba160ceb8058646040e30`

完整内容请参阅[中文发布说明](RELEASE_V8_5_2_PREVIEW.zh-CN.md)。

## Preview limitations / 预览版限制

Document, render, position-map and encoded-output buffers still have fixed
sizes; oversized input is rejected explicitly. Legacy code pages no longer serve
as a fallback. Code signing, ASLR and separated PE section permissions are not
implemented yet, and long-running memory-plateau measurements are outstanding.
Keep backups of important documents.

document、render、position-map 与编码输出缓冲区仍为固定大小，超大输入会被显式
拒绝。旧代码页不再作为回退。代码签名、ASLR 和 PE 权限分节尚未实现，长时间
运行的内存平台测量尚未完成。请为重要文档保留备份。

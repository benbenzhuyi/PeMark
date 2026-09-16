# PeMark 清晰里程碑计划

文档状态：现行规范  
起点：V8.5.1 Preview

## 1. 规划原则

里程碑按依赖与风险排序，不按功能吸引力排序。只有验收证据齐全才算推进；日期、
代码量和完成百分比不能替代 release gate。

每一步只实现解决当前已证实问题所必需的最小机制。“可以再加一个检查”不是
实施的充分理由；局部合理的机制累积起来也可能不经济。

本文的版本顺序是当前假设，不是必须执行的命令。当实现证据表明某个后续阶段
应该提前，或某项设计不可行时，先修改本文再改代码。

前三阶段先建立安全的原生核心，随后才进入 Workspace、高级编辑和 AI。

## 2. 当前基线：V8.5.1 Preview

已经建立：

- 可重复的纯 Direct-PE 构建；
- 主窗口确定性正常退出；
- Preview、styles、PositionMap、Outline 统一 Markdown 扫描；
- 集中的 Source/Preview 转换；
- 围栏代码空白保真；
- 视口限定的 Preview 格式化；
- 大纲滚动条共享几何；
- Windows GUI 回归自动化。

公开限制：保存非原子、短写处理不完整、没有未保存保护、存在固定容量、虚拟 BSS
很大、PE 仍是单一 RWX section。

## 3. V8.5.2：Document Safety（当前发布目标）

### 范围

只包含已被证据证实的数据安全问题：未保存保护、事务化保存、编码保真。
动态容量与 PE 加固不属于本版本，它们分别是 V8.5.3 与 V8.5.4。

理由：把五组工作绑进一个里程碑，会让一个功能上已经可用的安全版本长期
无法发布。文件安全与动态容量之间只有弱依赖，可以分批交付。

### Phase A：规格与观测基础

- 建立 New/Open/Save/Save As/Close 的行为契约；
- 定义 document revision 与 saved revision；
- 设计 file I/O 和 allocation failure injection；
- 采集标准文档的耗时、内存、进程与 handle 基线；
- 将构建测试入口改为版本无关名称；
- 映射当前 load/save routines、buffers、capacities 和 ownership writes。

Exit gate：

- 所有文件操作都有 success/failure/cancel 契约；
- fixture 与基线 hash 已冻结；
- diagnostics 能标识 operation、revision 和 Win32 error；
- 除诊断外不改变正式行为。

### Phase B：Dirty state 与破坏性转换

- Source 编辑递增 document revision；
- dirty 由 revision equality 推导；
- New/Open/Close 统一进入 unsaved-change controller；
- 程序内部更新不会形成 false dirty；
- 保存失败后不得继续隐式破坏性操作。

Exit gate：

- Save/Discard/Cancel 全矩阵通过；
- 100 次 edit/mode/close 循环无状态分歧；
- focus、menu、title 和 dirty state 一致；
- V8.5.1 原有行为全部回归通过。

### Phase C：Transactional output

- 编码不可变 revision snapshot；
- 循环处理部分写入；
- 写 sibling temporary file 并原子替换；
- 定义 recovery 文件命名、发现与清理；
- 捕获并显示可行动的错误信息。

Exit gate：

- 支持编码与换行的 byte-for-byte round trip 通过；
- 每个 write/replace 边界注入失败后原文件保持完好；
- replacement 完成前不报告成功；
- 不遗留无归属 handle 或无政策的临时文件。

### Phase D：Encoding policy

- UTF-8、UTF-8 BOM、UTF-16LE BOM；
- 明确旧代码页 fallback；
- 编码和 EOL metadata 与内部规范化分离；
- undecodable/oversized 输入采用事务式失败。

Exit gate：

- 中文、英文、日韩、emoji、LF、CRLF、CR fixtures 通过；
- malformed input 行为明确；
- 无静默替换、截断或半更新 DocumentModel。

### V8.5.2 Release gate

- 无已知可复现数据丢失或退出崩溃；
- Commit/Milestone 两级 gate 在目标 Windows 环境通过：确定性构建、机器码
  回归、Open/编码事务、破坏性转换矩阵、Windows GUI 冒烟与退出码；
- 两次构建二进制一致；
- manifest 记录已知限制；
- 独立复核接受 file transaction。

性能分布、内存平台与 handle 长跑属于 Release/Research gate，不作为本版本的
阻塞条件。

## 4. V8.5.3：Dynamic Capacity

原 V8.5.2 的 Phase E。它在 V8.5.2 发布之后独立进行，避免继续阻塞安全版本。

### 目标

移除随文档规模静默截断的固定容量，并让分配失败不破坏当前文档。降低初始
commit 与 working set 是期望结果，不是硬性验收条件。

### 已完成的切片

- Outline 三表（srcpos/renderpos/level）迁入动态 arena；
- 样式三列（start/end/type）迁入动态 arena，131072 项上限已退役；
- 两个 arena 都在 Open 提交边界之前预留，增长失败保持旧文档与旧 arena 完整；
- 分配失败注入覆盖两个 arena；140000 跨度用例证明不再截断。
- 渲染侧缓冲区迁入一个连续 arena：位置映射（4 字节/单元）与渲染文本
  （2 字节/单元），容量为 `max(4096, 归一化长度 + 1)`；扫描越界保护改为读取
  已发布容量，虚拟 BSS 由 119.5 MB 降至 68.5 MB。
- document 文本改为"保留政策上限 + 512 KiB 单元块提交"的 arena：可见上限与
   规范化上限仍是 `WIDE_CHARS`，物理提交随内容增长；编辑器同步在读取前预留，
   失败时用不变的模型回滚控件显示。虚拟 BSS 进一步降至 51.5 MB。
- 最后两个固定缓冲区（解码/序列化 scratch 与文件字节）改为按操作规模提交的
   arena；编码 API 的上限改为读取已发布容量。虚拟 BSS 降至 8 KB，PE 虚拟
   尺寸由 51.6 MB 降至 86 KB。
- 完成 12 轮 Open(仅解析)+Preview(解析)+New 的重复循环测量：句柄零增长，
  私有内存首末四分之一区间增长约 1.6 MB，达到稳定平台。

### 剩余范围

- 按风险逐个迁移 document、encoded output、render、map 缓冲区；
- 迁移时保留最小必要不变式：单一事实源、提交点、失败不破坏旧模型；
- 完成重复 open/parse/close 的内存平台观察；
- 声明并测试最大输入与安全拒绝行为。

### Exit gate

- 保留的固定数组不再承担独立事实源；
- 每个已迁移 arena 的分配失败不会改变当前文档状态；
- 大规模输入不再静默截断；
- 重复 open/parse/close 后内存与 handle 有界。

以上四项均已由 `tools/test_v8_5_3_*.py` 覆盖。V8.5.3 的剩余工作只有发布
验证与文档冻结。

## 5. V8.5.4：Direct-PE Hardening

### 目标

把 loader-simple RWX 映像改造成分节、可重定位、可审计的 PE，同时保留直接生成。

### Deliverables

- 声明式 PE region/section allocator；
- `.text/.rdata/.idata/.data/.bss` 权限分离；
- base relocation 与 ASLR；
- 适用函数的 `.pdata`/unwind metadata；
- deterministic symbol/function-range map；
- directory、alignment、fixup、overlap 构建验证；
- CFG/CET 可行性结论及可行部分实现。

### 已完成的切片

- 单一可读可写可执行节已拆分为按权限分离的四个节：`.text`（RX 代码）、
  `.rdata`（R 字符串与只读表）、`.idata`（RW 导入表与 IAT）、`.bss`（RW 零
  初始化状态）；不存在同时可写且可执行的节。
- 每个节的 VirtualSize/SizeOfRawData 覆盖到下一节的 RVA 间距，raw 缓冲与 RVA
  计划保持一一对应。紧凑布局会被 Windows 以 `ERROR_BAD_EXE_FORMAT` 拒绝，
  该失败变体记录在 `FAILED_APPROACHES.md`。
- 新增 `tools/test_v8_5_4_sections.py`：既检查磁盘上的节表，也用
  `VirtualQueryEx` 验证已加载映像的页保护为 RX / R / RW / RW，并做一次真实
  窗口启动与干净退出。
- 新增 `.reloc` 节：每个映像页一个块，条目全部为 `IMAGE_REL_BASED_ABSOLUTE`
  （本映像没有绝对地址，语义就是"无需修正"）；`DllCharacteristics` 增设
  `DYNAMIC_BASE`，实测加载基址为 `0x7FF73D810000` 一类随机值而非首选基址，
  窗口启动、符号访问与干净退出均正常。测试同时校验重定位目录、块结构与
  实际基址已随机化。
- 生成 `.pdata` 栈回溯元数据：为全部非叶例程（42 条）生成 RUNTIME_FUNCTION，
  prologue 从生成的机器码反解；UNWIND_INFO 按链接器惯例放在 `.rdata`，异常
  目录大小只覆盖数组。dbghelp 能为我们的地址解析出条目，真实栈回溯能进入
  本模块，程序在 ASLR 下启动、工作、退出均正常。
  **已知限制**：回溯到达本模块帧后未能继续向上，完整回溯尚未证明；程序行为
  不受影响（代码不使用异常），该状态由 `test_v8_5_4_unwind.py` 显式打印而非
  断言通过。

### 剩余切片

- CFG/CET 可行性结论已完成，见 `V8_5_4_CFG_CET_FEASIBILITY.md`：两者本里程碑都不实现
  （CFG 缺少可被控制的间接调用目标，CET 声明不改变行为且带来加载风险），并记录
  了重新评估条件。
- （可选）继续排查完整栈回溯，需要时再投入；当前记录为发布门禁偏差。

### Release gate 偏差说明

原定"representative nested frames 的 unwind 测试通过"这一条**未完全达成**：
`.pdata` 结构合法、系统可解析条目、回溯能到达本模块，但 dbghelp 未从我们的帧
继续向上（尝试过规范修正与两个真实 bug 修复后仍未跨帧）。由于本程序不抛出异常，
该偏差不影响行为正确性；它被显式记录，而不是通过放宽断言掩盖：
`tools/test_v8_5_4_unwind.py` 会打印这一状态。

### Release gate

- writable application data 不可执行；
- 非首选基址加载矩阵通过；
- representative nested frames 的 unwind 测试通过；
- `inspect_pe`、反汇编与 Windows loader 观察一致；
- V8.5.2 数据完整性和 GUI 套件不变通过；
- 分节对启动、内存的影响已测量且无未解释回归。

## 6. V8.6：Workspace Foundation

### 目标

在仍然只有一个 active writable document 的前提下加入安全的多文件导航。

### Deliverables

- WorkspaceModel 与 directory tree；
- lazy TreeView population；
- recent workspace/file；
- drag-and-drop open；
- 安全的 create/rename/delete；
- sidebar 与 window state 持久化；
- 外部文件变化检测与冲突提示。

### Release gate

- small 与 10,000-entry tree 契约通过；
- Unicode、长路径、拒绝访问、reparse point 和 race 有明确行为；
- 文件破坏性命令不能绕过 unsaved protection；
- idle CPU 与 handle 有界；
- 递归扫描不会无限阻塞 UI。

## 7. V8.7：Advanced Editing and Markdown Fidelity

### 目标

在保持原生效率可测量的前提下接近参照产品的核心编辑体验。

候选范围：

- line-number gutter 与 current line；
- search decorations；
- 基于 Source offset 的 fold model；
- 更完整的 block/inline Markdown contracts；
- incremental semantic invalidation；
- 生成式编辑的 Undo transaction；
- IME、selection、accessibility、high-DPI 改进。

RichEdit 并不预设需要替换。只有独立 ADR 和原型测量证明其不能满足行为契约时，
才启动 custom editor architecture。

### Release gate

- 约定的 Editor Core/Markdown parity score 达标；
- typing、scroll、mode transition 满足 p95 budget；
- 24 小时 stress editing 无无限内存或 handle 增长；
- IME 与 multilingual matrix 通过；
- malformed Markdown 不会崩溃或产生非法 PositionMap。

## 8. V8.8：Cross-Architecture Experiment Baseline

### 目标

先发布可复现比较方法，再提出架构优劣结论。

### Deliverables

- 冻结 Rabbit Electron reference commit；
- 与实现无关的 versioned feature contracts；
- shared small/medium/large/stress/headings/unicode workloads；
- deterministic UI action scripts；
- environment 与 release manifest schema；
- startup、memory、latency、stability、engineering-cost 方法；
- 可选的窄范围 C++/Rust native control。

### Release gate

- 各实现使用相同 contract/workload versions；
- 短操作结论至少 30 个样本；
- 结果包含 p50/p95/p99 与 validity limits；
- shipped footprint 与 runtime use 分开报告；
- 缺失功能和失败保留在 parity score 中。

规格工作可与 V8.5.2 并行，但在测量方法冻结前不得作正式比较结论。

## 9. V9：AI Native

### Phase A：Transport laboratory

- async WinHTTP lifecycle；
- cancellation、timeout、proxy；
- bounded UTF-8 与 JSON/SSE parser；
- 可确定分块的本地 mock server；
- token queue 与 backpressure 测量。

### Phase B：Bounded document actions

- immutable selection/request snapshot；
- Ctrl+K preview-before-apply；
- 与 Undo 集成的 insert/replace transaction；
- cancel 不产生 partial document mutation。

### Phase C：AI workspace

- 右侧 conversation panel 与 Ctrl+L；
- provider/model/settings abstraction；
- per-document conversation persistence；
- local/online OpenAI-compatible endpoints；
- secret storage 与 redaction policy。

### Release gate

- hostile fragmentation、malformed payload、response limit 测试通过；
- 慢流和 stalled stream 下 UI 保持响应；
- network completion 不能绕过 document transaction；
- credentials 不进入 repo、logs、crash evidence 或文档；
- mock benchmark 将客户端开销与模型延迟分离；
- V8.5 文件安全套件持续通过。

## 10. 明确延后

以下想法需要独立提案，不由本路线图自动授权：

- 多个同时可写文档或 tabs；
- PeMark 进程内 plugin execution；
- arbitrary HTML rendering；
- 自动更新 executable code；
- CPU-specific instruction variants；
- custom editor replacement；
- GPU rendering；
- 全量 Rabbit 功能身份复制。

## 11. Milestone Snapshot 分级

不同层级的记录要求不同。不要对每个日常提交套用发布级清单。

Commit 级（每个有界变更）：

```text
source commit
generator/EXE SHA-256
相关测试的 pass/fail
新增或更新的 known issue
binary size
```

Milestone 级（候选版与发布版）追加：

```text
version/channel
tested Windows environments
feature contract version/parity score
full regression pass/fail counts
已知限制与未解决发现
review identity
```

Release/Research 级（正式发布、性能专项、V8.8 对照实验）追加：

```text
workload hashes
startup/open/preview p50/p95/p99
idle/peak memory and commit
process/handle counts
Agent sessions/human interventions
```

跨越同一 milestone 的连续小提交可以共享一次 Milestone 级快照，不要求逐条
维护发布级指标。

## 12. 立即执行顺序

当前只做两件事，按顺序：

1. 收尾 V8.5.2 Document Safety 的发布门禁：确认 Commit/Milestone 两级证据齐全，
   记录已知限制，发布 V8.5.2。
2. 发布之后再决定 V8.5.3 Dynamic Capacity 的下一批 arena 切片，一次一个。

期间不新增长期架构文档、不预先实现后续版本需要的机制。新需求先回答
“这一步最低必要工程量是什么”，再决定是否进入计划。

历史准备步骤（契约、fixture、failure injection、baseline、ownership map）
已在 V8.5.2 前期完成，不再重复执行。

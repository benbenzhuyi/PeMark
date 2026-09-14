# PeMark 清晰里程碑计划

文档状态：现行规范  
起点：V8.5.1 Preview

## 1. 规划原则

里程碑按依赖与风险排序，不按功能吸引力排序。只有验收证据齐全才算推进；日期、
代码量和完成百分比不能替代 release gate。

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

## 3. V8.5.2：Document Safety and Dynamic Capacity

### 总目标

首先让用户数据转换可预测、可恢复，再移除固定容量架构，同时保持当前可见编辑模型。

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

### Phase E：Dynamic arenas

- 封装 VirtualAlloc/VirtualFree；
- 迁移 document、encoded output、render、map、styles、outline；
- scratch-build + commit-swap；
- 移除 active 2048 Outline 和 131072 style caps；
- 降低初始 commit 与 working set。

Exit gate：

- 2600 headings 全部显示且导航正确；
- growth boundaries 与 allocation failures 全部通过；
- 重复 open/parse/close 后内存达到稳定平台；
- 无旧固定 buffer 继续承担独立事实源；
- 最大输入政策已测试且能安全拒绝。

### V8.5.2 Release gate

- 无已知可复现数据丢失、退出崩溃或容量 P0；
- Tier 0–5 在目标 Windows 环境通过；
- 两次构建二进制一致；
- manifest 记录安全和容量边界；
- 独立复核接受 file transaction 与 allocation cleanup。

## 4. V8.5.3：Direct-PE Hardening

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

### Release gate

- writable application data 不可执行；
- 非首选基址加载矩阵通过；
- representative nested frames 的 unwind 测试通过；
- `inspect_pe`、反汇编与 Windows loader 观察一致；
- V8.5.2 数据完整性和 GUI 套件不变通过；
- 分节对启动、内存的影响已测量且无未解释回归。

## 5. V8.6：Workspace Foundation

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

## 6. V8.7：Advanced Editing and Markdown Fidelity

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

## 7. V8.8：Cross-Architecture Experiment Baseline

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

## 8. V9：AI Native

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

## 9. 明确延后

以下想法需要独立提案，不由本路线图自动授权：

- 多个同时可写文档或 tabs；
- PeMark 进程内 plugin execution；
- arbitrary HTML rendering；
- 自动更新 executable code；
- CPU-specific instruction variants；
- custom editor replacement；
- GPU rendering；
- 全量 Rabbit 功能身份复制。

## 10. 每个 Milestone Snapshot

候选版和发布版都记录：

```text
version/channel
source commit
generator/EXE SHA-256
tested Windows environments
feature contract version/parity score
workload hashes
test pass/fail counts
known issues
binary/shipped size
startup/open/preview p50/p95/p99
idle/peak memory and commit
process/handle counts
Agent sessions/human interventions
review identity/unresolved findings
```

## 11. 立即执行顺序

在修改 V8.5.1 generator 之前：

1. 起草 V8.5.2 file-operation contracts；
2. 冻结 safety/encoding/capacity fixtures；
3. 定义 file I/O 与 VirtualAlloc failure injection；
4. 采集 V8.5.1 timing/memory/process/handle baseline；
5. 完成现有 load/save/buffer/ownership map；
6. 起草 atomic replacement、encoding preservation、arena growth ADR；
7. 复核首个实现项：document revision 与 dirty-state ownership。

只有第 7 项进入 generator 行为修改。


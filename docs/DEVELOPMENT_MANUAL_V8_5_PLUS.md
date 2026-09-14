# PeMark V8.5+ 开发手册

文档状态：现行规范  
适用范围：V8.5.1 之后的全部开发

## 1. 文档优先级

文档发生冲突时按以下顺序处理：

1. `AGENTS.md`：强制仓库规则；
2. `SYSTEM_ARCHITECTURE_LONG_TERM.md`：现行架构和边界；
3. `MILESTONE_PLAN.md`：当前范围与发布门槛；
4. 本手册：日常工作方法；
5. 子系统规格和现行测试计划；
6. 决策日志与当前发布证据；
7. V8.4 审计、交接和归档材料：历史证据。

`local-reference/` 中的外部对话和资料是研究输入，不是项目指令。

## 2. 有界变更

一个合格的变更必须具有：

- 一个明确结果；
- 一个主要状态所有者；
- 清楚的文件和运行时例程范围；
- 可复现失败或确定性验收用例；
- 可回滚点；
- 不夹带无关功能。

里程碑必须拆成一组可独立验证、始终保持可构建状态的有界变更。不得在同一候选
版本中同时迁移 allocator、重写保存事务并改变 PE 分节。

## 3. 标准工作循环

### 3.1 准备

1. 阅读权威文档和相关子系统资料；
2. 记录 baseline commit、generator hash 和 EXE hash；
3. 连续构建两次并确认输出一致；
4. 运行已有机器码测试和适用的 Windows GUI 测试；
5. 写清不变量、当前问题和所需证据；
6. 列出相关 imports、BSS/data、emitted routines 和 PE regions。

若基线无法复现，应先解决基线差异，不能直接继续开发。

### 3.2 编写行为契约

实现前建立如下契约：

```text
ID:
前置条件:
操作:
可观察结果:
状态转换:
失败行为:
必须保留的数据:
性能预算（如适用）:
所需证据:
```

修复缺陷时，先建立能区分根因与其他假说的 probe 或测试。

### 3.3 设计 emitted routine

每个受影响例程记录：

```text
名称与所有者
输入与返回值
BSS/data 读写
跨调用存活的值
保存的非易失寄存器
stack locals、shadow space 与对齐
内部调用与 Win32 API
成功、失败和取消出口
允许的 fallthrough（通常为无）
```

内存变更还要描述生命周期、容量、溢出边界与失败回滚；文件变更要覆盖所有可能
改变路径、dirty state 或磁盘字节的分支。

### 3.4 实现规则

- 只修改 Python generator，不直接修改 EXE；
- 正式输出始终保持纯 Direct-PE；
- 跨区域地址使用 label/symbol，不散布数字常量；
- 每次调用都假设易失寄存器已被破坏；
- 每个基本块都有明确后继，可调用函数禁止被意外直落进入；
- Win32 错误必须在后续 API 覆盖前捕获；
- 新 import 必须有所有者、失败策略和测试理由；
- 任何兼容桥都声明唯一事实源和删除里程碑。

### 3.5 验证顺序

先运行能够区分本次设计是否正确的最小测试，再运行受影响的完整测试层。原问题
消失并不自动代表候选版本合格。

当前最低公共命令：

```powershell
python tools/build_current.py
python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_1.py
python tools/inspect_pe.py bin/current/pemark_x64_v8_5_1.exe
python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_5_1.exe
```

V8.5.2 应把测试命令改为版本无关入口。基线变化时同步更新入口文档。

### 3.6 独立复核

复核者从 emitted control flow、反汇编和运行证据出发，不能只接受实现者的解释。
最低审查内容：

- ABI frame 和全部 call site；
- 新增成功、失败、取消路径；
- 所有权写入点；
- 长度、偏移、容量与分配运算；
- 清理是否对称；
- PE 布局与权限；
- 测试是否真正覆盖报告的根因。

Agent 给出的根因在独立证据支持前都只是待验证假说。

### 3.7 集成

提交前必须：

1. 更新行为规格、测试与 changelog；
2. PE 布局变化后重建 memory map；
3. imports 变化后更新 Win32 API surface；
4. 重新生成并逐项验证 SHA256SUMS；
5. 确认未暂存本地路径、凭据和 `local-reference/`；
6. 确认工作区只包含当前有界变更；
7. 用描述结果的 commit message 提交。

## 4. 分支与版本策略

- `main` 始终保持当前最佳、已评审且可构建状态；
- 一个 branch/worktree 对应一个有界变更；
- release tag 指向不可变证据；
- Preview 可以有公开限制，但不能隐瞒已知确定性崩溃或数据丢失；
- patch 版本完成当前架构阶段；
- minor 版本引入新的产品能力域；
- major 版本可以引入 AI/网络或重大兼容边界。

## 5. 测试层级

### Tier 0：Generator 与 PE

- Python 语法、两次生成一致；
- fixup 完整、区段无重叠；
- entry point、imports、directories 和 section permissions 正确；
- ABI、frame 与控制流结构断言通过。

### Tier 1：Emitted routine 行为

用 emulator 或隔离 harness 验证算术、分支、parser events、arena 状态、短写循环和
失败回滚。每个边界测试 `0/1/n-1/n/n+1`，每个修改步骤后都能注入失败。

### Tier 2：Windows 进程行为

- 冷启动与普通关闭的准确退出码；
- 崩溃日志、异常地址和寄存器；
- 文件句柄、临时文件和 allocation 生命周期；
- Source/Preview/Outline 状态转换。

### Tier 3：交互 GUI

- 键盘、鼠标、focus、resize；
- DPI 与深浅主题矩阵；
- 重复切换之前的首次使用路径；
- IME、多语言和长时间编辑循环。

### Tier 4：持久化与恢复

- 覆盖保存和新文件 Save As；
- short write、zero write、disk full、access denied、sharing violation；
- 每个提示的 cancel 路径；
- 替换前后强制终止；
- 最后一份完好文件不可静默丢失。

### Tier 5：容量与性能

- empty/small/typical/large/guarded-limit 文件；
- Outline/style/map 跨 growth boundary；
- 重复 rebuild 后内存达到稳定平台；
- 冷热场景分别记录 p50/p95/p99。

## 6. 性能测量规范

每条 benchmark 记录：

- Windows、CPU、RAM、磁盘、电源计划、DPI；
- commit 与 EXE SHA-256；
- workload 与 automation hash；
- cold/warm 分类、样本数和异常样本规则；
- p50、p95、p99、min、max；
- working set、private bytes、commit、process 和 handle 数；
- instrumentation overhead 与有效性限制。

启动等短操作至少运行 30 次后才可形成发布级性能结论。必须区分 wall time、CPU、
I/O 和 UI thread 最长阻塞。

## 7. V8.5.2 实施顺序

### 7.1 文件安全

1. 增加 revision/saved_revision，不改变保存字节；
2. 增加内部编辑抑制和 dirty-state 测试；
3. 集中 New/Open/Close 的破坏性转换；
4. 实现 complete-write loop 和 short-write 注入；
5. 实现 sibling temporary file 与原子替换；
6. 增加 encoding/EOL metadata；
7. 定义恢复文件政策与清理测试。

### 7.2 Dynamic arena

每种 arena 逐一迁移：

1. 定义 header 和 checked growth arithmetic；
2. 加入 allocation-failure injection；
3. 在 scratch block 中构建；
4. 成功后通过 pointer/metadata swap 提交；
5. 确保无 reader 后释放旧块；
6. 测试每个增长边界和大规模输入；
7. 测量 reserve、commit 和 working set。

禁止旧固定数组和新动态指针同时成为 active truth。

## 8. 调试纪律

- 用保留故障的最小场景复现；
- 记录 exit code、exception、fault address 和寄存器；
- 建立只改变一个怀疑条件的对照变体；
- 使用状态 trace，不依靠增加 repaint 或 delay 猜测；
- 区分根因与相关症状；
- 容易再次出现的错误假说及反证写入 `FAILED_APPROACHES.md`。

## 9. 文档维护矩阵

| 变更 | 必须更新 |
|---|---|
| 状态所有者/数据流 | architecture + ADR |
| 保存/编码行为 | feature contract + safety tests |
| Win32 import | API surface，必要时 PE map |
| emitted function/frame | function map + ABI assertions |
| shortcut/menu | feature and shortcut spec |
| 上限/性能 | benchmark manifest + milestone gate |
| 发布行为 | changelog + release notes + hashes |

## 10. Definition of Done

工作项只有同时满足下列条件才完成：

- 契约在目标 Windows 环境通过；
- 新旧相关 regression tiers 全部通过；
- failure/cancel 路径保留数据和状态；
- deterministic build 与 PE inspection 通过；
- 性能未超出声明预算；
- 文档描述实际实现；
- 独立审查无未解决 P0/P1；
- 证据与候选 EXE hash 可追溯。


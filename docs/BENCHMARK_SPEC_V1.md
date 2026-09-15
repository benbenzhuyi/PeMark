# 跨架构基准测试规范 V1

状态：实验规范草案  
目的：公平比较 Electron、Direct-PE 与 native control

启用时机：V8.8 对照实验、正式发布验证或专项性能调查。日常提交只记录 EXE
大小与测试结果，不采集分布数据；把本规范压到每个提交上会挤掉功能开发预算。

## 1. 分别回答的问题

1. 相同行为下的启动、交互和文档处理性能；
2. shipped footprint 与实际 runtime resource use；
3. 获得结果所需的工程投入、缺陷修复和人工干预。

不能用单一指标概括整体优劣。

## 2. 固定环境

每轮记录 `machine_id`、CPU、RAM、磁盘、Windows build、电源计划、DPI、分辨率、
主题、安全软件状态、后台负载政策、implementation commit/tag/hash，以及 fixture
和 automation hashes。同一批次在同一机器、同一电源状态和窗口尺寸下执行。

## 3. Workload corpus

| Fixture | 规模 | 目的 |
|---|---:|---|
| `small.md` | 10 KiB | 常见编辑与 Markdown |
| `medium.md` | 500 KiB | 多章节、代码、Unicode |
| `large.md` | 1.2 MiB | 导航与 Preview |
| `stress.md` | 4 MiB/共同上限 | 容量与拒绝策略 |
| `headings.md` | 2600+ headings | Outline 与 mapping |
| `markdown-full.md` | 固定 corpus | 语法矩阵 |
| `unicode.md` | 固定 corpus | 中英日韩、emoji、EOL |
| `workspace/` | 10,000 entries | V8.6 文件树 |

正式比较前冻结全部 SHA-256。

## 4. 固定动作

```text
cold launch -> open large.md
-> navigate first/middle/last heading
-> first Source/Preview round trip
-> search fixed term
-> theme x20 -> mode x20
-> scroll end/back -> word wrap toggle
-> append fixed text -> save -> normal close
```

UI automation 使用语义动作或稳定控件身份，记录每步开始、完成和 timeout。

## 5. 指标

### Distribution 与 startup

- application payload、installer/archive、bundled runtime；
- idle process count；
- cold/warm launch-to-interactive。

### Runtime resources

- idle/peak working set、private bytes、commit、CPU time；
- USER/GDI/kernel handles；
- 100 次循环后的 memory/handle delta。

### User-visible latency

- open-to-source-visible、first Preview、Preview-to-Source；
- Outline build 与 first/middle/last jump；
- search、save、UI thread longest stall、input latency。

### Correctness 与 stability

- contract PASS/FAIL/UNSUPPORTED；
- crash/hang、output hash 或语义结果；
- data integrity 与 recovery result。

### Engineering economics

- Agent wall-clock time/turns 与人工干预；
- generator/source change size、新增 tests、regressions；
- report-to-root-cause 和 root-cause-to-validation 时间；
- 被反证假说与 unresolved architecture debt。

## 6. Sampling

- 启动和短操作至少 30 个有效样本；
- 报告 p50/p95/p99/min/max；
- cold/warm 分开；
- 预先声明 timeout、discard、outlier 规则；
- 批次顺序轮换；
- 保留原始样本而非只保存汇总。

## 7. 公平性

- 比较相同 feature contract，不要求实现相同；
- OS 自带 DLL 与 bundled runtime 分开披露；
- 默认设置用于产品比较，等价固定设置用于微基准；
- unsupported 保留在 parity 分母；
- 性能不能抵消错误输出或数据丢失；
- diagnostics build 与 release build 分开报告。

## 8. AI benchmark

客户端开销使用同一本地 mock server：固定文本/token 数、首 token 延迟、token
interval 和 UTF-8/SSE 分块，并注入 disconnect、timeout、malformed JSON 与
oversized response。测量 request setup、decode、queue/backpressure、render 和内存。
真实模型只测 end-to-end 体验，不用于证明客户端解析性能。

## 9. Result schema

每次运行保存：

```json
{
  "schema": 1,
  "environment": {},
  "implementation": {},
  "contract_version": "v1",
  "workload_hashes": {},
  "samples": [],
  "summary": {},
  "failures": [],
  "validity_limits": []
}
```

## 10. V1 冻结门槛

1. Rabbit reference commit 明确锁定；
2. fixture corpus 与 hashes 提交；
3. 至少两个实现完成 dry run；
4. 自动化没有实现专属捷径；
5. schema 能表达 timeout、failure 与 unsupported；
6. 测量重复性达到预先声明容差。

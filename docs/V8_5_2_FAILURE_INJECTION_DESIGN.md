# V8.5.2 Failure Injection Design

Status: transactional save, ReadFile injection, and Outline/style arena growth-allocation injection implemented

## Principle

Test variants remain Direct-PE and replace selected imported calls through
generator-controlled wrappers. Release builds have injection disabled and emit
the ordinary IAT call path.

## Injection state

```text
inject_api_id
inject_call_ordinal
inject_mode
inject_value
observed_call_count
last_operation_stage
last_error_snapshot
```

An injected failure is selected by API identity and the Nth call within one
operation. The wrapper records the stage before returning a Win32-compatible
result.

## Required file modes

以下模式已全部实现。新增模式只在发现了对应的真实失败场景时加入，不要求
预先覆盖全部理论组合。

- CreateFile failure with invalid handle and chosen error;
- ReadFile failure before bytes, after partial bytes and after full bytes;
- WriteFile failure, short success, zero success and eventual completion;
- Flush failure;
- atomic replace failure before and at commit;
- CloseHandle failure recorded without overriding the primary operation result.

## Implemented transactional-write slice

`tools/test_v8_5_2_write_injection.py` builds four visibly marked binaries in
ignored `bin/test/`. The generator accepts the mode only through its build
namespace; release execution defaults to `release`, emits no wrapper and keeps
the release candidate byte-identical.

Covered modes:

- seven-byte short successes followed by eventual completion;
- successful zero-byte progress, which the save loop rejects;
- failure on the first write call;
- seven-byte success followed by failure on the second call.
- failure while flushing the completed sibling staging file;
- failure at the atomic replacement commit point.
- failure to create the sibling staging file;
- failed first close status followed by a cleanup close retry.

The tests verify call counts, memory text, dirty revisions, pending destructive
action, resulting disk bytes, staging cleanup and release-candidate hash
preservation. Every injected failure preserves the prior target byte-for-byte.
The staging file is created with `CREATE_NEW`, so a preexisting artifact is also
preserved and causes a safe failure instead of being truncated.

## Required allocation modes

不是每个理论组合都要实现。按风险排序，优先覆盖能破坏文档状态的分支：

| 模式 | 何时必须实现 |
|---|---|
| 有活动文档时的 growth failure | 该 arena 的容量由文档长度推导 |
| 首次分配失败 | 该 arena 在启动或 Open 早期建立 |
| 分配后清理重试 | 失败路径会释放或复用旧块 |
| scratch allocation failure | 实现真的引入了 scratch 提交模型 |

只为已经观察到的失败模式添加阻塞性注入分支。其余组合在引入对应机制时再补。

## Implemented Outline allocation slice

The test-only `fail_second` allocator permits the initial 4096-entry arena and
then rejects the first growth request. Open computes the exact canonical CRLF
length of the decoded candidate and reserves the needed Outline capacity before
writing `document_model` or changing the editor. The Windows harness proves that
failed growth preserves text, path, revisions, encoding, EOL, view state,
  Outline count, all arena pointers, and prior arena bytes. The release build calls
  `VirtualAlloc` directly and remains free of injection state.

## Implemented style-arena allocation slice

`tools/test_v8_5_2_style_alloc_injection.py` builds two marked binaries in
ignored `bin/test/` through `ARENA_ALLOC_INJECTION_MODE`:

- `style_fail_second` permits the startup 4096-entry arena and rejects the first
  growth request. Opening a 140,000-span document then fails at the Open
  allocation gate while text, path, revisions, encoding, EOL, view state, span
  count, capacity, all three arena pointers and sampled prior arena bytes stay
  byte-for-byte identical.
- `style_fail_first` rejects the startup allocation. No capacity is published,
  no span is recorded through a stale pointer, the process stays alive, and a
  later Open retries the allocation and succeeds normally.

`ARENA_ALLOC_INJECTION_MODE` also accepts the original Outline modes
(`fail_first`, `fail_second`); the earlier `OUTLINE_ALLOC_INJECTION_MODE`
variable is still honored as an alias for external harnesses.

## Implemented ReadFile slice

The noninteractive Open test build can cap each successful read to seven bytes,
return successful zero progress, fail the first call, or fail after one partial
read. Each failure keeps the prior model, path, revisions and view mode intact;
short reads continue until the size snapshot is satisfied. These hooks and the
picker-bypass command exist only in visibly marked binaries under `bin/test/`.

## Assertions after every injected point

- active DocumentModel and committed path are either wholly old or wholly new;
- destination and recovery bytes match one declared valid state;
- dirty/revisions reflect the commit point;
- no handle or scratch block remains owned without a cleanup path;
- no UI success indication is emitted;
- captured error is the injected primary error, not a later cleanup error.

## Harness outputs

Each case writes JSON containing candidate hash, injection parameters, visited
stages, final revisions, output file hashes, remaining temporary paths, process
exit code and assertion results. The fixture directory is disposable and may
never point at user documents.

## Safety boundary

Injection hooks cannot be enabled by ordinary release UI or environment input.
They are selected at generation time for a test binary and are visibly marked in
the title, manifest and output filename.

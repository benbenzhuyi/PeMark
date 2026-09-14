# V8.5.2 Failure Injection Design

Status: transactional save and ReadFile injection implemented; allocation modes remain design gates

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

- reserve failure;
- first commit failure;
- growth commit failure;
- scratch allocation failure after active model exists;
- parser-derived arena failure independently for render/map/style/outline.

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

# V8.5.2 Failure Injection Design

Status: design gate; no production behavior enabled

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

## Required allocation modes

- reserve failure;
- first commit failure;
- growth commit failure;
- scratch allocation failure after active model exists;
- parser-derived arena failure independently for render/map/style/outline.

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


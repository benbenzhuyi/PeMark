# V8.5.2 Current I/O and Capacity Map

Status: historical V8.5.1 baseline; V8.5.2 changes are tracked below

## Current load path

```text
cmd_open -> GetOpenFileNameW
 -> reset view/timer state before file validity is known
 -> CreateFileW(OPEN_EXISTING)
 -> GetFileSize
 -> reject > 4 MiB
 -> one ReadFile call
 -> CloseHandle
 -> UTF-16LE BOM branch, otherwise UTF-8 then ACP fallback
 -> normalize_to_document_model
 -> load_model_into_editor
 -> update_preview/update_status
```

Risks: read completion is not looped; current state is disturbed before the new
document transaction commits; malformed UTF-8 can enter implicit ACP fallback;
path, encoding and model do not form one explicit commit record.

## Current save path

```text
cmd_save/cmd_saveas -> current_path
 -> sync_model_from_editor
 -> WideCharToMultiByte(CP_UTF8)
 -> CreateFileW(CREATE_ALWAYS) on final destination
 -> one WriteFile call
 -> CloseHandle
 -> report success path
```

Risks: `CREATE_ALWAYS` truncates the last good file before complete output is
known; returned `io_count` is not checked against requested bytes; no temporary
file/atomic replace; no revision/saved_revision; Save As path can change before
successful commit; no durability or recovery policy.

## Current state and buffers

| Item | Current representation | Limit/risk |
|---|---|---|
| path | `current_path`, 512 UTF-16 units | long-path policy absent |
| input | `bytebuf` | fixed 34.5 MB |
| decoded text | `widebuf` | fixed 8.5M UTF-16 |
| document | `document_model` | fixed 8.5M UTF-16 |
| render | `previewbuf` | fixed 8.5M UTF-16 |
| map | `render_srcmap` | fixed 8.5M dwords |
| style spans | three arrays | 131072, silently stops adding |
| outline | arrays | 2048 active cap |
| input file | `MAX_FILE_BYTES` | 4,194,304 bytes |
| dirty state | absent | destructive transitions unguarded |
| encoding | `encoding_state` | not a complete input/output policy |

## Required ownership additions

- `document_revision`, `saved_revision`;
- explicit operation state and error capture;
- immutable save snapshot metadata;
- candidate path separate from committed path;
- encoding and preferred EOL metadata;
- arena descriptors and scratch/active ownership.

## Migration boundary

The first production change adds revision ownership only. It must not yet alter
file bytes, encoding behavior, PE sections or allocation. Atomic save and arena
migration follow as separate bounded changes.

## V8.5.2 implemented delta

- Open defers view, path, encoding and revision changes until one success point.
- Empty files bypass a zero-length `ReadFile` call.
- Nonempty files use a checked complete-read loop; short reads advance, while
  API failure, zero progress and counts above the remainder fail transactionally.
- UTF-8 uses `MB_ERR_INVALID_CHARS`; ACP fallback has been removed.
- UTF-8 BOM and UTF-16LE BOM remain explicit, and odd UTF-16 byte counts or
  decoded embedded NULs fail transactionally.
- Save uses the sibling staging and atomic-replacement transaction documented in
  `V8_5_2_FILE_OPERATION_CONTRACTS.md` and `V8_5_2_RECOVERY_POLICY.md`.

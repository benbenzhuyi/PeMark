# Known Issues and Technical Debt

## P0 — active functional defects in V8.4.23

### P0-001 Preview Outline navigation can map every item to document end

Confirmed root cause: volatile RAX array offset clobbered by `IsWindowVisible` in `navigate_outline`. See `CURRENT_CODE_AUDIT.md` and `patches/P0_PREVIEW_OUTLINE_RAX_CLOBBER.md`.

### P0-002 Custom Outline scrollbar thumb is not reliably visible/draggable

Field reproduced. Exact single-line root cause not established. Current architecture distributes state/geometry across multiple routines. Required response: bounded controller/state refactor, not more repaint patches.

## P1 — architecture debt

- Multiple view-state representations (`preview_flag`, visibility, `view_hwnd`).
- Separate Markdown scans for Outline and Preview.
- Fixed 2048-entry Outline capacity.
- Fixed 131072 style-span capacity.
- Fixed 4 MiB file cap / large static buffers.
- Layout computations still spread beyond a single true LayoutManager.
- Message pump intercepts child mouse messages and also acts as a controller.
- Custom scroll surface paint, hover, hit-test and drag do not yet consume one immutable geometry record.

## P1 — build-layout debt

Current text segment has ~1.2 KiB headroom before RDATA. Major code growth requires PE layout refactor.

## P2 — PE hardening debt

- single RWX section
- no relocations/ASLR
- no `.pdata` unwind metadata
- no CFG metadata
- no read-only separation for static data

These are not the cause of current UI bugs but are important if the experiment becomes a long-lived product.

## P2 — testing debt

Until Codex/agents run on Windows with debugging/instrumentation, many visual/state fixes have been validated manually by the user. Build automated/semi-automated Windows regression tooling as an early takeover task.

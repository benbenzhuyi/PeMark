# V8.4.24 Windows regression record

Environment: Windows build 26200, 150% display scaling, Light and Dark. Date: 2026-09-13. The Python platform string reports Windows-10-10.0.26200-SP0. UI input uses native Windows automation; BSS snapshots are read-only debugger observations.

## Frozen baseline

V8.4.23 EXE SHA256: `50fdb51c28a90f9457d61761c923cd54f668de040e81941d99030fc42f2f2f4f`.

On `position_map_300_chapters.md`, Preview Chapter 2 incorrectly jumped to Chapter 300 / EOF. The scrollbar thumb occupied all 557 track units (zero travel). Both were reproduced before editing. Initial Source Chapter 3 navigation and the first Preview toggle worked on this sample; the historical cold-start failure was not reproduced.

## Intermediate Windows evidence (not the final build)

SHA `3b9a875faf2340faf4416a493d9f5fbf648a1aff522846186c87ceacf717a0a3`: corrected Preview Chapter 2 and Chapter 149 navigation, 20 mode toggles and Source thumb dragging. Fast Preview drag still became page clicks, and long formatting stalls were observed. Files named `candidate_*.json` and `gui_20_mode_toggles.json` belong to this intermediate build.

SHA `0a1197c6e7b2d7ec7aba445daa1191684f49cd09f40360ae8659665de173f3ad`: opened `large_regression_1_2mb.md` (887,567 Source UTF-16 units; 696,374 rendered units; 600 headings). First Source Chapter 2 navigation and first Preview toggle worked. Preview Chapters 1, 50 and 100 were correct. Fast thumb top/middle/end/return and track page-down worked. Twenty mode toggles and twenty theme toggles passed; document/render lengths stayed unchanged through theme toggles. See `latest_gui_toggles.json` and `latest_large_middle.json`. Input plus first Preview screenshot took 246 ms in one observation; this is not a controlled performance benchmark. This build revealed fenced-code spaces disappearing and wrap-triggered Preview restyling loss. Normal Alt+F4 exited PID 35072 without a lingering process.

SHA `b09f9d034f7c493a9bdec68df172bb5120af1688af89cb789bb97db7e03a14db`: verified restored code spaces/indentation visually and fixed styling after wrap. Wrap still returned Preview to the top; the final candidate avoids rebuilding the unchanged RenderModel. PID 38124 exited normally.

## Further intermediate regression

SHA `b90ff9f1fdd1b6d935d69ae17319268e48ab81637b4ba8ec4040de0a10416513`: Markdown styles and Preview wrap position passed, but opening the large document and enabling Source wrap exited the process. A following build (`41a55da65b97e3b9e4688b48b8e801e44905d69c92108efeb7de59b5094f8768`) corrected a stale module handle yet still exited. Creating an empty EDIT first, raising its limit, then loading text resolved the reproduced failure. This is why intermediate tests must not be treated as final acceptance.

## Current candidate

SHA `a0342cd8f7bd8a6c4118241621e54fed7b4b83401c881fdfc73cc7e6633ee260`. Code size 26,878 bytes; remaining code budget 1,794 bytes. EXE size 45,056 bytes. Final run: 2026-09-14, PID 25024.

Twelve machine-code regression groups pass. PE inspection reports AMD64 PE32+, GUI subsystem, unchanged imports and section layout. All changes are in the independent stabilization generator/output; the V8.4.23 generators and binaries remain frozen.

Windows Markdown matrix was visually verified on the preceding b90ff9 build: H1–H6, bold, italic, inline code, quote, bullets, link appearance, fenced-code background/indentation/internal spaces and Chinese emphasis. Ctrl+End reaches the bottom; Ctrl+Shift+W preserves Preview position and formatting. The later changes only alter Source control creation. Link activation is not tested.

On the current candidate, PID 28268 opened the 1.2 MB document, successfully switched Source wrap off/on and navigated to Chapter 2. Some immediate Source recreation screenshots showed transient incomplete repaint; subsequent navigation repainted correctly. This visual transition has not been formally characterized.

Fresh current-candidate run PID 25024 passed initial Source Chapter 2 navigation, first Preview toggle, 20 mode transitions (BSS mode plus accessible HWND state), 20 theme transitions (theme flag plus unchanged document/render lengths), Preview Chapter 1/50/100 navigation, fast thumb dragging top/middle/end/back and page-down track click. Thumb height 32, track 557, travel 525, maximum top 582 for 600 headings/18 visible rows. Alt+F4 removed both the window and process. Evidence: `tests/results/final_gui_toggles.json`, `final_large_end.json`, `final_machine_tests.json`, `final_pe_inspection.txt`, `final_integrity.json`.

No crash/exit occurred during this fresh run. This statement does not erase the intermediate-build failures above or certify long-duration stability. The full release gate remains pending, including per-transition menu check verification and the remaining smoke/capacity/encoding matrix. Unlisted tests are pending, not implicit passes.

## Reproduction commands

From the project root:

```powershell
python src/stabilization/generate_markdown_editor_v8_4_24.py
python tools/test_stabilization.py
python tools/inspect_pe.py bin/stabilization/direct_pe_markdown_editor_x64_v8_4_24.exe
```

Machine-code tests require `unicorn` (`python -m pip install unicorn`); the production generator requires no compiler/assembler/linker. `tools/read_runtime_state.py PID generator.py output.json` is a read-only debugger snapshot, not a GUI assertion.

## Not certified

Full edit/save/reopen, all editing shortcuts, find/replace, newline/encoding permutations, >4 MiB rejection, 2,600-heading capacity and long-duration stability still require a dedicated pass. The existing 2,048-heading cap and FileIO audit risks are not resolved by this candidate. Do not present this as a general bug-free/stable release.

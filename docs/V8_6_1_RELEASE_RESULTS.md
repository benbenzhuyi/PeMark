# PeMark V8.6.1 — Current Release Results

Status: current release snapshot  
Generator: `src/current/generate_markdown_editor_v8_6_1.py`  
Binary: `bin/current/pemark_x64_v8_6_1.exe`  
EXE SHA-256:
`abd79de90999a70f3b5328c63cb73109ea0a38cac85c5ed59f197cab397ac4bc`

## What changed in V8.6.1

- The main window uses a 32px custom title row instead of the native
  caption + menu pair.
- The title row owns the left sidebar switch, the app name, the five menu
  entries, six tool icons and the window buttons.
- Panel switches follow Codex's rounded-rectangle-with-divider shape; Source
  mode renders literal `</>` chevrons.
- Save, find, render/source, dark/light, minimize, maximize and close reuse
  the existing command IDs.
- Gear and right-sidebar buttons are hover-only placeholders.

## Validation

- `tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_6_1.py`:
  13/13 groups, 0 failures.
- `tools/test_v8_6_caption.py`: caption geometry, icon hit rectangles, hover,
  inert placeholders and the live left switch.
- `tools/smoke_test_v8_5_1.py`: 17/17 on the candidate; the release binary
  passed a PID-filtered new / preview / source / dark / light / wrap / close
  smoke matrix because a hand-test instance was holding the interactive
  window during the final release build.
- `tools/inspect_pe.py bin/current/pemark_x64_v8_6_1.exe`: 6 sections,
  machine `0x8664`, subsystem 2, no W+X section.

## Known limits

- The executable is unsigned.
- The V8.6 file-panel redesign is not complete: the tree model, create /
  rename / delete / refresh operations and the remaining Rabbit-parity
  interactions are still scheduled slices.
- The V8.5.4 document-safety and PE-hardening guarantees remain inherited.

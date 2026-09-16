# Handoff Checklist

> Historical V8.4.23 takeover checklist. Use `CODEX_START_HERE.md` for the
> current V8.5.4 Preview workflow.

## Package integrity

- [ ] Extract package preserving directory structure.
- [ ] Verify `SHA256SUMS.txt` if desired.
- [ ] Read `CODEX_START_HERE.md` and `AGENTS.md`.
- [ ] Tag/copy frozen V8.4.23 before edits.

## Baseline reproduction

- [ ] Run portable build helper or generator.
- [ ] Confirm EXE SHA-256 `50fdb51c28a90f9457d61761c923cd54f668de040e81941d99030fc42f2f2f4f` for unchanged V8.4.23.
- [ ] Run `tools/inspect_pe.py`.
- [ ] Record Windows version/DPI/theme for GUI tests.

## Reproduce known P0 issues

- [ ] Preview Outline navigation to EOF.
- [ ] Custom Outline scrollbar missing/non-draggable thumb.

## Stabilization work

- [ ] Implement ViewController single-state ownership.
- [ ] Fix canonical source-offset Outline navigation.
- [ ] Consolidate OutlineScrollState and geometry.
- [ ] Add debug instrumentation option.
- [ ] Run full regression suite.

## Documentation

- [ ] Update current audit after fixes.
- [ ] Record new binary/source hashes.
- [ ] Update version history and decision log.
- [ ] Do not remove failed-approach history; it prevents regression archaeology loss.

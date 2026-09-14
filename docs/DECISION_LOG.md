# Architecture Decision Log

## ADR-001 — Preserve pure Direct-PE build

Decision: final EXE remains directly generated from Python; no compiler/assembler/linker. Rationale: this is the defining experimental objective and the user's explicit continuation requirement.

## ADR-002 — DocumentModel is canonical

Decision: Source/Preview/Outline derive from one normalized document model. Preview never writes Source.

## ADR-003 — RichEdit retained for Preview for now

Decision: keep RichEdit as current presentation surface while reducing full-document formatting. Reconsider only with measured reasons.

## ADR-004 — Source offsets are canonical navigation coordinates

Decision: Outline entries store source offsets only. Preview coordinates are derived through the current PositionMap.

## ADR-005 — UI visuals and hit regions are separate

Decision: 1px divider may have 8px logical hit area; scrollbar visual thumb may be narrower than interaction gutter.

## ADR-006 — No more state-by-screenshot patching

Decision: visual bug fixes must identify ownership/geometry/state layer and add a regression case. Avoid repeated repaint calls without a state model.

## ADR-007 — V8.4.23 frozen as historical active snapshot

Decision: handoff package preserves V8.4.23 unchanged. Fixes happen on a stabilization branch so Codex can compare exact before/after binaries.

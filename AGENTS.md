# AGENTS.md — Mandatory Instructions for Codex and Other Development Agents

## Project identity

This is a **pure Direct-PE Windows x64 experiment**. The build-time Python generator constructs the PE32+ image, import table, static data, virtual BSS, and AMD64 machine code bytes directly.

### Non-negotiable build constraint

The production `.exe` must **not** be produced by:
- C/C++ compiler
- Rust compiler
- assembler
- linker
- .NET / managed compiler
- packager that embeds an interpreter

Analysis/debugging tools are allowed. Python is allowed as the generator and test harness.

## Before editing

- Read `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`.
- Read `docs/MILESTONE_PLAN.md`.
- Read `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`.
- Read `docs/CURRENT_CODE_AUDIT.md`.
- Read `docs/WIN64_ABI_RULES.md`.
- Read `docs/ARCHITECTURE_V8_5_TARGET.md`.
- Read `docs/FAILED_APPROACHES.md` so you do not reintroduce already-proven bad designs.
- Rebuild and hash the current baseline.

When documents conflict, the long-term architecture, milestone plan and V8.5+
development manual describe current policy. V8.4 audit/handoff files are
historical evidence unless a current document explicitly adopts their finding.

## Hard engineering rules

1. **One source of truth:** `DocumentModel` owns document text.
2. **One view-mode state:** SOURCE/PREVIEW must not be represented by multiple independent flags/visibility assumptions.
3. **Outline stores source offsets only.** Preview offsets are derived through PositionMap.
4. **Every Win64 API call may clobber RAX, RCX, RDX, R8, R9, R10, R11.** Never keep live values there across calls.
5. Before every nested call from emitted machine code, maintain Win64 stack alignment and 32-byte shadow space.
6. Geometry belongs to one LayoutManager. Do not let individual commands independently calculate/move panes.
7. Scrollbar paint, hit-test, and drag must consume the same cached `thumbRect`; never recompute three subtly different rectangles.
8. Theme changes swap Palette + invalidate. Theme must not reparse Markdown.
9. Zoom must not rebuild Markdown RenderModel.
10. Do not perform RichEdit full-document per-span formatting on large documents.
11. Do not claim a GUI bug fixed without Windows execution. Linux/container static checks are necessary but insufficient.
12. Every fix must add/update a deterministic regression case.
13. **Minimum sufficient engineering.** Implement the smallest mechanism that
    solves a demonstrated problem. Plans and architecture documents describe
    intent; they do not authorize building future infrastructure early. Before
    adding a check, contract, ADR, gate or fixture, name the failure it prevents
    and why a cheaper option is insufficient.
14. **Gate by level.** Apply commit-level, milestone-level or release-level
    verification as defined in `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md` 5.1. Do not
    apply release-level process to every change.

## Change discipline

- Prefer bounded refactors over patch chains.
- Make one subsystem the owner of each state.
- Keep a `CHANGELOG_UNRELEASED.md` while working.
- If changing PE layout, regenerate `docs/PE_MEMORY_MAP.md` and run `tools/inspect_pe.py`.
- If changing imports, update `docs/WIN32_API_SURFACE.md`.
- If changing shortcuts/menu commands, update `docs/FEATURE_AND_SHORTCUT_SPEC.md`.

## Completion gate for V8.4.24 stabilization

Do not call the stabilization complete until the Windows regression suite passes: first-open source Outline navigation; first Source→Preview toggle; Preview Outline navigation at beginning/middle/end; 20 mode toggles; 20 theme toggles; scrollbar hover/drag/page; 887k/1.2MB document navigation; Markdown feature matrix; no crash.

# PeMark V8.5.4 (unreleased)

V8.5.3 shipped; its full record is `docs/CHANGELOG_V8_5_3.md`.

V8.5.4 is the Direct-PE hardening milestone: declare sections and region
permissions, add base relocations and ASLR, emit unwind metadata where it
applies, and verify the result with the existing loader and regression
evidence. The huge single writable region is gone, so this work can now be
measured instead of argued about.

Add entries here as each bounded change lands, with level-appropriate evidence.

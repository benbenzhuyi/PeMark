# Win64 ABI Rules for the Direct Machine-Code Emitter

These rules are mandatory. Several historical crashes/corruptions came from violating them.

## Integer argument registers

Windows x64 first four integer/pointer arguments:

```text
arg1 RCX
arg2 RDX
arg3 R8
arg4 R9
```

Additional arguments are placed on the stack after the 32-byte home/shadow space.

## Volatile registers

A called function/API may freely destroy:

```text
RAX RCX RDX R8 R9 R10 R11
XMM0-XMM5
```

**Never keep a live index, pointer, width, RECT coordinate, source offset or state value in these registers across a Win32 API call.** Spill to:

- nonvolatile register,
- stack local,
- or named BSS state.

Historical regressions:

- V8.4.4 owner-draw crash: `R9` reused after `SelectObject`.
- V8.4.22/23 Preview Outline navigation: array offset in `RAX` reused after `IsWindowVisible`.
- scrollbar paint experiments: geometry kept in `R10` across API calls.

## Nonvolatile registers

Callee must preserve if modified:

```text
RBX RBP RSI RDI R12 R13 R14 R15
XMM6-XMM15
```

If an emitted routine pushes/saves them, restore symmetrically.

## Stack alignment and shadow space

On entry after a CALL, `RSP` is 8 mod 16. Before making another call, the caller must provide 32 bytes of shadow space and have RSP 16-byte aligned at the CALL instruction.

Common no-extra-push prologue:

```text
sub rsp, 0x28
...
call API
...
add rsp, 0x28
ret
```

If you push registers first, recalculate alignment. Do not blindly copy `sub rsp,0x28`.

Historical large-file crash V8.4.3 came from a function pushing an odd/even set of registers and then reserving the wrong amount, causing misaligned Win32 calls.

## Return values

Scalar/pointer return is in RAX/EAX. It overwrites whatever was previously there.

## Call-site checklist

Before every `call_iat` / `call_label`:

1. Is RSP correctly aligned?
2. Is 32-byte shadow space available for an ABI call?
3. Are all values needed after the call stored outside volatile registers?
4. Are stack-passed args at correct offsets for the current frame size?
5. If a nested internal routine can call APIs, treat it as clobbering volatile regs too.

## Recommended generator improvement

Introduce call helpers with declared clobbers and local slots instead of hand-coding lifetime assumptions. Example conceptual API:

```python
with fn_frame(locals=16, save=['r12','r13']):
    spill('source_offset', 'rax')
    call_win64('IsWindowVisible', ...)
    reload('r10', 'source_offset')
```

This can remain a raw byte emitter; the goal is to encode ABI discipline in the generator.
